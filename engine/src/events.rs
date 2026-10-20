//! Event families: every (type, direction, horizon, line) strategy over a table of event legs, decided together.
//!
//! The rules are the lab's event-lane rules (R267/R269, scripts/run_delist.py), unchanged:
//! - r0 is the hourly bar that contains the event; entry is its close; the exit is the close of r0 + h
//!   (the last traded close if that bar did not trade).
//! - Funding settled in (entry, exit]; the short receives +rate.
//! - One observation per cluster (same type, same hour): the equal-weight mean net of its legs, one per instrument.
//! - Each leg trades on the first venue (in spec order) whose symbol traded in the event's hour.
//! Family decision: a max-t cluster bootstrap over every strategy (types resampled independently), then halves,
//! 2025+, a matched same-hour null and the 2x mean, on each strategy that clears it.

use crate::data::{self, Axis, Source, VenueSpec};
use crate::stats::{self, Obs, Stats};
use anyhow::{Context, Result, anyhow};
use rand::{Rng, SeedableRng};
use rand_chacha::ChaCha8Rng;
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::fs;
use std::path::Path;

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct Venue {
    pub name: String,
    pub col: String,
    pub klines: String,
    #[serde(default = "d_vol")]
    pub vol: String,
    #[serde(default)]
    pub funding: Option<String>,
}

fn d_vol() -> String { "volume".into() }
fn d_kind() -> String { "kind".into() }
fn d_min() -> usize { 10 }
fn d_start() -> String { "2021-01-01".into() }
fn d_end() -> String { "2026-09-30".into() }
fn d_alpha() -> f64 { 0.05 }
fn d_g3() -> usize { 3 }
fn d_hcost() -> f64 { 0.001 }
fn d_lines() -> Vec<String> { vec!["net".into()] }
fn d_null() -> String { "rc_pass".into() }
fn d_y25() -> String { "2025-01-01".into() }
fn d_stops() -> Vec<f64> { vec![0.0] }

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct Spec {
    pub name: String,
    pub events: String,
    #[serde(default)]
    pub filter: BTreeMap<String, String>,
    #[serde(default = "d_kind")]
    pub kind_col: String,
    #[serde(default)]
    pub kinds: Option<Vec<String>>,
    pub venues: Vec<Venue>,
    pub horizons: Vec<i64>,
    pub directions: Vec<String>,
    #[serde(default = "d_lines")]
    pub lines: Vec<String>,
    pub costs: Vec<f64>,
    #[serde(default = "d_min")]
    pub min_clusters: usize,
    pub reps: usize,
    pub seed: u64,
    #[serde(default = "d_null")]
    pub null_for: String,
    pub out: String,
    #[serde(default = "d_start")]
    pub start: String,
    #[serde(default = "d_end")]
    pub end: String,
    #[serde(default)]
    pub hedge: Option<String>,
    #[serde(default = "d_hcost")]
    pub hedge_cost: f64,
    #[serde(default = "d_alpha")]
    pub alpha: f64,
    #[serde(default = "d_g3")]
    pub g3_min: usize,
    #[serde(default = "d_y25")]
    pub recent_from: String,
    /// Winsorize each strategy's cluster observations at (q, 1 - q) for the reality check only (0 = off).
    #[serde(default)]
    pub winsor: f64,
    /// Drop a leg if any one-bar move of its instrument in [r0 - 24, r0 + max h] exceeds this factor (0 = off):
    /// redenominations and token swaps (COCOS 1:1000 in 2021) are not returns.
    #[serde(default)]
    pub max_bar_jump: f64,
    /// Protective covers to try, as fractions of the entry price (0 = hold to the horizon). Each is its own strategy:
    /// exit at the first hourly close that has moved this much against the position (`Series::leg_stop`).
    #[serde(default = "d_stops")]
    pub stops: Vec<f64>,
}

#[derive(Clone, Debug)]
struct Ev {
    notice: String,
    kind: String,
    ticker: String,
    t: i64,
    syms: Vec<String>, // per venue, "" if none
}

