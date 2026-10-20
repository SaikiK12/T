//! Hourly price sources on one research axis, with the lab's accounting rules (scripts/run_delist.py `Book`,
//! lab/panel.py `load_panel`): prices and funding are stored as f32 like the Python panel, a bar is traded only if its
//! close is finite and its volume > 0, funding settles on the bar whose open equals the settlement time.

use anyhow::{Context, Result, anyhow};
use arrow_array::{Array, Float64Array, Int64Array};
use arrow_cast::cast;
use arrow_schema::DataType;
use parquet::arrow::ProjectionMask;
use parquet::arrow::arrow_reader::ParquetRecordBatchReaderBuilder;
use rayon::prelude::*;
use std::collections::HashMap;
use std::fs::File;
use std::path::{Path, PathBuf};

pub const H: i64 = 3_600_000;

/// Epoch ms of a UTC date "YYYY-MM-DD".
pub fn ms(date: &str) -> Result<i64> {
    let p: Vec<i64> = date.split('-').map(|x| x.parse::<i64>()).collect::<Result<_, _>>()?;
    if p.len() != 3 {
        return Err(anyhow!("bad date {date}"));
    }
    let (y, m, d) = (p[0], p[1], p[2]);
    // days from civil (Howard Hinnant)
    let y2 = if m <= 2 { y - 1 } else { y };
    let era = y2.div_euclid(400);
    let yoe = y2 - era * 400;
    let mp = (m + 9) % 12;
    let doy = (153 * mp + 2) / 5 + d - 1;
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    Ok((era * 146097 + doe - 719468) * 86_400_000)
}

/// UTC calendar year of epoch ms.
pub fn year(t: i64) -> i32 {
    let z = t.div_euclid(86_400_000) + 719468;
    let era = z.div_euclid(146097);
    let doe = z - era * 146097;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    (yoe + era * 400 + if m <= 2 { 1 } else { 0 }) as i32
}

/// The research axis: hourly opens from `start` to `end` + 1 day (exclusive), as lab/panel.py builds it.
#[derive(Clone, Copy, Debug)]
pub struct Axis {
    pub t0: i64,
    pub n: usize,
}

impl Axis {
    pub fn new(start: &str, end: &str) -> Result<Self> {
        let t0 = ms(start)?;
        let t1 = ms(end)? + 24 * H;
        Ok(Axis { t0, n: ((t1 - t0 + H - 1) / H) as usize })
    }
    pub fn row(&self, t: i64) -> i64 {
        (t - self.t0).div_euclid(H)
    }
}

/// One symbol on the axis.
pub struct Series {
    pub close: Vec<f64>,
    pub traded: Vec<bool>,
    pub last: Vec<i64>,  // last traded row at or before r, -1 if none
    pub cumf: Vec<f64>,  // cumf[k] = sum of settled funding on rows < k (length n + 1)
}

impl Series {
    /// Short from the close of r0 to the close of r0 + h (last traded close at or before it). None if not tradable.
    pub fn leg(&self, r0: i64, h: i64) -> Option<Leg> {
        let n = self.close.len() as i64;
        let xr = r0 + h;
        if r0 < 1 || xr + 1 >= n || !self.traded[r0 as usize] {
            return None;
        }
        let jx = self.last[xr as usize];
        let (entry, exit) = (self.close[r0 as usize], self.close[jx as usize]);
        Some(Leg {
            gross: -(exit / entry - 1.0),
            funding: self.fund(r0, xr),
            stale_exit: jx < xr,
            delisted_in_hold: self.last[(n - 1) as usize] < xr,
        })
    }
    /// `leg` with a protective cover: exit at the first traded close in (r0, r0 + h] that has moved `stop` or more
    /// against the position (up for a short, down for a long); funding stops at that close. stop 0 is `leg` itself.
    /// The flag says the cover fired.
    pub fn leg_stop(&self, r0: i64, h: i64, short: bool, stop: f64) -> Option<(Leg, bool)> {
        let l = self.leg(r0, h)?;
        if stop <= 0.0 {
            return Some((l, false));
        }
        let entry = self.close[r0 as usize];
        for r in r0 + 1..=r0 + h {
            if !self.traded[r as usize] {
                continue;
            }
            let ret = self.close[r as usize] / entry - 1.0;
            if (short && ret >= stop) || (!short && ret <= -stop) {
                let n = self.close.len() as i64;
                return Some((Leg { gross: -ret, funding: self.fund(r0, r), stale_exit: false,
                                   delisted_in_hold: self.last[(n - 1) as usize] < r }, true));
            }
        }
        Some((l, false))
    }
    /// Settlements in (entry, exit]: rows r0 + 2 .. xr + 1.
    pub fn fund(&self, r0: i64, xr: i64) -> f64 {
        self.cumf[(xr + 2) as usize] - self.cumf[(r0 + 2) as usize]
    }
    /// Long return close(r0) -> close(r0 + h), NaN-propagating, and the funding over the hold.
    pub fn long(&self, r0: i64, h: i64) -> (f64, f64) {
        let xr = r0 + h;
        (self.close[xr as usize] / self.close[r0 as usize] - 1.0, self.fund(r0, xr))
    }
    pub fn traded_at(&self, r: i64) -> bool {
        r >= 0 && (r as usize) < self.traded.len() && self.traded[r as usize]
    }
}

