//! Factor report (alphalens / Qlib style) for a family of cross-sectional factors, decided together.
//!
//! Input: a long parquet with t (ms, the open of the hourly bar whose close is the decision), sym, and one numeric column
//! per factor; a factor value must use only data up to that bar's close. Prices and funding come from one venue folder.
//! - Forward return of a coin at horizon h: close(r0) to the last traded close at or before r0 + h, minus the funding a
//!   long pays over (entry, exit]. A coin needs a traded bar at r0 and data to r0 + h + 1.
//! - Per decision date, factor and horizon, with at least `min_names` coins: Pearson IC, rank IC (Spearman, average
//!   ranks for ties), mean forward return per quantile (by factor rank; ties broken by symbol order), and the
//!   long-short spread (top quantile minus bottom).
//! - Turnover: the share of the top (bottom) quantile's names that were not there on the previous date.
//! - Net long-short, for the horizon equal to the date spacing only (a book rebalanced every date): spread minus
//!   2 x cost x (top turnover + bottom turnover).
//! - t: Newey-West (Bartlett) with lags = ceil(h / spacing), since forward windows overlap when h > spacing.
//! Family decision: moving-block bootstrap of dates (blocks of ceil(max h / spacing), at least `min_block`), each series
//! centred on its own mean; the statistic is the max |t| of rank IC over every factor and horizon.

use crate::data::{self, Axis, VenueSpec};
use crate::events::percentile;
use crate::stats;
use anyhow::{Context, Result, anyhow};
use arrow_array::{Array, Int64Array, StringArray};
use arrow_cast::cast;
use arrow_schema::DataType;
use parquet::arrow::arrow_reader::ParquetRecordBatchReaderBuilder;
use rand::{Rng, SeedableRng};
use rand_chacha::ChaCha8Rng;
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, HashMap};
use std::fs::{self, File};
use std::path::Path;

fn d_q() -> usize { 5 }
fn d_min() -> usize { 20 }
fn d_vol() -> String { "volume".into() }
fn d_block() -> usize { 5 }
fn d_alpha() -> f64 { 0.05 }

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct Spec {
    pub name: String,
    pub factors: String,
    pub prices: String,
    #[serde(default = "d_vol")]
    pub vol: String,
    #[serde(default)]
    pub funding: Option<String>,
    pub start: String,
    pub end: String,
    /// hours
    pub horizons: Vec<i64>,
    /// hours between decision dates (the net spread is for h == step_h)
    pub step_h: i64,
    #[serde(default = "d_q")]
    pub quantiles: usize,
    #[serde(default = "d_min")]
    pub min_names: usize,
    /// per side
    pub cost: f64,
    pub reps: usize,
    pub seed: u64,
    #[serde(default = "d_block")]
    pub min_block: usize,
    #[serde(default = "d_alpha")]
    pub alpha: f64,
    pub out: String,
}

pub struct Table {
    pub t: Vec<i64>,
    pub sym: Vec<String>,
    pub names: Vec<String>,
    pub cols: Vec<Vec<f64>>,
}

pub fn read_table(path: &Path) -> Result<Table> {
    let file = File::open(path).with_context(|| format!("open {}", path.display()))?;
    let reader = ParquetRecordBatchReaderBuilder::try_new(file)?.build()?;
    let mut tb = Table { t: vec![], sym: vec![], names: vec![], cols: vec![] };
    for batch in reader {
        let batch = batch?;
        if tb.names.is_empty() {
            tb.names = batch.schema().fields().iter().map(|f| f.name().clone()).filter(|n| n != "t" && n != "sym").collect();
            tb.cols = vec![Vec::new(); tb.names.len()];
        }
        let t = cast(batch.column_by_name("t").ok_or_else(|| anyhow!("no t column"))?, &DataType::Int64)?;
        let t = t.as_any().downcast_ref::<Int64Array>().unwrap();
        tb.t.extend((0..t.len()).map(|i| t.value(i)));
        let s = cast(batch.column_by_name("sym").ok_or_else(|| anyhow!("no sym column"))?, &DataType::Utf8)?;
        let s = s.as_any().downcast_ref::<StringArray>().unwrap();
        tb.sym.extend((0..s.len()).map(|i| s.value(i).to_string()));
        for (k, n) in tb.names.iter().enumerate() {
            let c = cast(batch.column_by_name(n).unwrap(), &DataType::Float64)?;
            let c = c.as_any().downcast_ref::<arrow_array::Float64Array>().unwrap();
            tb.cols[k].extend((0..c.len()).map(|i| if c.is_null(i) { f64::NAN } else { c.value(i) }));
        }
    }
    Ok(tb)
}