/// A priced leg.
#[derive(Clone, Debug, Serialize)]
pub struct PLeg {
    pub notice: String,
    pub kind: String,
    pub ticker: String,
    pub t0: i64,
    pub r0: i64,
    pub venue: String,
    pub sym: String,
    pub sg: Vec<f64>,        // per horizon: short gross + funding, NaN if not priceable
    pub hedge: Vec<f64>,     // per horizon: hedge symbol's long return minus its funding, NaN if none
    pub stale: Vec<bool>,
    pub delisted: Vec<bool>,
    pub premove: f64,        // close(r0 - 1) -> close(r0), NaN if r0 - 1 did not trade
    pub xs: Vec<f64>,        // per (direction, horizon, nonzero stop): gross + funding in the short's sign
    pub xhit: Vec<bool>,     // the cover fired
}

#[derive(Clone, Debug, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize)]
pub struct Strat {
    pub kind: String,
    pub dir: String,
    pub h: i64,
    pub line: String,
    pub stop_bp: i64, // protective cover in basis points of the entry price, 0 = none
}

impl Strat {
    pub fn label(&self) -> String {
        format!("{} {} {}h{}{}", self.kind, self.dir, self.h,
            if self.line == "net" { String::new() } else { format!(" {}", self.line) },
            if self.stop_bp == 0 { String::new() } else { format!(" stop{}%", self.stop_bp as f64 / 100.0) })
    }
}

fn bp(x: f64) -> i64 {
    (x * 10_000.0).round() as i64
}

fn read_events(spec: &Spec) -> Result<Vec<Ev>> {
    let mut rd = csv::Reader::from_path(&spec.events).with_context(|| spec.events.clone())?;
    let hdr = rd.headers()?.clone();
    let col = |n: &str| hdr.iter().position(|h| h == n);
    let (ni, ti, ri) = (col("notice"), col("ticker"), col("release_ms"));
    let ki = col(&spec.kind_col);
    let ri = ri.ok_or_else(|| anyhow!("events need release_ms"))?;
    let vi: Vec<Option<usize>> = spec.venues.iter().map(|v| col(&v.col)).collect();
    let fi: Vec<(usize, String)> = spec.filter.iter()
        .map(|(k, v)| col(k).map(|i| (i, v.clone())).ok_or_else(|| anyhow!("filter column {k} missing")))
        .collect::<Result<_>>()?;
    let mut out = Vec::new();
    for r in rd.records() {
        let r = r?;
        if !fi.iter().all(|(i, v)| r.get(*i) == Some(v.as_str())) {
            continue;
        }
        let kind = ki.and_then(|i| r.get(i)).unwrap_or("all").to_string();
        if let Some(ks) = &spec.kinds {
            if !ks.contains(&kind) {
                continue;
            }
        }
        out.push(Ev {
            notice: ni.and_then(|i| r.get(i)).unwrap_or("").to_string(),
            kind,
            ticker: ti.and_then(|i| r.get(i)).unwrap_or("").to_string(),
            t: r.get(ri).unwrap().parse::<f64>()? as i64,
            syms: vi.iter().map(|i| i.and_then(|i| r.get(i)).unwrap_or("").to_string()).collect(),
        });
    }
    Ok(out)
}

pub struct Family {
    pub spec: Spec,
    pub suspect: Vec<String>,
    pub sources: Vec<Source>,
    pub legs: Vec<PLeg>,
    pub no_market: usize,
    pub events_in: usize,
}

