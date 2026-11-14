//! Cross-venue funding carry ("funding arbitrage"): hold one coin long on the venue where its funding is lower and short
//! on the venue where it is higher, so the price legs cancel and the funding difference is collected. A family of daily
//! books (venue set x lookback x entry threshold x slots), decided together.
//!
//! Accounting, on a daily axis where day d is the instant start + d days (00:00 UTC):
//! - A venue's close on day d is its last traded close at or before that instant (hourly bars, or daily bars for a venue
//!   that only serves daily history). It is fresh on day d when the bar ending at that instant traded. Rows before
//!   `start` are dropped as they are read (a start before 2021 needs `reserved_prereg`, engine/src/reserved.rs).
//! - Funding settled in (day d - 1, day d] belongs to day d, settlement times floored to the hour. The long pays +rate and
//!   the short receives it. A pair opened at day d's close earns day d + 1's funding onward.
//! - Signal on day d: each venue's settled funding over the last L days, (day d - L, day d]. The spread is the higher
//!   minus the lower, annualized x 365 / L. A venue is eligible when it is fresh on day d and its funding history covers
//!   the whole window. A pair is eligible when the two venues' fresh daily returns over the last `corr_days` correlate at
//!   least `corr_min` (the same ticker is not proof of the same coin). A set of more than two venues takes, per coin, its
//!   widest eligible pair.
//! - A book with K slots enters the widest spreads >= threshold into free slots and holds while the held pair's own
//!   spread stays >= threshold / 2 (no switching). Entries and exits happen only on days both legs are fresh, except a
//!   leg whose venue never trades again (delisted), which closes at its last close. Each slot is 1/K of capital, posted
//!   1x on each leg, so a leg's notional is 1/(2K), reset daily (constant-notional marking).
//! - Net day = [sum over held pairs of (long return - short return + short funding - long funding)
//!   - cost x legs traded] / (2K). Pairs still open on the last day pay their exit.
//!
//! Family decision: a moving-block bootstrap of days (the same blocks for every strategy, each centred on its own mean)
//! gives the null of the family's maximum t. A strategy passes when its 1x t beats that null (p_rc < alpha), its
//! Newey-West t is above 2, both halves, the days from `recent_from` and the 1%-trimmed mean are positive at 1x, its 1x
//! annual net reaches `hurdle_ann_pct`, and its 2x mean is positive.

use crate::data::{self, H};
use crate::events::percentile;
use crate::stats;
use anyhow::{Context, Result, anyhow};
use rand::{Rng, SeedableRng};
use rand_chacha::ChaCha8Rng;
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::fs;
use std::path::Path;

pub const DAY: i64 = 86_400_000;

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct VenueCfg {
    pub name: String,
    /// folder of `<symbol>.parquet` with t (bar open, ms), close and the volume column
    pub prices: String,
    pub vol: String,
    /// folder of `<symbol>.parquet` with t (settlement, ms) and rate
    pub funding: String,
    /// bar length in hours (1, or 24 for daily history)
    #[serde(default = "d_bar")]
    pub bar_h: i64,
}

fn d_bar() -> i64 { 1 }
fn d_alpha() -> f64 { 0.05 }
fn d_y25() -> String { "2025-01-01".into() }
fn d_trim() -> f64 { 0.01 }
fn d_nw() -> usize { 10 }
fn d_keep() -> usize { 10 }

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct Spec {
    pub name: String,
    pub start: String,
    pub end: String,
    /// CSV: `key` then one column per venue name holding that venue's file stem (empty = not listed there)
    pub symbols: String,
    pub venues: Vec<VenueCfg>,
    /// A frozen batch PREREG that declares the reserved samples this spec reads (engine/src/reserved.rs).
    #[serde(default)]
    pub reserved_prereg: Option<String>,
    pub sets: Vec<Vec<String>>,
    /// days
    pub lookbacks: Vec<usize>,
    /// annualized spread to enter; a held pair exits below half of it
    pub thresholds: Vec<f64>,
    pub slots: Vec<usize>,
    /// cost per leg per side at 1x, 2x, 3x
    pub costs: Vec<f64>,
    pub corr_days: usize,
    pub corr_min: f64,
    pub corr_obs: usize,
    pub block_days: usize,
    pub reps: usize,
    pub seed: u64,
    pub out: String,
    #[serde(default = "d_alpha")]
    pub alpha: f64,
    #[serde(default = "d_y25")]
    pub recent_from: String,
    #[serde(default = "d_trim")]
    pub trim: f64,
    #[serde(default = "d_nw")]
    pub nw_lags: usize,
    /// daily rows are written for the survivors and this many best strategies
    #[serde(default = "d_keep")]
    pub keep_daily: usize,
    /// a strategy's 1x annual net must reach this (percent; a T-bill pays it without risk)
    #[serde(default)]
    pub hurdle_ann_pct: f64,
}

/// One coin on one venue, on the daily axis (instants 0..nd).
#[derive(Clone, Debug)]
pub struct Daily {
    pub close: Vec<f64>,
    pub fresh: Vec<bool>,
    /// cumf[d] = funding settled in (day 0, day d]; cumn counts the settlements
    pub cumf: Vec<f64>,
    pub cumn: Vec<u32>,
    pub first_fund: usize,
    pub last_fresh: i64,
}

impl Daily {
    /// Settled funding over (day d - l, day d], if the venue's history covers the whole window.
    pub fn window(&self, d: usize, l: usize) -> Option<f64> {
        if d < l || self.first_fund > d + 1 - l || self.cumn[d] == self.cumn[d - l] {
            return None;
        }
        Some(self.cumf[d] - self.cumf[d - l])
    }
    pub fn fund_on(&self, d: usize) -> f64 {
        self.cumf[d] - self.cumf[d - 1]
    }
    /// Close-to-close return d -> d + 1 on the marking closes (0 while the venue has no price yet).
    pub fn ret(&self, d: usize) -> f64 {
        let (a, b) = (self.close[d], self.close[d + 1]);
        if a.is_finite() && b.is_finite() && a > 0.0 { b / a - 1.0 } else { 0.0 }
    }
}