/// Average ranks (1-based), ties share their mean rank.
pub fn ranks(x: &[f64]) -> Vec<f64> {
    let mut idx: Vec<usize> = (0..x.len()).collect();
    idx.sort_by(|&a, &b| x[a].total_cmp(&x[b]));
    let mut r = vec![0.0; x.len()];
    let mut i = 0;
    while i < idx.len() {
        let mut j = i;
        while j + 1 < idx.len() && x[idx[j + 1]] == x[idx[i]] {
            j += 1;
        }
        let avg = (i + j) as f64 / 2.0 + 1.0;
        for k in i..=j {
            r[idx[k]] = avg;
        }
        i = j + 1;
    }
    r
}

pub fn pearson(x: &[f64], y: &[f64]) -> f64 {
    let (mx, my) = (stats::mean(x), stats::mean(y));
    let (mut a, mut b, mut c) = (0.0, 0.0, 0.0);
    for i in 0..x.len() {
        a += (x[i] - mx) * (y[i] - my);
        b += (x[i] - mx) * (x[i] - mx);
        c += (y[i] - my) * (y[i] - my);
    }
    if b > 0.0 && c > 0.0 { a / (b * c).sqrt() } else { f64::NAN }
}

/// Quantile of each element by factor rank, 0 = lowest; ties broken by position (the caller orders by symbol).
pub fn quantile_of(f: &[f64], q: usize) -> Vec<usize> {
    let n = f.len();
    let mut idx: Vec<usize> = (0..n).collect();
    idx.sort_by(|&a, &b| f[a].total_cmp(&f[b]).then(a.cmp(&b)));
    let mut out = vec![0; n];
    for (pos, &i) in idx.iter().enumerate() {
        out[i] = pos * q / n;
    }
    out
}

pub fn newey_west_t(x: &[f64], lags: usize) -> f64 {
    crate::spread::newey_west_t(x, lags)
}

/// One date's cross-section for one factor and horizon.
#[derive(Clone, Debug)]
pub struct Cross {
    pub n: usize,
    pub ic: f64,
    pub rank_ic: f64,
    pub q_means: Vec<f64>,
    pub ls: f64,
    pub top: Vec<usize>,
    pub bottom: Vec<usize>,
}

/// f and r aligned, `ids` the coins' indices (ascending), at least min_names finite pairs.
pub fn cross(f: &[f64], r: &[f64], ids: &[usize], q: usize, min_names: usize) -> Option<Cross> {
    let keep: Vec<usize> = (0..f.len()).filter(|&i| f[i].is_finite() && r[i].is_finite()).collect();
    if keep.len() < min_names.max(q) {
        return None;
    }
    let fx: Vec<f64> = keep.iter().map(|&i| f[i]).collect();
    let rx: Vec<f64> = keep.iter().map(|&i| r[i]).collect();
    let qs = quantile_of(&fx, q);
    let mut sums = vec![0.0; q];
    let mut cnt = vec![0usize; q];
    for (k, &b) in qs.iter().enumerate() {
        sums[b] += rx[k];
        cnt[b] += 1;
    }
    let q_means: Vec<f64> = (0..q).map(|b| if cnt[b] > 0 { sums[b] / cnt[b] as f64 } else { f64::NAN }).collect();
    Some(Cross {
        n: keep.len(),
        ic: pearson(&fx, &rx),
        rank_ic: pearson(&ranks(&fx), &ranks(&rx)),
        ls: q_means[q - 1] - q_means[0],
        q_means,
        top: keep.iter().zip(&qs).filter(|(_, b)| **b == q - 1).map(|(&i, _)| ids[i]).collect(),
        bottom: keep.iter().zip(&qs).filter(|(_, b)| **b == 0).map(|(&i, _)| ids[i]).collect(),
    })
}

fn churn(now: &[usize], prev: &[usize]) -> f64 {
    if now.is_empty() {
        return f64::NAN;
    }
    now.iter().filter(|x| prev.binary_search(x).is_err()).count() as f64 / now.len() as f64
}