pub fn build(spec: Spec, log: &dyn Fn(String)) -> Result<Family> {
    let axis = Axis::new(&spec.start, &spec.end)?;
    if spec.stops.is_empty() || spec.stops.iter().any(|&x| !(0.0..10.0).contains(&x)) {
        return Err(anyhow!("stops must be fractions in [0, 10), with 0 for no cover"));
    }
    if spec.stops.iter().any(|&x| x > 0.0) && spec.lines.iter().any(|l| l == "hedged") {
        return Err(anyhow!("a cover with the hedged line is not implemented (the hedge would need the same exit)"));
    }
    if data::ms(&spec.start)? < data::ms("2021-01-01")? {
        return Err(anyhow!("rows before 2021-01-01 are the reserved 2020 sample (docs/GATES.md); not read here"));
    }
    let evs = read_events(&spec)?;
    let root = data::data_root();
    let mut sources = Vec::new();
    for (k, v) in spec.venues.iter().enumerate() {
        let mut syms: BTreeSet<String> = evs.iter().map(|e| e.syms[k].clone()).filter(|s| !s.is_empty()).collect();
        if k == 0 {
            if let Some(h) = &spec.hedge {
                syms.insert(h.clone());
            }
        }
        let syms: Vec<String> = syms.into_iter().collect();
        let vs = VenueSpec { name: &v.name, klines: &v.klines, vol: &v.vol, funding: v.funding.as_deref() };
        let s = data::load(&root, &vs, &syms, axis)?;
        log(format!("venue {}: {} of {} symbols loaded", v.name, s.series.len(), syms.len()));
        sources.push(s);
    }
    let mut evs = evs;
    evs.sort_by(|a, b| (a.t, &a.notice, &a.ticker).cmp(&(b.t, &b.notice, &b.ticker)));
    let mut seen = BTreeSet::new();
    let (mut legs, mut no_market, mut suspect) = (Vec::new(), 0usize, Vec::new());
    let hmax = *spec.horizons.iter().max().unwrap_or(&1);
    let hedge = spec.hedge.as_ref().and_then(|h| sources[0].get(h));
    for e in &evs {
        let r0 = axis.row(e.t);
        let pick = (0..sources.len()).find(|&k| {
            !e.syms[k].is_empty() && r0 > 0 && sources[k].get(&e.syms[k]).map_or(false, |s| s.traded_at(r0))
        });
        let Some(k) = pick else {
            no_market += 1;
            continue;
        };
        if !seen.insert((e.kind.clone(), r0, k, e.syms[k].clone())) {
            continue; // one leg per instrument per cluster
        }
        let s = sources[k].get(&e.syms[k]).unwrap();
        if spec.max_bar_jump > 0.0 {
            let (lo, hi) = ((r0 - 24).max(0) as usize, ((r0 + hmax) as usize).min(s.close.len() - 1));
            let mut prev = f64::NAN;
            let mut bad = false;
            for r in lo..=hi {
                if s.traded[r] {
                    if prev.is_finite() && (s.close[r] / prev > spec.max_bar_jump || prev / s.close[r] > spec.max_bar_jump) {
                        bad = true;
                    }
                    prev = s.close[r];
                }
            }
            if bad {
                suspect.push(format!("{} {} {} {}", e.kind, e.ticker, spec.venues[k].name, e.t));
                continue;
            }
        }
        let mut leg = PLeg {
            notice: e.notice.clone(), kind: e.kind.clone(), ticker: e.ticker.clone(), t0: e.t, r0,
            venue: spec.venues[k].name.clone(), sym: e.syms[k].clone(), sg: vec![], hedge: vec![], stale: vec![],
            delisted: vec![], xs: vec![], xhit: vec![],
            premove: if s.traded_at(r0 - 1) { s.close[r0 as usize] / s.close[(r0 - 1) as usize] - 1.0 } else { f64::NAN },
        };
        for &h in &spec.horizons {
            match s.leg(r0, h) {
                Some(l) => {
                    leg.sg.push(l.gross + l.funding);
                    leg.stale.push(l.stale_exit);
                    leg.delisted.push(l.delisted_in_hold);
                    // the hedge's long over the same rows (the leg is valid, so r0 + h + 1 < n)
                    leg.hedge.push(hedge.map(|b| { let (ret, f) = b.long(r0, h); ret - f }).unwrap_or(f64::NAN));
                }
                None => {
                    leg.sg.push(f64::NAN);
                    leg.hedge.push(f64::NAN);
                    leg.stale.push(false);
                    leg.delisted.push(false);
                }
            }
        }
        for short in [true, false] {
            for &h in &spec.horizons {
                for &st in spec.stops.iter().filter(|&&x| x > 0.0) {
                    let (v, hit) = s.leg_stop(r0, h, short, st).map_or((f64::NAN, false), |(l, hit)| (l.gross + l.funding, hit));
                    leg.xs.push(v);
                    leg.xhit.push(hit);
                }
            }
        }
        legs.push(leg);
    }
    Ok(Family { events_in: evs.len(), spec, suspect, sources, legs, no_market })
}

impl Family {
    fn hidx(&self, h: i64) -> usize {
        self.spec.horizons.iter().position(|&x| x == h).unwrap()
    }

    /// Index into `PLeg::xs` for a strategy with a cover.
    fn xidx(&self, s: &Strat) -> usize {
        let nz: Vec<i64> = self.spec.stops.iter().filter(|&&x| x > 0.0).map(|&x| bp(x)).collect();
        let k = nz.iter().position(|&b| b == s.stop_bp).unwrap();
        let d = if s.dir == "short" { 0 } else { 1 };
        (d * self.spec.horizons.len() + self.hidx(s.h)) * nz.len() + k
    }