/// Daily closes from bars (t = bar open): the last traded bar ending in (day d - 1, day d] marks day d, carried forward.
pub fn daily_prices(t: &[f64], close: &[f64], vol: &[f64], bar_ms: i64, t0: i64, nd: usize) -> (Vec<f64>, Vec<bool>) {
    let mut day_close = vec![f64::NAN; nd];
    let mut day_t = vec![i64::MIN; nd];
    let mut fresh = vec![false; nd];
    for i in 0..t.len() {
        if !t[i].is_finite() {
            continue;
        }
        let ti = t[i] as i64;
        if ti < t0 || !(close[i].is_finite() && close[i] > 0.0 && vol[i].is_finite() && vol[i] > 0.0) {
            continue;
        }
        let end = ti + bar_ms;
        let d = (end - t0 + DAY - 1).div_euclid(DAY);
        if d < 0 || d as usize >= nd {
            continue;
        }
        let d = d as usize;
        if ti > day_t[d] {
            day_t[d] = ti;
            day_close[d] = close[i];
        }
        if end == t0 + d as i64 * DAY {
            fresh[d] = true;
        }
    }
    let mut out = vec![f64::NAN; nd];
    let mut last = f64::NAN;
    for d in 0..nd {
        if day_close[d].is_finite() {
            last = day_close[d];
        }
        out[d] = last;
    }
    (out, fresh)
}

/// Settled funding per day: a settlement at time s (floored to the hour) belongs to day ceil((s - t0) / DAY).
pub fn daily_funding(t: &[f64], rate: &[f64], t0: i64, nd: usize) -> (Vec<f64>, Vec<u32>) {
    let mut f = vec![0.0; nd];
    let mut n = vec![0u32; nd];
    for i in 0..t.len() {
        if !t[i].is_finite() || !rate[i].is_finite() {
            continue;
        }
        let ti = t[i] as i64;
        if ti < t0 {
            continue;
        }
        let th = ti - ti.rem_euclid(H);
        let d = (th - t0 + DAY - 1).div_euclid(DAY);
        if d < 1 || d as usize >= nd {
            continue;
        }
        f[d as usize] += rate[i];
        n[d as usize] += 1;
    }
    (f, n)
}

pub fn assemble(close: Vec<f64>, fresh: Vec<bool>, f: &[f64], n: &[u32]) -> Daily {
    let nd = close.len();
    let mut cumf = vec![0.0; nd];
    let mut cumn = vec![0u32; nd];
    for d in 1..nd {
        cumf[d] = cumf[d - 1] + f[d];
        cumn[d] = cumn[d - 1] + n[d];
    }
    let first_fund = (1..nd).find(|&d| n[d] > 0).unwrap_or(usize::MAX);
    let last_fresh = (0..nd).rev().find(|&d| fresh[d]).map(|d| d as i64).unwrap_or(-1);
    Daily { close, fresh, cumf, cumn, first_fund, last_fresh }
}

fn load_daily(root: &Path, v: &VenueCfg, sym: &str, t0: i64, nd: usize) -> Result<Option<Daily>> {
    let pp = root.join(&v.prices).join(format!("{sym}.parquet"));
    let fp = root.join(&v.funding).join(format!("{sym}.parquet"));
    if !pp.exists() || !fp.exists() {
        return Ok(None);
    }
    let c = data::read_cols(&pp, &["t", "close", &v.vol])?;
    let (close, fresh) = daily_prices(&c[0], &c[1], &c[2], v.bar_h * H, t0, nd);
    let g = data::read_cols(&fp, &["t", "rate"])?;
    let (f, n) = daily_funding(&g[0], &g[1], t0, nd);
    Ok(Some(assemble(close, fresh, &f, &n)))
}

/// Pearson correlation of the two venues' fresh daily returns over (d - days, d], if at least `min_obs` days.
pub fn pair_corr(a: &Daily, b: &Daily, d: usize, days: usize, min_obs: usize) -> Option<f64> {
    let mut x = Vec::with_capacity(days);
    let mut y = Vec::with_capacity(days);
    for k in (d + 1).saturating_sub(days).max(1)..=d {
        if a.fresh[k] && a.fresh[k - 1] && b.fresh[k] && b.fresh[k - 1] {
            x.push((a.close[k] / a.close[k - 1]).ln());
            y.push((b.close[k] / b.close[k - 1]).ln());
        }
    }
    if x.len() < min_obs.max(3) {
        return None;
    }
    let (mx, my) = (stats::mean(&x), stats::mean(&y));
    let (mut sxy, mut sxx, mut syy) = (0.0, 0.0, 0.0);
    for i in 0..x.len() {
        sxy += (x[i] - mx) * (y[i] - my);
        sxx += (x[i] - mx) * (x[i] - mx);
        syy += (y[i] - my) * (y[i] - my);
    }
    if sxx > 0.0 && syy > 0.0 { Some(sxy / (sxx * syy).sqrt()) } else { None }
}

/// Coins and their venues: series[coin][venue] (None = not listed there or no file).
pub struct Universe {
    pub keys: Vec<String>,
    pub series: Vec<Vec<Option<Daily>>>,
    pub nd: usize,
    pub t0: i64,
}