#[derive(Clone, Copy, Debug)]
pub struct Leg {
    pub gross: f64,
    pub funding: f64,
    pub stale_exit: bool,
    pub delisted_in_hold: bool,
}

/// A venue: a folder of hourly klines (and optionally settled funding), loaded for the symbols asked.
pub struct Source {
    pub name: String,
    pub idx: HashMap<String, usize>,
    pub series: Vec<Series>,
}

impl Source {
    pub fn get(&self, sym: &str) -> Option<&Series> {
        self.idx.get(sym).map(|&i| &self.series[i])
    }
}

pub(crate) fn read_cols(path: &Path, names: &[&str]) -> Result<Vec<Vec<f64>>> {
    let file = File::open(path).with_context(|| format!("open {}", path.display()))?;
    let b = ParquetRecordBatchReaderBuilder::try_new(file)?;
    let schema = b.schema().clone();
    let idx: Vec<usize> = names.iter().map(|n| schema.index_of(n)).collect::<Result<_, _>>()
        .with_context(|| format!("columns {names:?} in {}", path.display()))?;
    let mask = ProjectionMask::roots(b.parquet_schema(), idx.clone());
    let reader = b.with_projection(mask).build()?;
    let mut out = vec![Vec::new(); names.len()];
    for batch in reader {
        let batch = batch?;
        for (k, n) in names.iter().enumerate() {
            let col = batch.column_by_name(n).ok_or_else(|| anyhow!("missing {n}"))?;
            if *n == "t" {
                let a = cast(col, &DataType::Int64)?;
                let a = a.as_any().downcast_ref::<Int64Array>().unwrap();
                out[k].extend((0..a.len()).map(|i| if a.is_null(i) { f64::NAN } else { a.value(i) as f64 }));
            } else {
                let a = cast(col, &DataType::Float64)?;
                let a = a.as_any().downcast_ref::<Float64Array>().unwrap();
                out[k].extend((0..a.len()).map(|i| if a.is_null(i) { f64::NAN } else { a.value(i) }));
            }
        }
    }
    Ok(out)
}

fn f32r(x: f64) -> f64 {
    (x as f32) as f64
}

fn load_one(root: &Path, klines: &str, vol: &str, funding: Option<&str>, sym: &str, ax: Axis) -> Result<Series> {
    let n = ax.n;
    let mut close = vec![f64::NAN; n];
    let mut volume = vec![f64::NAN; n];
    let c = read_cols(&root.join(klines).join(format!("{sym}.parquet")), &["t", "close", vol])?;
    for i in 0..c[0].len() {
        let r = ax.row(c[0][i] as i64);
        if r >= 0 && (r as usize) < n {
            close[r as usize] = f32r(c[1][i]);
            volume[r as usize] = f32r(c[2][i]);
        }
    }
    let mut fe = vec![0.0f64; n];
    if let Some(f) = funding {
        let p = root.join(f).join(format!("{sym}.parquet"));
        if p.exists() {
            let g = read_cols(&p, &["t", "rate"])?;
            for i in 0..g[0].len() {
                let r = ax.row(g[0][i] as i64);
                if r >= 0 && (r as usize) < n && g[1][i].is_finite() {
                    fe[r as usize] = f32r(g[1][i]);
                }
            }
        }
    }
    let traded: Vec<bool> = (0..n).map(|r| close[r].is_finite() && volume[r].is_finite() && volume[r] > 0.0).collect();
    let mut last = vec![-1i64; n];
    let mut l = -1i64;
    for r in 0..n {
        if traded[r] {
            l = r as i64;
        }
        last[r] = l;
    }
    let mut cumf = vec![0.0f64; n + 1];
    for r in 0..n {
        cumf[r + 1] = cumf[r] + fe[r];
    }
    Ok(Series { close, traded, last, cumf })
}