    /// Gross + funding of one leg in the short's sign, with the strategy's cover.
    fn leg_sg(&self, l: &PLeg, s: &Strat) -> f64 {
        if s.stop_bp == 0 { l.sg[self.hidx(s.h)] } else { l.xs[self.xidx(s)] }
    }

    /// Net of one leg for a strategy at cost multiple m (1-based), NaN if not priceable.
    pub fn leg_net(&self, l: &PLeg, s: &Strat, m: usize) -> f64 {
        let i = self.hidx(s.h);
        let c = self.spec.costs[m - 1];
        let sign = if s.dir == "short" { 1.0 } else { -1.0 };
        let mut v = sign * self.leg_sg(l, s) - c;
        if s.line == "hedged" {
            v += sign * l.hedge[i] - self.spec.hedge_cost * m as f64;
        }
        v
    }

    /// One observation per cluster, in time order, from legs with a finite net.
    pub fn obs_with(&self, s: &Strat, net: &dyn Fn(&PLeg) -> f64, keep: &dyn Fn(&PLeg) -> bool) -> Vec<(i64, Obs)> {
        let mut g: BTreeMap<i64, (i64, f64, usize)> = BTreeMap::new();
        for l in self.legs.iter().filter(|l| l.kind == s.kind && keep(l)) {
            let v = net(l);
            if !v.is_finite() {
                continue;
            }
            let e = g.entry(l.r0).or_insert((i64::MAX, 0.0, 0));
            e.0 = e.0.min(l.t0);
            e.1 += v;
            e.2 += 1;
        }
        let mut o: Vec<(i64, Obs)> = g.into_iter().map(|(r0, (t0, s, n))| (r0, Obs { t0, obs: s / n as f64, legs: n })).collect();
        o.sort_by_key(|x| x.1.t0);
        o
    }

    pub fn obs(&self, s: &Strat, m: usize) -> Vec<(i64, Obs)> {
        self.obs_with(s, &|l| self.leg_net(l, s, m), &|_| true)
    }

    pub fn clusters_by_kind(&self) -> BTreeMap<String, usize> {
        let mut c: BTreeMap<String, BTreeSet<i64>> = BTreeMap::new();
        for l in &self.legs {
            c.entry(l.kind.clone()).or_default().insert(l.r0);
        }
        c.into_iter().map(|(k, v)| (k, v.len())).collect()
    }

    pub fn strategies(&self) -> Vec<Strat> {
        let ncl = self.clusters_by_kind();
        let mut out = Vec::new();
        for (k, n) in &ncl {
            if *n < self.spec.min_clusters {
                continue;
            }
            for d in &self.spec.directions {
                for &h in &self.spec.horizons {
                    for &st in &self.spec.stops {
                        for line in &self.spec.lines {
                            out.push(Strat { kind: k.clone(), dir: d.clone(), h, line: line.clone(), stop_bp: bp(st) });
                        }
                    }
                }
            }
        }
        out
    }