#[derive(Clone, Debug, Serialize)]
pub struct FactorResult {
    pub factor: String,
    pub horizon_h: i64,
    pub dates: usize,
    pub mean_names: f64,
    pub ic: f64,
    pub rank_ic: f64,
    pub rank_ic_t: f64,
    pub rank_ic_ir: f64,
    pub rank_ic_pos: f64,
    pub q_mean_bp: Vec<f64>,
    pub monotonic: f64,
    pub ls_bp: f64,
    pub ls_t: f64,
    pub turnover_top: f64,
    pub turnover_bottom: f64,
    pub ls_net_bp: Option<f64>,
    pub ls_net_t: Option<f64>,
    pub ls_net_ann_pct: Option<f64>,
    pub p_rc: f64,
    pub rc_pass: bool,
}

#[derive(Serialize)]
pub struct Report {
    pub name: String,
    pub trials: usize,
    pub coins: usize,
    pub dates: usize,
    pub rc_null_p95: f64,
    pub block: usize,
    pub survivors: Vec<String>,
    pub results: Vec<FactorResult>,
    pub spec: Spec,
}

/// Block bootstrap of the max |t| over series that share one date axis (NaN = no value that date).
pub fn max_abs_t_null(x: &[Vec<f64>], block: usize, reps: usize, seed: u64) -> Vec<f64> {
    let n = x.first().map(|v| v.len()).unwrap_or(0);
    if n == 0 {
        return vec![];
    }
    let mu: Vec<f64> = x.iter().map(|v| stats::mean(&v.iter().copied().filter(|z| z.is_finite()).collect::<Vec<_>>())).collect();
    (0..reps).into_par_iter().map(|b| {
        let mut rng = ChaCha8Rng::seed_from_u64(seed.wrapping_add(b as u64));
        let mut idx = Vec::with_capacity(n + block);
        while idx.len() < n {
            let s = rng.gen_range(0..n);
            idx.extend((0..block).map(|i| (s + i) % n));
        }
        idx.truncate(n);
        let mut best = 0.0f64;
        for (j, v) in x.iter().enumerate() {
            let (mut k, mut s1, mut s2) = (0usize, 0.0, 0.0);
            for &i in &idx {
                if v[i].is_finite() {
                    let z = v[i] - mu[j];
                    k += 1;
                    s1 += z;
                    s2 += z * z;
                }
            }
            if k > 2 {
                let m = s1 / k as f64;
                let var = (s2 - k as f64 * m * m) / (k - 1) as f64;
                if var > 0.0 {
                    best = best.max((m / (var / k as f64).sqrt()).abs());
                }
            }
        }
        best
    }).collect()
}

