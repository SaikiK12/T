//! Cluster statistics as scripts/run_delist.py `stats` computes them.

use serde::Serialize;

/// One observation per cluster, in time order.
#[derive(Clone, Debug)]
pub struct Obs {
    pub t0: i64,
    pub obs: f64,
    pub legs: usize,
}

#[derive(Clone, Debug, Default, Serialize)]
pub struct Stats {
    pub n: usize,
    pub legs: usize,
    pub mean_pct: f64,
    pub median_pct: f64,
    pub hit: f64,
    pub t: f64,
    pub half1_pct: f64,
    pub half2_pct: f64,
    pub y2025_pct: f64,
    pub y2025_n: usize,
}

pub fn mean(x: &[f64]) -> f64 {
    if x.is_empty() {
        return f64::NAN;
    }
    x.iter().sum::<f64>() / x.len() as f64
}

pub fn sd1(x: &[f64]) -> f64 {
    let n = x.len();
    if n < 2 {
        return f64::NAN;
    }
    let m = mean(x);
    (x.iter().map(|v| (v - m) * (v - m)).sum::<f64>() / (n - 1) as f64).sqrt()
}

pub fn median(x: &[f64]) -> f64 {
    if x.is_empty() {
        return f64::NAN;
    }
    let mut v = x.to_vec();
    v.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let n = v.len();
    if n % 2 == 1 { v[n / 2] } else { 0.5 * (v[n / 2 - 1] + v[n / 2]) }
}

pub fn tstat(x: &[f64]) -> f64 {
    let s = sd1(x);
    if !(s > 0.0) {
        return f64::NAN;
    }
    mean(x) / (s / (x.len() as f64).sqrt())
}

pub fn stats(o: &[Obs], y2025_ms: i64) -> Stats {
    let x: Vec<f64> = o.iter().map(|v| v.obs).collect();
    let n = x.len();
    if n < 2 {
        return Stats { n, legs: o.iter().map(|v| v.legs).sum(), ..Default::default() };
    }
    let half = n / 2;
    let y: Vec<f64> = o.iter().filter(|v| v.t0 >= y2025_ms).map(|v| v.obs).collect();
    Stats {
        n,
        legs: o.iter().map(|v| v.legs).sum(),
        mean_pct: mean(&x) * 100.0,
        median_pct: median(&x) * 100.0,
        hit: x.iter().filter(|v| **v > 0.0).count() as f64 / n as f64,
        t: tstat(&x),
        half1_pct: mean(&x[..half]) * 100.0,
        half2_pct: mean(&x[half..]) * 100.0,
        y2025_pct: if y.is_empty() { f64::NAN } else { mean(&y) * 100.0 },
        y2025_n: y.len(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn basic() {
        let o: Vec<Obs> = [0.01, -0.02, 0.03, 0.04].iter().enumerate()
            .map(|(i, v)| Obs { t0: i as i64, obs: *v, legs: 1 }).collect();
        let s = stats(&o, 2);
        assert!((s.mean_pct - 1.5).abs() < 1e-12);
        assert!((s.median_pct - 2.0).abs() < 1e-12);
        assert!((s.half1_pct - -0.5).abs() < 1e-12);
        assert!((s.y2025_pct - 3.5).abs() < 1e-12);
        assert_eq!(s.y2025_n, 2);
        let sd = sd1(&[0.01, -0.02, 0.03, 0.04]);
        assert!((s.t - 0.015 / (sd / 2.0)).abs() < 1e-12);
    }
}