    /// Max-t cluster bootstrap. Returns observed t per strategy and the family max-t of each replication.
    pub fn reality_check(&self, strats: &[Strat]) -> (Vec<f64>, Vec<f64>) {
        let kinds: BTreeSet<&String> = strats.iter().map(|s| &s.kind).collect();
        let mut tobs = vec![f64::NAN; strats.len()];
        let mut tmax = vec![f64::NEG_INFINITY; self.spec.reps];
        for kind in kinds {
            let cols: Vec<usize> = (0..strats.len()).filter(|&j| &strats[j].kind == kind).collect();
            let per: Vec<BTreeMap<i64, f64>> = cols.iter().map(|&j| self.obs(&strats[j], 1).into_iter().map(|(r, o)| (r, o.obs)).collect()).collect();
            let rows: Vec<i64> = per.iter().flat_map(|m| m.keys().copied()).collect::<BTreeSet<_>>().into_iter().collect();
            let n = rows.len();
            let mut x: Vec<Vec<f64>> = rows.iter().map(|r| per.iter().map(|m| *m.get(r).unwrap_or(&f64::NAN)).collect()).collect();
            if self.spec.winsor > 0.0 {
                for j in 0..cols.len() {
                    let mut v: Vec<f64> = x.iter().map(|r| r[j]).filter(|v| v.is_finite()).collect();
                    v.sort_by(|a, b| a.partial_cmp(b).unwrap());
                    let (lo, hi) = (percentile(&v, 100.0 * self.spec.winsor), percentile(&v, 100.0 * (1.0 - self.spec.winsor)));
                    for r in x.iter_mut() {
                        if r[j].is_finite() {
                            r[j] = r[j].clamp(lo, hi);
                        }
                    }
                }
            }
            let mu: Vec<f64> = (0..cols.len()).map(|j| {
                let v: Vec<f64> = x.iter().map(|r| r[j]).filter(|v| v.is_finite()).collect();
                stats::mean(&v)
            }).collect();
            for (k, &j) in cols.iter().enumerate() {
                let v: Vec<f64> = x.iter().map(|r| r[k]).filter(|v| v.is_finite()).collect();
                tobs[j] = stats::tstat(&v);
            }
            let seed = self.spec.seed ^ hash(kind);
            let tk: Vec<f64> = (0..self.spec.reps).into_par_iter().map(|b| {
                let mut rng = ChaCha8Rng::seed_from_u64(seed.wrapping_add(b as u64));
                let pick: Vec<usize> = (0..n).map(|_| rng.gen_range(0..n)).collect();
                let mut best = f64::NEG_INFINITY;
                for k in 0..cols.len() {
                    let v: Vec<f64> = pick.iter().map(|&i| x[i][k] - mu[k]).filter(|v| v.is_finite()).collect();
                    let t = stats::tstat(&v);
                    if t.is_finite() && t > best {
                        best = t;
                    }
                }
                best
            }).collect();
            for b in 0..self.spec.reps {
                tmax[b] = tmax[b].max(tk[b]);
            }
        }
        (tobs, tmax)
    }

    /// Same instruments, same hour of day, a random day 7-60 days before (180 if fewer than 10 admissible days).
    pub fn matched_null(&self, s: &Strat, seed: u64) -> NullResult {
        let obs = self.obs(s, 1);
        let stop = s.stop_bp as f64 / 10_000.0;
        let mut cand: Vec<Vec<f64>> = Vec::new();
        let mut kept_obs = Vec::new();
        let sign = if s.dir == "short" { 1.0 } else { -1.0 };
        let hedge = self.spec.hedge.as_ref().and_then(|h| self.sources[0].get(h));
        for (r0, o) in &obs {
            let legs: Vec<&PLeg> = self.legs.iter().filter(|l| l.kind == s.kind && l.r0 == *r0 && self.leg_sg(l, s).is_finite()).collect();
            let ser: Vec<_> = legs.iter().map(|l| self.source(&l.venue).get(&l.sym).unwrap()).collect();
            let mut vals = Vec::new();
            for kmax in [60i64, 180] {
                vals.clear();
                for k in 7..=kmax {
                    let r = r0 - 24 * k;
                    if r < 1 || !ser.iter().all(|x| x.traded_at(r)) {
                        continue;
                    }
                    let xs: Vec<_> = ser.iter().map(|x| x.leg_stop(r, s.h, s.dir == "short", stop)).collect();
                    if xs.iter().any(|x| x.is_none()) {
                        continue;
                    }
                    let sg = stats::mean(&xs.iter().map(|x| { let x = x.unwrap().0; x.gross + x.funding }).collect::<Vec<_>>());
                    let mut v = sign * sg - self.spec.costs[0];
                    if s.line == "hedged" {
                        let hv = hedge.map(|b| { let (ret, f) = b.long(r, s.h); ret - f }).unwrap_or(f64::NAN);
                        v += sign * hv - self.spec.hedge_cost;
                    }
                    if v.is_finite() {
                        vals.push(v);
                    }
                }
                if vals.len() >= 10 {
                    break;
                }
            }
            if vals.len() >= 10 {
                cand.push(vals.clone());
                kept_obs.push(o.obs);
            }
        }
        if cand.is_empty() {
            return NullResult { clusters: 0, of: obs.len(), ..Default::default() };
        }
        let o = stats::mean(&kept_obs);
        let null: Vec<f64> = (0..self.spec.reps).into_par_iter().map(|b| {
            let mut rng = ChaCha8Rng::seed_from_u64(seed.wrapping_add(b as u64));
            stats::mean(&cand.iter().map(|c| c[rng.gen_range(0..c.len())]).collect::<Vec<_>>())
        }).collect();
        let mut sorted = null.clone();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let p95 = percentile(&sorted, 95.0);
        NullResult {
            clusters: cand.len(), of: obs.len(), observed_pct: o * 100.0, null_mean_pct: stats::mean(&null) * 100.0,
            null_p95_pct: p95 * 100.0, p: (1 + null.iter().filter(|&&v| v >= o).count()) as f64 / (self.spec.reps + 1) as f64,
        }
    }