pub fn load_universe(spec: &Spec, log: &dyn Fn(String)) -> Result<Universe> {
    let t0 = data::ms(&spec.start)?;
    let nd = ((data::ms(&spec.end)? + DAY - t0) / DAY + 1) as usize;
    let root = data::data_root();
    let mut rdr = csv::Reader::from_path(&spec.symbols).with_context(|| format!("symbols {}", spec.symbols))?;
    let hdr: Vec<String> = rdr.headers()?.iter().map(String::from).collect();
    let col: Vec<usize> = spec.venues.iter().map(|v| hdr.iter().position(|h| h == &v.name)
        .ok_or_else(|| anyhow!("symbols has no column {}", v.name))).collect::<Result<_>>()?;
    let kcol = hdr.iter().position(|h| h == "key").ok_or_else(|| anyhow!("symbols has no key column"))?;
    let rows: Vec<Vec<String>> = rdr.records().map(|r| r.map(|r| r.iter().map(String::from).collect())).collect::<Result<_, _>>()?;
    let series: Vec<Vec<Option<Daily>>> = rows.par_iter().map(|r| {
        spec.venues.iter().zip(&col).map(|(v, &c)| {
            let sym = r[c].trim();
            if sym.is_empty() { Ok(None) } else { load_daily(&root, v, sym, t0, nd) }
        }).collect::<Result<Vec<_>>>()
    }).collect::<Result<_>>()?;
    let keys: Vec<String> = rows.iter().map(|r| r[kcol].clone()).collect();
    for (j, v) in spec.venues.iter().enumerate() {
        log(format!("{}: {} coins with prices and funding", v.name, series.iter().filter(|s| s[j].is_some()).count()));
    }
    Ok(Universe { keys, series, nd, t0 })
}

#[derive(Clone, Copy, Debug)]
pub struct Cand {
    pub lo: usize,
    pub hi: usize,
    pub spread: f64,
}