pub fn run(spec: Spec, log: &dyn Fn(String)) -> Result<Report> {
    let tb = read_table(Path::new(&spec.factors))?;
    let ax = Axis::new(&spec.start, &spec.end)?;
    let mut syms: Vec<String> = tb.sym.clone();
    syms.sort();
    syms.dedup();
    let sid: HashMap<&str, usize> = syms.iter().enumerate().map(|(i, s)| (s.as_str(), i)).collect();
    let v = VenueSpec { name: "venue", klines: &spec.prices, vol: &spec.vol, funding: spec.funding.as_deref() };
    let src = data::load(&data::data_root(), &v, &syms, ax)?;
    log(format!("{} rows, {} factors, {} coins ({} with prices)", tb.t.len(), tb.names.len(), syms.len(), src.idx.len()));
    // rows by date, ordered by coin
    let mut by_date: BTreeMap<i64, Vec<usize>> = BTreeMap::new();
    for (i, &t) in tb.t.iter().enumerate() {
        let r0 = ax.row(t);
        if r0 >= 1 && (r0 as usize) < ax.n {
            by_date.entry(t).or_default().push(i);
        }
    }
    for rows in by_date.values_mut() {
        rows.sort_by_key(|&i| sid[tb.sym[i].as_str()]);
    }
    let dates: Vec<i64> = by_date.keys().copied().collect();
    let nh = spec.horizons.len();
    let nf = tb.names.len();
    // forward returns per date, horizon, row
    let fwd: Vec<Vec<Vec<f64>>> = dates.par_iter().map(|t| {
        let r0 = ax.row(*t);
        let rows = &by_date[t];
        spec.horizons.iter().map(|&h| rows.iter().map(|&i| {
            let Some(s) = src.get(&tb.sym[i]) else { return f64::NAN };
            let n = s.close.len() as i64;
            let xr = r0 + h;
            if !s.traded_at(r0) || xr + 1 >= n {
                return f64::NAN;
            }
            let jx = s.last[xr as usize];
            if jx < r0 {
                return f64::NAN;
            }
            s.close[jx as usize] / s.close[r0 as usize] - 1.0 - s.fund(r0, xr)
        }).collect()).collect()
    }).collect();
    // cross-sections: [factor][horizon][date]
    let cs: Vec<Vec<Vec<Option<Cross>>>> = (0..nf).into_par_iter().map(|k| {
        (0..nh).map(|hi| dates.iter().enumerate().map(|(di, t)| {
            let rows = &by_date[t];
            let f: Vec<f64> = rows.iter().map(|&i| tb.cols[k][i]).collect();
            let ids: Vec<usize> = rows.iter().map(|&i| sid[tb.sym[i].as_str()]).collect();
            cross(&f, &fwd[di][hi], &ids, spec.quantiles, spec.min_names)
        }).collect()).collect()
    }).collect();
    let block = spec.horizons.iter().map(|&h| ((h + spec.step_h - 1) / spec.step_h) as usize).max().unwrap_or(1).max(spec.min_block);
    let series: Vec<Vec<f64>> = (0..nf).flat_map(|k| (0..nh).map(move |hi| (k, hi)))
        .map(|(k, hi)| cs[k][hi].iter().map(|c| c.as_ref().map(|x| x.rank_ic).unwrap_or(f64::NAN)).collect()).collect();
    let null = max_abs_t_null(&series, block, spec.reps, spec.seed);
    let mut sorted = null.clone();
    sorted.sort_by(|a, b| a.total_cmp(b));
    let p95 = percentile(&sorted, 95.0);
    let mut results = Vec::new();
    for k in 0..nf {
        for (hi, &h) in spec.horizons.iter().enumerate() {
            let c: Vec<&Cross> = cs[k][hi].iter().flatten().collect();
            let lags = ((h + spec.step_h - 1) / spec.step_h).max(1) as usize;
            let ric: Vec<f64> = c.iter().map(|x| x.rank_ic).filter(|v| v.is_finite()).collect();
            let ic: Vec<f64> = c.iter().map(|x| x.ic).filter(|v| v.is_finite()).collect();
            let ls: Vec<f64> = c.iter().map(|x| x.ls).filter(|v| v.is_finite()).collect();
            let qm: Vec<f64> = (0..spec.quantiles).map(|b| stats::mean(&c.iter().map(|x| x.q_means[b]).filter(|v| v.is_finite()).collect::<Vec<_>>()) * 1e4).collect();
            // turnover between consecutive dates that both have a cross-section
            let (mut tt, mut tbm, mut net) = (Vec::new(), Vec::new(), Vec::new());
            let mut prev: Option<&Cross> = None;
            for x in cs[k][hi].iter() {
                match (x, prev) {
                    (Some(x), Some(p)) => {
                        let mut pt = p.top.clone();
                        pt.sort();
                        let mut pb = p.bottom.clone();
                        pb.sort();
                        let (a, b) = (churn(&x.top, &pt), churn(&x.bottom, &pb));
                        tt.push(a);
                        tbm.push(b);
                        net.push(x.ls - 2.0 * spec.cost * (a + b));
                    }
                    (Some(x), None) => net.push(x.ls - 2.0 * spec.cost * 2.0),
                    _ => {}
                }
                prev = x.as_ref().or(prev);
            }
            let sd = stats::sd1(&ric);
            let t_ric = newey_west_t(&ric, lags);
            let p_rc = if t_ric.is_finite() { (1 + null.iter().filter(|&&v| v >= t_ric.abs()).count()) as f64 / (spec.reps + 1) as f64 } else { 1.0 };
            let netting = h == spec.step_h;
            results.push(FactorResult {
                factor: tb.names[k].clone(), horizon_h: h, dates: c.len(),
                mean_names: stats::mean(&c.iter().map(|x| x.n as f64).collect::<Vec<_>>()),
                ic: stats::mean(&ic), rank_ic: stats::mean(&ric), rank_ic_t: t_ric,
                rank_ic_ir: if sd > 0.0 { stats::mean(&ric) / sd } else { f64::NAN },
                rank_ic_pos: ric.iter().filter(|v| **v > 0.0).count() as f64 / ric.len().max(1) as f64,
                monotonic: pearson(&(0..spec.quantiles).map(|b| b as f64).collect::<Vec<_>>(), &qm),
                q_mean_bp: qm,
                ls_bp: stats::mean(&ls) * 1e4, ls_t: newey_west_t(&ls, lags),
                turnover_top: stats::mean(&tt), turnover_bottom: stats::mean(&tbm),
                ls_net_bp: netting.then(|| stats::mean(&net) * 1e4),
                ls_net_t: netting.then(|| newey_west_t(&net, 1)),
                ls_net_ann_pct: netting.then(|| stats::mean(&net) * (365.0 * 24.0 / h as f64) * 100.0),
                p_rc, rc_pass: p_rc < spec.alpha,
            });
        }
    }
    results.sort_by(|a, b| b.rank_ic_t.abs().total_cmp(&a.rank_ic_t.abs()));
    let out = Path::new(&spec.out);
    fs::create_dir_all(out)?;
    let mut w = csv::Writer::from_path(out.join("ic.csv"))?;
    w.write_record(["factor", "horizon_h", "t", "names", "ic", "rank_ic", "ls"])?;
    for k in 0..nf {
        for (hi, &h) in spec.horizons.iter().enumerate() {
            for (di, x) in cs[k][hi].iter().enumerate() {
                if let Some(x) = x {
                    w.write_record([tb.names[k].clone(), h.to_string(), dates[di].to_string(),
                        x.n.to_string(), format!("{:.6}", x.ic), format!("{:.6}", x.rank_ic),
                        format!("{:.8}", x.ls)])?;
                }
            }
        }
    }
    w.flush()?;
    let rep = Report {
        name: spec.name.clone(), trials: nf * nh, coins: syms.len(), dates: dates.len(), rc_null_p95: p95, block,
        survivors: results.iter().filter(|r| r.rc_pass).map(|r| format!("{} {}h", r.factor, r.horizon_h)).collect(),
        results, spec: spec.clone(),
    };
    fs::write(out.join("report.json"), serde_json::to_string_pretty(&rep)?.replace("NaN", "null"))?;
    Ok(rep)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ranks_and_quantiles() {
        assert_eq!(ranks(&[3.0, 1.0, 2.0, 2.0]), vec![4.0, 1.0, 2.5, 2.5]);
        assert_eq!(quantile_of(&[5.0, 1.0, 3.0, 2.0, 4.0], 5), vec![4, 0, 2, 1, 3]);
        assert_eq!(quantile_of(&[1.0, 1.0, 1.0, 1.0], 2), vec![0, 0, 1, 1]);   // ties by position
        assert!((pearson(&[1.0, 2.0, 3.0], &[2.0, 4.0, 6.0]) - 1.0).abs() < 1e-12);
    }

    #[test]
    fn cross_section_reads_a_planted_factor() {
        // the factor is the coming return: IC 1, top minus bottom = mean of top 20% minus bottom 20%
        let r: Vec<f64> = (0..50).map(|i| i as f64 / 1000.0).collect();
        let f = r.clone();
        let ids: Vec<usize> = (0..50).collect();
        let c = cross(&f, &r, &ids, 5, 20).unwrap();
        assert!((c.ic - 1.0).abs() < 1e-12 && (c.rank_ic - 1.0).abs() < 1e-12);
        assert!((c.ls - (0.0445 - 0.0045)).abs() < 1e-12);
        assert_eq!(c.top, (40..50).collect::<Vec<_>>());
        assert!(cross(&f[..10], &r[..10], &ids[..10], 5, 20).is_none());          // too few names
        let mut g = f.clone();
        g[3] = f64::NAN;
        assert_eq!(cross(&g, &r, &ids, 5, 20).unwrap().bottom.len(), 10);         // 49 names: positions 0..9 are bottom
        assert_eq!(churn(&[1, 2, 3, 4], &[3, 4, 5, 6]), 0.5);
    }

    #[test]
    fn null_bootstrap() {
        let noise: Vec<f64> = (0..400).map(|i| ((i * 7919) % 97) as f64 / 97.0 - 0.5).collect();
        let strong: Vec<f64> = noise.iter().map(|v| v * 0.1 + 0.05).collect();
        let null = max_abs_t_null(&[noise.clone(), strong.clone()], 5, 300, 3);
        let mut s = null.clone();
        s.sort_by(|a, b| a.total_cmp(b));
        assert!(stats::tstat(&strong) > percentile(&s, 95.0));
        assert!(stats::tstat(&noise).abs() < percentile(&s, 95.0));
    }
}