    fn source(&self, name: &str) -> &Source {
        self.sources.iter().find(|s| s.name == name).unwrap()
    }

    pub fn robustness(&self, s: &Strat) -> Robust {
        let i = self.hidx(s.h);
        let y25 = data::ms(&self.spec.recent_from).unwrap();
        let st = |o: Vec<(i64, Obs)>| stats::stats(&o.into_iter().map(|x| x.1).collect::<Vec<_>>(), y25);
        let net = |l: &PLeg| self.leg_net(l, s, 1);
        let mut nets: Vec<(f64, usize)> = self.legs.iter().enumerate().filter(|(_, l)| l.kind == s.kind)
            .map(|(k, l)| (net(l), k)).filter(|x| x.0.is_finite()).collect();
        nets.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap());
        let top: BTreeSet<usize> = nets.iter().take(3).map(|x| x.1).collect();
        let idx: HashMap<*const PLeg, usize> = self.legs.iter().enumerate().map(|(k, l)| (l as *const PLeg, k)).collect();
        let drop = self.obs_with(s, &net, &|l| !top.contains(&idx[&(l as *const PLeg)]));
        let mut per_year: BTreeMap<i32, (usize, f64)> = BTreeMap::new();
        for (_, o) in self.obs(s, 1) {
            let y = data::year(o.t0);
            let e = per_year.entry(y).or_insert((0, 0.0));
            e.0 += 1;
            e.1 += o.obs;
        }
        let sign = if s.dir == "short" { -1.0 } else { 1.0 };
        let mut by_venue = BTreeMap::new();
        for v in &self.spec.venues {
            let o = self.obs_with(s, &net, &|l| l.venue == v.name);
            if o.len() >= 2 {
                by_venue.insert(v.name.clone(), st(o));
            }
        }
        let gross = Strat { line: "net".into(), ..s.clone() };
        let hit = |l: &PLeg| s.stop_bp > 0 && l.xhit[self.xidx(s)];
        Robust {
            drop_top3_legs: st(drop),
            gross: st(self.obs_with(&gross, &|l| self.leg_net(l, &gross, 1) + self.spec.costs[0], &|_| true)),
            per_year: per_year.into_iter().map(|(y, (n, sum))| (y, YearStat { n, mean_pct: sum / n as f64 * 100.0 })).collect(),
            by_venue,
            premove_in_direction: st(self.obs_with(s, &|l| sign * l.premove, &|_| true)),
            stale_exits: self.legs.iter().filter(|l| l.kind == s.kind && l.sg[i].is_finite() && l.stale[i]).count(),
            delisted_in_hold: self.legs.iter().filter(|l| l.kind == s.kind && l.sg[i].is_finite() && l.delisted[i]).count(),
            covered: self.legs.iter().filter(|l| l.kind == s.kind && self.leg_sg(l, s).is_finite() && hit(l)).count(),
        }
    }
}

pub fn percentile(sorted: &[f64], q: f64) -> f64 {
    // numpy's default (linear interpolation)
    let n = sorted.len();
    if n == 0 {
        return f64::NAN;
    }
    let pos = q / 100.0 * (n - 1) as f64;
    let lo = pos.floor() as usize;
    let hi = pos.ceil() as usize;
    sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo as f64)
}

fn hash(s: &str) -> u64 {
    s.bytes().fold(1469598103934665603u64, |h, b| (h ^ b as u64).wrapping_mul(1099511628211))
}

#[derive(Clone, Debug, Default, Serialize)]
pub struct NullResult {
    pub clusters: usize,
    pub of: usize,
    pub observed_pct: f64,
    pub null_mean_pct: f64,
    pub null_p95_pct: f64,
    pub p: f64,
}

#[derive(Clone, Debug, Serialize)]
pub struct YearStat {
    pub n: usize,
    pub mean_pct: f64,
}