/// Per day and coin, the widest eligible pair of the set (venue indices), for one lookback.
pub fn candidates(u: &Universe, set: &[usize], l: usize, corr: &(dyn Fn(usize, usize, usize, usize) -> bool + Sync))
    -> Vec<Vec<Option<Cand>>> {
    (0..u.nd).into_par_iter().map(|d| {
        u.series.iter().enumerate().map(|(c, sv)| {
            let mut best: Option<Cand> = None;
            for (i, &a) in set.iter().enumerate() {
                let Some(sa) = sv[a].as_ref() else { continue };
                if !sa.fresh[d] {
                    continue;
                }
                let Some(fa) = sa.window(d, l) else { continue };
                for &b in &set[i + 1..] {
                    let Some(sb) = sv[b].as_ref() else { continue };
                    if !sb.fresh[d] {
                        continue;
                    }
                    let Some(fb) = sb.window(d, l) else { continue };
                    let (lo, hi, w) = if fa <= fb { (a, b, fb - fa) } else { (b, a, fa - fb) };
                    let s = w * 365.0 / l as f64;
                    if best.map(|x| s > x.spread).unwrap_or(true) && corr(c, a, b, d) {
                        best = Some(Cand { lo, hi, spread: s });
                    }
                }
            }
            best
        }).collect()
    }).collect()
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub struct Strat {
    pub set: String,
    pub lookback: usize,
    pub threshold: f64,
    pub slots: usize,
}

impl Strat {
    pub fn label(&self) -> String {
        format!("{} L{}d th{}% K{}", self.set, self.lookback, (self.threshold * 100.0).round() as i64, self.slots)
    }
}

/// One book's days: index d holds the return of the interval day d -> d + 1 (before costs), its funding part, the legs
/// traded at day d's close (charged on that interval), and the pairs held over it.
#[derive(Clone, Debug, Default)]
pub struct Book {
    pub w0: usize,
    pub gross: Vec<f64>,
    pub funding: Vec<f64>,
    pub legs: Vec<f64>,
    pub held: Vec<f64>,
    pub trades: Vec<Trade>,
}

#[derive(Clone, Debug, Serialize)]
pub struct Trade {
    pub coin: String,
    pub long: String,
    pub short: String,
    pub entry_day: usize,
    pub exit_day: Option<usize>,
    pub spread_in: f64,
    pub price_pnl: f64,
    pub funding_pnl: f64,
    pub forced: bool,
}

/// Run one book. Both returns are per unit of one leg's notional; divide by 2K for the book.
pub fn simulate(u: &Universe, cand: &[Vec<Option<Cand>>], w0: usize, l: usize, th: f64, k: usize, names: &[String]) -> Book {
    let nd = u.nd;
    let mut b = Book { w0, gross: vec![0.0; nd], funding: vec![0.0; nd], legs: vec![0.0; nd], held: vec![0.0; nd], trades: vec![] };
    // open: (coin, lo, hi, trade index)
    let mut open: Vec<(usize, usize, usize, usize)> = Vec::new();
    for d in w0..nd - 1 {
        let s = &u.series;
        // exits
        let mut keep = Vec::with_capacity(open.len());
        for &(c, lo, hi, ti) in &open {
            let (a, h) = (s[c][lo].as_ref().unwrap(), s[c][hi].as_ref().unwrap());
            let forced = a.last_fresh < d as i64 || h.last_fresh < d as i64;
            let mut exit = forced;
            if !forced && a.fresh[d] && h.fresh[d] {
                let w = match (a.window(d, l), h.window(d, l)) {
                    (Some(fa), Some(fh)) => Some((fh - fa) * 365.0 / l as f64),
                    _ => None,
                };
                exit = w.map(|x| x < th / 2.0).unwrap_or(true);
            }
            if exit {
                b.legs[d] += 2.0;
                b.trades[ti].exit_day = Some(d);
                b.trades[ti].forced = forced;
            } else {
                keep.push((c, lo, hi, ti));
            }
        }
        open = keep;
        // entries
        if open.len() < k {
            let held: BTreeSet<usize> = open.iter().map(|x| x.0).collect();
            let mut cs: Vec<(usize, Cand)> = cand[d].iter().enumerate()
                .filter_map(|(c, x)| x.filter(|x| x.spread >= th && !held.contains(&c)).map(|x| (c, x))).collect();
            cs.sort_by(|x, y| y.1.spread.partial_cmp(&x.1.spread).unwrap().then(x.0.cmp(&y.0)));
            for (c, x) in cs.into_iter().take(k - open.len()) {
                b.legs[d] += 2.0;
                b.trades.push(Trade { coin: u.keys[c].clone(), long: names[x.lo].clone(), short: names[x.hi].clone(),
                    entry_day: d, exit_day: None, spread_in: x.spread, price_pnl: 0.0, funding_pnl: 0.0, forced: false });
                open.push((c, x.lo, x.hi, b.trades.len() - 1));
            }
        }
        // the interval d -> d + 1
        for &(c, lo, hi, ti) in &open {
            let (a, h) = (s[c][lo].as_ref().unwrap(), s[c][hi].as_ref().unwrap());
            let price = a.ret(d) - h.ret(d);
            let fund = h.fund_on(d + 1) - a.fund_on(d + 1);
            b.gross[d] += price + fund;
            b.funding[d] += fund;
            b.trades[ti].price_pnl += price;
            b.trades[ti].funding_pnl += fund;
        }
        b.held[d] = open.len() as f64;
    }
    // pairs open at the end pay their exit on the last interval
    if nd >= 2 {
        b.legs[nd - 2] += 2.0 * open.len() as f64;
    }
    b
}

/// Per-day net of a book at one cost, over its window [w0, nd - 1).
pub fn net(b: &Book, k: usize, cost: f64) -> Vec<f64> {
    (b.w0..b.gross.len() - 1).map(|d| (b.gross[d] - cost * b.legs[d]) / (2.0 * k as f64)).collect()
}

pub fn newey_west_t(x: &[f64], lags: usize) -> f64 {
    let n = x.len();
    if n < 3 {
        return f64::NAN;
    }
    let m = stats::mean(x);
    let e: Vec<f64> = x.iter().map(|v| v - m).collect();
    let mut lrv = e.iter().map(|v| v * v).sum::<f64>() / n as f64;
    for j in 1..=lags.min(n - 2) {
        let c: f64 = (j..n).map(|i| e[i] * e[i - j]).sum::<f64>() / n as f64;
        lrv += 2.0 * (1.0 - j as f64 / (lags + 1) as f64) * c;
    }
    if lrv > 0.0 { m / (lrv / n as f64).sqrt() } else { f64::NAN }
}

#[derive(Clone, Debug, Default, Serialize)]
pub struct DayStats {
    pub days: usize,
    pub mean_bp: f64,
    pub ann_pct: f64,
    pub vol_pct: f64,
    pub sharpe: f64,
    pub t: f64,
    pub t_nw: f64,
    pub half1_bp: f64,
    pub half2_bp: f64,
    pub recent_bp: f64,
    pub recent_days: usize,
    pub trimmed_bp: f64,
    pub max_dd_pct: f64,
    pub top10_share: f64,
    pub total_pct: f64,
}

pub fn day_stats(x: &[f64], first_day: usize, recent_day: usize, trim: f64, lags: usize) -> DayStats {
    let n = x.len();
    if n < 3 {
        return DayStats { days: n, ..Default::default() };
    }
    let m = stats::mean(x);
    let sd = stats::sd1(x);
    let half = n / 2;
    let rec: Vec<f64> = x.iter().enumerate().filter(|(i, _)| first_day + i >= recent_day).map(|(_, v)| *v).collect();
    let mut s = x.to_vec();
    s.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let cut = (trim * n as f64).floor() as usize;
    let trimmed = if n > 2 * cut { stats::mean(&s[cut..n - cut]) } else { f64::NAN };
    let (mut eq, mut peak, mut dd) = (1.0f64, 1.0f64, 0.0f64);
    for v in x {
        eq *= 1.0 + v;
        peak = peak.max(eq);
        dd = dd.min(eq / peak - 1.0);
    }
    let sum: f64 = x.iter().sum();
    let top: f64 = s.iter().rev().take(10).sum();
    DayStats {
        days: n,
        mean_bp: m * 1e4,
        ann_pct: m * 365.0 * 100.0,
        vol_pct: sd * 365f64.sqrt() * 100.0,
        sharpe: if sd > 0.0 { m / sd * 365f64.sqrt() } else { f64::NAN },
        t: stats::tstat(x),
        t_nw: newey_west_t(x, lags),
        half1_bp: stats::mean(&x[..half]) * 1e4,
        half2_bp: stats::mean(&x[half..]) * 1e4,
        recent_bp: if rec.is_empty() { f64::NAN } else { stats::mean(&rec) * 1e4 },
        recent_days: rec.len(),
        trimmed_bp: trimmed * 1e4,
        max_dd_pct: dd * 100.0,
        top10_share: if sum != 0.0 { top / sum } else { f64::NAN },
        total_pct: (eq - 1.0) * 100.0,
    }
}

/// Moving-block bootstrap of days under the null of no mean: the family's max t in each replication.
/// `x[j]` is strategy j's series over its window, which starts at axis day `w0[j]`; every strategy uses the same blocks.
pub fn block_rc(x: &[Vec<f64>], w0: &[usize], axis: usize, block: usize, reps: usize, seed: u64) -> Vec<f64> {
    let mu: Vec<f64> = x.iter().map(|v| stats::mean(v)).collect();
    let block = block.max(1);
    (0..reps).into_par_iter().map(|b| {
        let mut rng = ChaCha8Rng::seed_from_u64(seed.wrapping_add(b as u64));
        let mut idx = Vec::with_capacity(axis + block);
        while idx.len() < axis {
            let s = rng.gen_range(0..axis);
            idx.extend((0..block).map(|i| (s + i) % axis));
        }
        idx.truncate(axis);
        let mut best = f64::NEG_INFINITY;
        for j in 0..x.len() {
            let (mut n, mut s1, mut s2) = (0usize, 0.0f64, 0.0f64);
            for &i in &idx {
                if i >= w0[j] && i - w0[j] < x[j].len() {
                    let v = x[j][i - w0[j]] - mu[j];
                    n += 1;
                    s1 += v;
                    s2 += v * v;
                }
            }
            if n > 2 {
                let m = s1 / n as f64;
                let var = (s2 - n as f64 * m * m) / (n - 1) as f64;
                if var > 0.0 {
                    best = best.max(m / (var / n as f64).sqrt());
                }
            }
        }
        best
    }).collect()
}

#[derive(Clone, Debug, Serialize)]
pub struct StratResult {
    pub label: String,
    pub strat: Strat,
    pub window_from: String,
    /// at 1x, 2x, 3x
    pub stats: Vec<DayStats>,
    pub funding_share: f64,
    pub avg_held: f64,
    pub trades: usize,
    pub forced_exits: usize,
    pub p_rc: f64,
    pub gates: BTreeMap<String, bool>,
    pub pass: bool,
}

#[derive(Clone, Debug, Serialize)]
pub struct SetInfo {
    pub set: String,
    pub lookback: usize,
    pub window_from: String,
    pub coins_ever: usize,
    /// mean coins per day whose widest eligible spread is >= each threshold
    pub mean_candidates: BTreeMap<String, f64>,
}

#[derive(Serialize)]
pub struct Report {
    pub name: String,
    pub trials: usize,
    pub coins: usize,
    pub coins_by_venue: BTreeMap<String, usize>,
    pub rc_null_p95: f64,
    pub verdict: String,
    pub survivors: Vec<String>,
    pub sets: Vec<SetInfo>,
    pub strategies: Vec<StratResult>,
    pub spec: Spec,
}

fn day_str(t0: i64, d: usize) -> String {
    let ms = t0 + d as i64 * DAY;
    let z = ms.div_euclid(DAY) + 719468;
    let era = z.div_euclid(146097);
    let doe = z - era * 146097;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let dd = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    format!("{:04}-{:02}-{:02}", yoe + era * 400 + if m <= 2 { 1 } else { 0 }, m, dd)
}

pub fn run(spec: Spec, log: &dyn Fn(String)) -> Result<Report> {
    let mut paths: Vec<&str> = vec![spec.symbols.as_str()];
    for v in &spec.venues {
        paths.push(&v.prices);
        paths.push(&v.funding);
    }
    crate::reserved::check(&spec.start, &paths, spec.reserved_prereg.as_deref())?;
    let u = load_universe(&spec, log)?;
    let names: Vec<String> = spec.venues.iter().map(|v| v.name.clone()).collect();
    let vix: HashMap<&str, usize> = names.iter().enumerate().map(|(i, n)| (n.as_str(), i)).collect();
    let sets: Vec<Vec<usize>> = spec.sets.iter().map(|s| s.iter().map(|n| vix.get(n.as_str()).copied()
        .ok_or_else(|| anyhow!("set names unknown venue {n}"))).collect::<Result<_>>()).collect::<Result<_>>()?;
    // the correlation guard, per coin and venue pair, once
    let nv = names.len();
    let pairs: Vec<(usize, usize)> = (0..nv).flat_map(|a| (a + 1..nv).map(move |b| (a, b))).collect();
    let ok: HashMap<(usize, usize), Vec<Vec<bool>>> = pairs.iter().map(|&(a, b)| {
        let m: Vec<Vec<bool>> = u.series.par_iter().map(|sv| match (sv[a].as_ref(), sv[b].as_ref()) {
            (Some(x), Some(y)) => (0..u.nd).map(|d| pair_corr(x, y, d, spec.corr_days, spec.corr_obs)
                .map(|r| r >= spec.corr_min).unwrap_or(false)).collect(),
            _ => vec![false; u.nd],
        }).collect();
        ((a, b), m)
    }).collect();
    let corr = |c: usize, a: usize, b: usize, d: usize| ok[&(a.min(b), a.max(b))][c][d];
    let recent = ((data::ms(&spec.recent_from)? - u.t0) / DAY).max(0) as usize;
    let mut strats = Vec::new();
    let mut books: Vec<Book> = Vec::new();
    let mut infos = Vec::new();
    for (si, set) in sets.iter().enumerate() {
        let sname = spec.sets[si].join("+");
        for &l in &spec.lookbacks {
            let cand = candidates(&u, set, l, &corr);
            let w0 = (0..u.nd).find(|&d| cand[d].iter().any(|c| c.is_some())).unwrap_or(u.nd - 1);
            let live = u.nd - 1 - w0;
            let mut mc = BTreeMap::new();
            for &th in &spec.thresholds {
                let tot: usize = (w0..u.nd - 1).map(|d| cand[d].iter().filter(|c| c.map(|x| x.spread >= th).unwrap_or(false)).count()).sum();
                mc.insert(format!("{th:.2}"), if live > 0 { tot as f64 / live as f64 } else { f64::NAN });
            }
            let ever = (0..u.series.len()).filter(|&c| (w0..u.nd).any(|d| cand[d][c].is_some())).count();
            infos.push(SetInfo { set: sname.clone(), lookback: l, window_from: day_str(u.t0, w0), coins_ever: ever, mean_candidates: mc });
            let grid: Vec<(f64, usize)> = spec.thresholds.iter().flat_map(|&th| spec.slots.iter().map(move |&k| (th, k))).collect();
            let bs: Vec<Book> = grid.par_iter().map(|&(th, k)| simulate(&u, &cand, w0, l, th, k, &names)).collect();
            for ((th, k), b) in grid.into_iter().zip(bs) {
                strats.push(Strat { set: sname.clone(), lookback: l, threshold: th, slots: k });
                books.push(b);
            }
            log(format!("{sname} L{l}d: window from {}, {ever} coins ever eligible", day_str(u.t0, w0)));
        }
    }
    let x1: Vec<Vec<f64>> = strats.iter().zip(&books).map(|(s, b)| net(b, s.slots, spec.costs[0])).collect();
    let w0s: Vec<usize> = books.iter().map(|b| b.w0).collect();
    let tmax = block_rc(&x1, &w0s, u.nd - 1, spec.block_days, spec.reps, spec.seed);
    let mut sorted = tmax.clone();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let rc95 = percentile(&sorted, 95.0);
    let mut results: Vec<StratResult> = strats.iter().zip(&books).map(|(s, b)| {
        let st: Vec<DayStats> = spec.costs.iter().map(|&c| day_stats(&net(b, s.slots, c), b.w0, recent, spec.trim, spec.nw_lags)).collect();
        let t1 = st[0].t;
        let p_rc = if t1.is_finite() { (1 + tmax.iter().filter(|&&v| v >= t1).count()) as f64 / (spec.reps + 1) as f64 } else { 1.0 };
        let mut gates = BTreeMap::new();
        gates.insert("RC".to_string(), t1.is_finite() && p_rc < spec.alpha);
        gates.insert("NW".to_string(), st[0].t_nw > 2.0);
        gates.insert("HALVES".to_string(), st[0].half1_bp > 0.0 && st[0].half2_bp > 0.0);
        gates.insert("TRIM".to_string(), st[0].trimmed_bp > 0.0);
        gates.insert("RECENT".to_string(), st[0].recent_days > 0 && st[0].recent_bp > 0.0);
        gates.insert("HURDLE".to_string(), st[0].ann_pct >= spec.hurdle_ann_pct);
        if st.len() > 1 {
            gates.insert("COST2X".to_string(), st[1].mean_bp > 0.0);
        }
        let gsum: f64 = b.gross[b.w0..].iter().sum();
        let fsum: f64 = b.funding[b.w0..].iter().sum();
        let live = (u.nd - 1 - b.w0).max(1) as f64;
        StratResult {
            label: s.label(), strat: s.clone(), window_from: day_str(u.t0, b.w0), stats: st,
            funding_share: if gsum != 0.0 { fsum / gsum } else { f64::NAN },
            avg_held: b.held[b.w0..].iter().sum::<f64>() / live,
            trades: b.trades.len(), forced_exits: b.trades.iter().filter(|t| t.forced).count(),
            p_rc, pass: gates.values().all(|&g| g), gates,
        }
    }).collect();
    let order: Vec<usize> = {
        let mut o: Vec<usize> = (0..results.len()).collect();
        let key = |j: usize| { let t = results[j].stats[0].t; if t.is_finite() { t } else { f64::NEG_INFINITY } };
        o.sort_by(|&a, &b| key(b).total_cmp(&key(a)).then(a.cmp(&b)));      // books that never traded (t NaN) go last
        o
    };
    let survivors: Vec<String> = order.iter().filter(|&&j| results[j].pass).map(|&j| results[j].label.clone()).collect();
    let out = Path::new(&spec.out);
    fs::create_dir_all(out)?;
    // daily rows and trades for the survivors and the best few by 1x t
    let mut keep: Vec<usize> = order.iter().copied().filter(|&j| results[j].pass).collect();
    for &j in order.iter().take(spec.keep_daily) {
        if !keep.contains(&j) {
            keep.push(j);
        }
    }
    let mut w = csv::Writer::from_path(out.join("daily.csv"))?;
    w.write_record(["strategy", "date", "cost_multiple", "net", "gross", "funding", "legs", "held"])?;
    let mut wt = csv::Writer::from_path(out.join("trades.csv"))?;
    wt.write_record(["strategy", "coin", "long", "short", "entry", "exit", "spread_in_ann", "price_pnl", "funding_pnl", "forced"])?;
    for &j in &keep {
        let (s, b) = (&strats[j], &books[j]);
        for (m, &c) in spec.costs.iter().enumerate() {
            for (i, v) in net(b, s.slots, c).iter().enumerate() {
                let d = b.w0 + i;
                w.write_record([results[j].label.clone(), day_str(u.t0, d + 1), (m + 1).to_string(), format!("{v:.10}"),
                    format!("{:.10}", b.gross[d] / (2.0 * s.slots as f64)), format!("{:.10}", b.funding[d] / (2.0 * s.slots as f64)),
                    b.legs[d].to_string(), b.held[d].to_string()])?;
            }
        }
        for t in &b.trades {
            wt.write_record([results[j].label.clone(), t.coin.clone(), t.long.clone(), t.short.clone(), day_str(u.t0, t.entry_day),
                t.exit_day.map(|d| day_str(u.t0, d)).unwrap_or_default(), format!("{:.6}", t.spread_in),
                format!("{:.8}", t.price_pnl), format!("{:.8}", t.funding_pnl), t.forced.to_string()])?;
        }
    }
    w.flush()?;
    wt.flush()?;
    let mut cbv = BTreeMap::new();
    for (j, n) in names.iter().enumerate() {
        cbv.insert(n.clone(), u.series.iter().filter(|s| s[j].is_some()).count());
    }
    let mut ordered = Vec::with_capacity(results.len());
    let mut slots: Vec<Option<StratResult>> = results.drain(..).map(Some).collect();
    for &j in &order {
        ordered.push(slots[j].take().unwrap());
    }
    let rep = Report {
        name: spec.name.clone(), trials: strats.len(), coins: u.keys.len(), coins_by_venue: cbv, rc_null_p95: rc95,
        verdict: if survivors.is_empty() { "NULL".into() } else { "PASS (gate 0)".into() },
        survivors, sets: infos, strategies: ordered, spec: spec.clone(),
    };
    let mut wc = csv::Writer::from_path(out.join("strategies.csv"))?;
    wc.write_record(["label", "set", "lookback_d", "threshold", "slots", "window_from", "days", "ann_1x_pct", "ann_2x_pct",
        "ann_3x_pct", "sharpe_1x", "t_1x", "t_nw_1x", "p_rc", "half1_bp", "half2_bp", "recent_bp", "trimmed_bp", "max_dd_pct",
        "top10_share", "funding_share", "avg_held", "trades", "forced_exits", "pass"])?;
    for r in &rep.strategies {
        let s = &r.stats;
        let a = |k: usize| s.get(k).map(|x| format!("{:.4}", x.ann_pct)).unwrap_or_default();
        wc.write_record([r.label.clone(), r.strat.set.clone(), r.strat.lookback.to_string(), r.strat.threshold.to_string(),
            r.strat.slots.to_string(), r.window_from.clone(), s[0].days.to_string(), a(0), a(1), a(2),
            format!("{:.4}", s[0].sharpe), format!("{:.4}", s[0].t), format!("{:.4}", s[0].t_nw), format!("{:.5}", r.p_rc),
            format!("{:.4}", s[0].half1_bp), format!("{:.4}", s[0].half2_bp), format!("{:.4}", s[0].recent_bp),
            format!("{:.4}", s[0].trimmed_bp), format!("{:.4}", s[0].max_dd_pct), format!("{:.4}", s[0].top10_share),
            format!("{:.4}", r.funding_share), format!("{:.3}", r.avg_held), r.trades.to_string(), r.forced_exits.to_string(),
            r.pass.to_string()])?;
    }
    wc.flush()?;
    fs::write(out.join("report.json"), serde_json::to_string_pretty(&rep)?.replace("NaN", "null"))?;
    Ok(rep)
}

#[cfg(test)]
mod tests {
    use super::*;

    const T0: i64 = 1_609_459_200_000; // 2021-01-01

    fn flat(nd: usize, price: f64, fund: f64) -> Daily {
        let f: Vec<f64> = (0..nd).map(|d| if d >= 1 { fund } else { 0.0 }).collect();
        let n: Vec<u32> = (0..nd).map(|d| if d >= 1 { 1 } else { 0 }).collect();
        assemble(vec![price; nd], vec![true; nd], &f, &n)
    }

    #[test]
    fn prices_and_funding_on_the_daily_axis() {
        // hourly bars: one opening 23:00 the day before start (dropped), one ending at day 1 exactly, one mid-day 2
        let t = [T0 - H, T0 + 23 * H, T0 + DAY + 5 * H];
        let c = [9.0, 10.0, 11.0];
        let v = [1.0, 1.0, 1.0];
        let (close, fresh) = daily_prices(&t.map(|x| x as f64), &c, &v, H, T0, 4);
        assert!(close[0].is_nan() && !fresh[0]);
        assert_eq!((close[1], fresh[1]), (10.0, true));
        assert_eq!((close[2], fresh[2]), (11.0, false)); // traded inside day 2, not in the bar ending at it
        assert_eq!(close[3], 11.0);                      // carried forward
        // a zero-volume bar never marks
        let (close, _) = daily_prices(&[(T0 + 23 * H) as f64], &[5.0], &[0.0], H, T0, 3);
        assert!(close[1].is_nan());
        // daily bars: the bar opening at day 0 closes at day 1
        let (close, fresh) = daily_prices(&[T0 as f64], &[7.0], &[1.0], 24 * H, T0, 3);
        assert_eq!((close[1], fresh[1]), (7.0, true));
        // funding: settlement exactly at day 1 (+2 ms recording jitter) is day 1; 01:00 on day 1 is day 2;
        // a settlement at start belongs to day 0 and is dropped
        let (f, n) = daily_funding(&[(T0 + DAY + 2) as f64, (T0 + DAY + H + 48) as f64, T0 as f64], &[0.001, 0.002, 0.5], T0, 4);
        assert_eq!((f[1], n[1]), (0.001, 1));
        assert_eq!((f[2], n[2]), (0.002, 1));
        assert_eq!(f.iter().sum::<f64>(), 0.003);
    }

    #[test]
    fn windows_need_full_history() {
        let mut f = vec![0.0; 10];
        let mut n = vec![0u32; 10];
        for d in 4..10 {
            f[d] = 0.001;
            n[d] = 3;
        }
        let s = assemble(vec![1.0; 10], vec![true; 10], &f, &n);
        assert_eq!(s.first_fund, 4);
        assert!(s.window(5, 3).is_none());                   // window days 3..5 starts before the history
        assert!((s.window(6, 3).unwrap() - 0.003).abs() < 1e-15);
        assert!((s.fund_on(6) - 0.001).abs() < 1e-15);
    }

    fn uni(series: Vec<Vec<Option<Daily>>>) -> Universe {
        let nd = series[0].iter().flatten().next().unwrap().close.len();
        Universe { keys: (0..series.len()).map(|i| format!("C{i}")).collect(), series, nd, t0: T0 }
    }

    #[test]
    fn book_collects_the_funding_difference() {
        // one coin, same price on both venues; venue 1 pays 0.001/day more to shorts
        let nd = 12;
        let u = uni(vec![vec![Some(flat(nd, 100.0, 0.0)), Some(flat(nd, 100.0, 0.001))]]);
        let yes = |_: usize, _: usize, _: usize, _: usize| true;
        let cand = candidates(&u, &[0, 1], 2, &yes);
        assert!(cand[1].iter().all(|c| c.is_none()));       // a 2-day window needs days 1..2 of history
        let c = cand[2][0].unwrap();
        assert_eq!((c.lo, c.hi), (0, 1));
        assert!((c.spread - 0.001 * 365.0).abs() < 1e-9);
        let names = vec!["a".to_string(), "b".to_string()];
        let b = simulate(&u, &cand, 2, 2, 0.1, 1, &names);
        assert_eq!(b.legs[2], 2.0);                          // entry at day 2's close
        assert!((b.gross[2] - 0.001).abs() < 1e-12);         // earns day 3's funding
        assert_eq!(b.legs[nd - 2], 2.0);                     // still open at the end: pays its exit
        assert_eq!(b.trades.len(), 1);
        let x = net(&b, 1, 0.0005);
        assert_eq!(x.len(), nd - 1 - 2);
        assert!((x[0] - (0.001 - 0.001) / 2.0).abs() < 1e-12); // first interval: funding minus two legs' cost
        assert!((x[1] - 0.0005).abs() < 1e-12);
    }

    #[test]
    fn book_exits_below_half_the_threshold_and_on_delisting() {
        let nd = 14;
        let mut hi = flat(nd, 100.0, 0.001);
        // funding stops paying from day 6: the 2-day spread falls to 0 by day 7
        let f: Vec<f64> = (0..nd).map(|d| if (1..6).contains(&d) { 0.001 } else if d >= 6 { 0.0 } else { 0.0 }).collect();
        let n: Vec<u32> = (0..nd).map(|d| if d >= 1 { 1 } else { 0 }).collect();
        hi = assemble(hi.close.clone(), hi.fresh.clone(), &f, &n);
        // a second coin whose short venue stops trading after day 4 (delisted)
        let mut gone = flat(nd, 50.0, 0.002);
        for d in 5..nd {
            gone.fresh[d] = false;
        }
        gone.last_fresh = 4;
        let u = uni(vec![vec![Some(flat(nd, 100.0, 0.0)), Some(hi)], vec![Some(flat(nd, 50.0, 0.0)), Some(gone)]]);
        let yes = |_: usize, _: usize, _: usize, _: usize| true;
        let cand = candidates(&u, &[0, 1], 2, &yes);
        let names = vec!["a".to_string(), "b".to_string()];
        let b = simulate(&u, &cand, 2, 2, 0.2, 2, &names);
        let t0 = b.trades.iter().find(|t| t.coin == "C0").unwrap();
        let t1 = b.trades.iter().find(|t| t.coin == "C1").unwrap();
        assert_eq!(t0.exit_day, Some(7));                    // day 6's window still pays 18%/yr (>= 10%); day 7's pays 0
        assert!(!t0.forced);
        assert_eq!(t1.exit_day, Some(5));                    // never fresh again after day 4
        assert!(t1.forced);
    }

    #[test]
    fn identity_guard_and_rc() {
        // two unrelated random walks fail the guard; the same walk passes
        let nd = 60;
        let mut rng = ChaCha8Rng::seed_from_u64(1);
        let mut walk = |s: f64| -> Vec<f64> {
            let mut p = vec![s];
            for _ in 1..nd {
                let r: f64 = rng.gen_range(-0.05..0.05);
                p.push(p.last().unwrap() * (1.0 + r));
            }
            p
        };
        let (pa, pb) = (walk(10.0), walk(10.0));
        let mk = |p: Vec<f64>| assemble(p, vec![true; nd], &vec![0.0; nd], &vec![1; nd]);
        let (a, b, a2) = (mk(pa.clone()), mk(pb), mk(pa.iter().map(|x| x * 1000.0).collect()));
        assert!(pair_corr(&a, &b, 40, 30, 20).unwrap() < 0.9);
        assert!(pair_corr(&a, &a2, 40, 30, 20).unwrap() > 0.999);
        assert!(pair_corr(&a, &a2, 10, 30, 20).is_none());   // too few days yet
        // RC: a strong drift beats the family null; noise does not
        let noise: Vec<f64> = (0..500).map(|i| ((i * 7919) % 101) as f64 / 101.0 - 0.5).collect();
        let strong: Vec<f64> = noise.iter().map(|v| v * 0.01 + 0.002).collect();
        let tmax = block_rc(&[noise.clone(), strong.clone()], &[0, 0], 500, 10, 300, 7);
        let mut s = tmax.clone();
        s.sort_by(|a, b| a.partial_cmp(b).unwrap());
        assert!(stats::tstat(&strong) > percentile(&s, 95.0));
        assert!(stats::tstat(&noise).abs() < percentile(&s, 95.0));
    }

    #[test]
    fn labels_and_dates() {
        let s = Strat { set: "binance+gate".into(), lookback: 7, threshold: 0.2, slots: 10 };
        assert_eq!(s.label(), "binance+gate L7d th20% K10");
        assert_eq!(day_str(T0, 0), "2021-01-01");
        assert_eq!(day_str(T0, 59), "2021-03-01");
        let x = [0.01, -0.02, 0.03, 0.0, 0.01];
        let st = day_stats(&x, 0, 3, 0.0, 2);
        assert!((st.mean_bp - 60.0).abs() < 1e-9);
        assert!((st.recent_bp - 50.0).abs() < 1e-9);
        assert_eq!(st.days, 5);
    }
}