pub struct VenueSpec<'a> {
    pub name: &'a str,
    pub klines: &'a str,
    pub vol: &'a str,
    pub funding: Option<&'a str>,
}

/// Load the symbols in parallel. Symbols without a file are skipped (the caller sees them as not traded).
pub fn load(root: &Path, v: &VenueSpec, syms: &[String], ax: Axis) -> Result<Source> {
    let have: Vec<String> = syms.iter().filter(|s| root.join(v.klines).join(format!("{s}.parquet")).exists()).cloned().collect();
    let series: Vec<Series> = have.par_iter().map(|s| load_one(root, v.klines, v.vol, v.funding, s, ax))
        .collect::<Result<_>>()?;
    let idx = have.iter().enumerate().map(|(i, s)| (s.clone(), i)).collect();
    Ok(Source { name: v.name.to_string(), idx, series })
}

pub fn data_root() -> PathBuf {
    std::env::var("QX_DATA").map(PathBuf::from).unwrap_or_else(|_| PathBuf::from("data"))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn epoch_ms() {
        assert_eq!(ms("1970-01-01").unwrap(), 0);
        assert_eq!(ms("2021-01-01").unwrap(), 1_609_459_200_000);
        assert_eq!(ms("2025-01-01").unwrap(), 1_735_689_600_000);
        assert_eq!(year(ms("2025-01-01").unwrap()), 2025);
        assert_eq!(year(ms("2024-12-31").unwrap() + 86_399_999), 2024);
        assert_eq!(year(ms("2024-02-29").unwrap()), 2024);
    }
    #[test]
    fn axis_rows() {
        let a = Axis::new("2021-01-01", "2021-01-01").unwrap();
        assert_eq!(a.n, 24);
        assert_eq!(a.row(1_609_459_200_000 + 3 * H + 5), 3);
    }
    #[test]
    fn leg_rules() {
        let close = vec![1.0, 2.0, 2.0, 1.0, f64::NAN, 4.0];
        let traded = vec![true, true, true, true, false, true];
        let last = vec![0, 1, 2, 3, 3, 5];
        let mut cumf = vec![0.0; 7];
        for k in 1..7 {
            cumf[k] = cumf[k - 1] + 0.01;
        }
        let s = Series { close, traded, last, cumf };
        let l = s.leg(1, 2).unwrap();
        assert!((l.gross - 0.5).abs() < 1e-12);           // short 2 -> 1
        assert!((l.funding - 0.02).abs() < 1e-12);         // rows 3..4
        assert!(!l.stale_exit);
        let l = s.leg(2, 2).unwrap();                       // exit row 4 not traded: last close row 3
        assert!(l.stale_exit);
        assert!(s.leg(0, 1).is_none());
        assert!(s.leg(3, 2).is_none());                     // xr + 1 >= n
    }
    #[test]
    fn stop_rules() {
        // entry close 10 at row 1; row 2 +30%, row 3 -40%, row 4 not traded, row 5 +50%
        let close = vec![9.0, 10.0, 13.0, 6.0, f64::NAN, 15.0, 15.0];
        let traded = vec![true, true, true, true, false, true, true];
        let last = vec![0, 1, 2, 3, 3, 5, 6];
        let mut cumf = vec![0.0; 8];
        for k in 1..8 {
            cumf[k] = cumf[k - 1] + 0.01;
        }
        let s = Series { close, traded, last, cumf };
        // no stop is exactly `leg`
        let (l, hit) = s.leg_stop(1, 4, true, 0.0).unwrap();
        assert!(!hit && (l.gross - s.leg(1, 4).unwrap().gross).abs() < 1e-15);
        // short, 20% cover: fires at row 2 (+30%), funding rows 3..3 only
        let (l, hit) = s.leg_stop(1, 4, true, 0.2).unwrap();
        assert!(hit && (l.gross + 0.3).abs() < 1e-12 && (l.funding - 0.01).abs() < 1e-12 && !l.stale_exit);
        // short, 40% cover: never reached (row 5 is beyond h = 3), so the plain exit at row 4 -> last close row 3
        let (l, hit) = s.leg_stop(1, 3, true, 0.4).unwrap();
        assert!(!hit && (l.gross - 0.4).abs() < 1e-12 && l.stale_exit);
        // long, 35% cover: fires at row 3 (-40%)
        let (l, hit) = s.leg_stop(1, 4, false, 0.35).unwrap();
        assert!(hit && (l.gross - 0.4).abs() < 1e-12 && (l.funding - 0.02).abs() < 1e-12);
        // the cover is checked at the exit bar too
        let (_, hit) = s.leg_stop(1, 1, true, 0.3).unwrap();
        assert!(hit);
    }
}