#[derive(Clone, Debug, Serialize)]
pub struct Robust {
    pub drop_top3_legs: Stats,
    pub gross: Stats,
    pub per_year: BTreeMap<i32, YearStat>,
    pub by_venue: BTreeMap<String, Stats>,
    pub premove_in_direction: Stats,
    pub stale_exits: usize,
    pub delisted_in_hold: usize,
    pub covered: usize, // legs whose cover fired
}

#[derive(Clone, Debug, Serialize)]
pub struct StratResult {
    pub label: String,
    pub strat: Strat,
    pub stats: Vec<Stats>, // per cost multiple
    pub p_rc: f64,
    pub gates: BTreeMap<String, bool>,
    pub null: Option<NullResult>,
    pub robustness: Option<Robust>,
    pub pass: bool,
}

#[derive(Clone, Debug, Serialize)]
pub struct Report {
    pub name: String,
    pub trials: usize,
    pub events_in: usize,
    pub priced_legs: usize,
    pub no_market: usize,
    pub clusters: BTreeMap<String, usize>,
    pub legs_by_venue: BTreeMap<String, usize>,
    pub rc_null_p95: f64,
    pub rc_t: Vec<(String, f64)>,
    pub suspect: Vec<String>,
    pub verdict: String,
    pub survivors: Vec<String>,
    pub strategies: Vec<StratResult>,
    pub spec: Spec,
}

pub fn run(spec: Spec, log: &dyn Fn(String)) -> Result<Report> {
    let fam = build(spec, log)?;
    let y25 = data::ms(&fam.spec.recent_from)?;
    let strats = fam.strategies();
    log(format!("{} events, {} priced legs, {} no market, {} suspect; clusters {:?}; {} strategies",
        fam.events_in, fam.legs.len(), fam.no_market, fam.suspect.len(), fam.clusters_by_kind(), strats.len()));
    let (tobs, tmax) = fam.reality_check(&strats);
    let mut sorted = tmax.clone();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let reps = fam.spec.reps;
    let mut results: Vec<StratResult> = strats.par_iter().enumerate().map(|(j, s)| {
        let st: Vec<Stats> = (1..=fam.spec.costs.len()).map(|m| {
            stats::stats(&fam.obs(s, m).into_iter().map(|x| x.1).collect::<Vec<_>>(), y25)
        }).collect();
        let p_rc = (1 + tmax.iter().filter(|&&v| v >= tobs[j]).count()) as f64 / (reps + 1) as f64;
        let s1 = &st[0];
        let mut gates = BTreeMap::new();
        gates.insert("RC".into(), p_rc < fam.spec.alpha);
        gates.insert("G2".into(), s1.half1_pct > 0.0 && s1.half2_pct > 0.0);
        gates.insert("G3".into(), s1.y2025_n >= fam.spec.g3_min && s1.y2025_pct > 0.0);
        if st.len() > 1 {
            gates.insert("G5".into(), st[1].mean_pct > 0.0);
        }
        StratResult { label: s.label(), strat: s.clone(), stats: st, p_rc, gates, null: None, robustness: None, pass: false }
    }).collect();
    let null_all = fam.spec.null_for == "all";
    let seed = fam.spec.seed;
    results.par_iter_mut().for_each(|r| {
        if null_all || r.gates["RC"] {
            let nr = fam.matched_null(&r.strat, seed ^ hash(&r.label));
            r.gates.insert("G4".into(), nr.p < fam.spec.alpha);
            r.null = Some(nr);
            r.robustness = Some(fam.robustness(&r.strat));
        }
        r.pass = r.gates.get("G4").is_some() && r.gates.values().all(|&g| g);
    });
    results.sort_by(|a, b| b.stats[0].t.partial_cmp(&a.stats[0].t).unwrap_or(std::cmp::Ordering::Equal));
    let survivors: Vec<String> = results.iter().filter(|r| r.pass).map(|r| r.label.clone()).collect();
    let mut lv = BTreeMap::new();
    for l in &fam.legs {
        *lv.entry(l.venue.clone()).or_insert(0) += 1;
    }
    let out = Path::new(&fam.spec.out);
    fs::create_dir_all(out)?;
    write_legs(&fam, &out.join("legs_priced.csv"))?;
    let rep = Report {
        name: fam.spec.name.clone(), trials: strats.len(), events_in: fam.events_in, priced_legs: fam.legs.len(),
        no_market: fam.no_market, clusters: fam.clusters_by_kind(), legs_by_venue: lv,
        rc_null_p95: percentile(&sorted, 95.0),
        rc_t: strats.iter().zip(tobs.iter()).map(|(s, t)| (s.label(), *t)).collect(),
        suspect: fam.suspect.clone(),
        verdict: if survivors.is_empty() { "NULL".into() } else { "PASS (gate 0)".into() },
        survivors, strategies: results, spec: fam.spec.clone(),
    };
    write_table(&rep, &out.join("strategies.csv"))?;
    fs::write(out.join("report.json"), serde_json::to_string_pretty(&rep)?.replace("NaN", "null"))?;
    Ok(rep)
}

fn write_legs(fam: &Family, path: &Path) -> Result<()> {
    let mut w = csv::Writer::from_path(path)?;
    let mut hdr = vec!["notice", "kind", "ticker", "t0", "r0", "venue", "sym", "premove"].into_iter().map(String::from).collect::<Vec<_>>();
    for h in &fam.spec.horizons {
        hdr.extend([format!("sg_{h}"), format!("hedge_{h}"), format!("stale_{h}"), format!("delisted_{h}")]);
    }
    for d in ["short", "long"] {
        for h in &fam.spec.horizons {
            for st in fam.spec.stops.iter().filter(|&&x| x > 0.0) {
                hdr.extend([format!("{d}_{h}_stop{}", bp(*st)), format!("{d}_{h}_stop{}_hit", bp(*st))]);
            }
        }
    }
    w.write_record(&hdr)?;
    for l in &fam.legs {
        let mut r = vec![l.notice.clone(), l.kind.clone(), l.ticker.clone(), l.t0.to_string(), l.r0.to_string(),
                         l.venue.clone(), l.sym.clone(), num(l.premove)];
        for i in 0..fam.spec.horizons.len() {
            r.extend([num(l.sg[i]), num(l.hedge[i]), l.stale[i].to_string(), l.delisted[i].to_string()]);
        }
        for (v, hit) in l.xs.iter().zip(&l.xhit) {
            r.extend([num(*v), hit.to_string()]);
        }
        w.write_record(&r)?;
    }
    w.flush()?;
    Ok(())
}

fn num(x: f64) -> String {
    if x.is_finite() { format!("{x:.10}") } else { String::new() }
}

fn write_table(rep: &Report, path: &Path) -> Result<()> {
    let mut w = csv::Writer::from_path(path)?;
    w.write_record(["label", "kind", "dir", "h", "line", "n", "legs", "mean_1x_pct", "median_pct", "hit", "t", "p_rc",
        "half1_pct", "half2_pct", "y2025_pct", "y2025_n", "mean_2x_pct", "mean_3x_pct", "null_p", "pass", "stop_pct"])?;
    for r in &rep.strategies {
        let s = &r.stats[0];
        let m = |k: usize| r.stats.get(k).map(|x| num(x.mean_pct)).unwrap_or_default();
        w.write_record([r.label.clone(), r.strat.kind.clone(), r.strat.dir.clone(), r.strat.h.to_string(),
            r.strat.line.clone(), s.n.to_string(), s.legs.to_string(), num(s.mean_pct), num(s.median_pct), num(s.hit),
            num(s.t), num(r.p_rc), num(s.half1_pct), num(s.half2_pct), num(s.y2025_pct), s.y2025_n.to_string(), m(1), m(2),
            r.null.as_ref().map(|n| num(n.p)).unwrap_or_default(), r.pass.to_string(),
            format!("{}", r.strat.stop_bp as f64 / 100.0)])?;
    }
    w.flush()?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn labels_and_stops() {
        let s = Strat { kind: "neg1".into(), dir: "short".into(), h: 72, line: "net".into(), stop_bp: 0 };
        assert_eq!(s.label(), "neg1 short 72h");
        let s = Strat { stop_bp: bp(0.2), ..s };
        assert_eq!(s.label(), "neg1 short 72h stop20%");
        let s = Strat { stop_bp: bp(0.075), ..s };
        assert_eq!(s.label(), "neg1 short 72h stop7.5%");
        let spec: Spec = toml::from_str("name='x'\nevents='e'\nvenues=[]\nhorizons=[1]\ndirections=['short']\ncosts=[0.004]\nreps=1\nseed=1\nout='o'").unwrap();
        assert_eq!(spec.stops, vec![0.0]); // old specs keep their strategies
    }
}
