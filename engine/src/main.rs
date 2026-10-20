//! qx: the lab's fast engine. Families of strategies run from a spec file, decided together.
//!
//! usage: qx events <spec.toml>      run an event family (see engine/README.md)
//!        qx spread <spec.toml>      run a cross-venue funding carry family
//!        qx factors <spec.toml>     factor report (IC, rank IC, quantiles, turnover) over a factor family

mod data;
mod events;
mod factors;
mod spread;
mod stats;

use anyhow::Result;
use clap::{Parser, Subcommand};
use std::time::Instant;

#[derive(Parser)]
#[command(name = "qx", about = "The lab's fast engine")]
struct Cli {
    #[command(subcommand)]
    cmd: Cmd,
}

#[derive(Subcommand)]
enum Cmd {
    /// Run an event family from a TOML spec; writes report.json, strategies.csv and legs_priced.csv to its `out`.
    Events { spec: String },
    /// Run a cross-venue funding carry family; writes report.json, strategies.csv, daily.csv and trades.csv to its `out`.
    Spread { spec: String },
    /// Factor report over a factor family; writes report.json and ic.csv to its `out`.
    Factors { spec: String },
}

fn main() -> Result<()> {
    let start = Instant::now();
    let log = move |m: String| eprintln!("[{:7.1}s] {m}", start.elapsed().as_secs_f64());
    match Cli::parse().cmd {
        Cmd::Events { spec } => {
            let s: events::Spec = toml::from_str(&std::fs::read_to_string(&spec)?)?;
            let rep = events::run(s, &log)?;
            log(format!("reality check: family max-t 95th pct {:.2} over {} strategies", rep.rc_null_p95, rep.trials));
            for r in rep.strategies.iter().take(12) {
                let s = &r.stats[0];
                let m = |k: usize| r.stats.get(k).map(|x| x.mean_pct).unwrap_or(f64::NAN);
                log(format!("{:28} n {:4} mean {:+6.2}% med {:+6.2}% t {:5.2} p_rc {:.4} halves {:+.2}/{:+.2} 2025+ {:+.2}% ({}) 2x {:+.2}% 3x {:+.2}%{}",
                    r.label, s.n, s.mean_pct, s.median_pct, s.t, r.p_rc, s.half1_pct, s.half2_pct, s.y2025_pct, s.y2025_n,
                    m(1), m(2), r.null.as_ref().map(|n| format!(" null p {:.4}", n.p)).unwrap_or_default()));
            }
            log(format!("VERDICT {}; survivors {:?}", rep.verdict, rep.survivors));
        }
        Cmd::Spread { spec } => {
            let s: spread::Spec = toml::from_str(&std::fs::read_to_string(&spec)?)?;
            let rep = spread::run(s, &log)?;
            log(format!("reality check: family max-t 95th pct {:.2} over {} strategies", rep.rc_null_p95, rep.trials));
            for r in rep.strategies.iter().take(12) {
                let (a, b) = (&r.stats[0], r.stats.get(1));
                log(format!("{:34} from {} {:+7.2}%/yr t {:5.2} nw {:5.2} p_rc {:.4} halves {:+.1}/{:+.1} bp 2x {:+7.2}%/yr fund {:.2} held {:.1}",
                    r.label, r.window_from, a.ann_pct, a.t, a.t_nw, r.p_rc, a.half1_bp, a.half2_bp,
                    b.map(|x| x.ann_pct).unwrap_or(f64::NAN), r.funding_share, r.avg_held));
            }
            log(format!("VERDICT {}; survivors {:?}", rep.verdict, rep.survivors));
        }
        Cmd::Factors { spec } => {
            let s: factors::Spec = toml::from_str(&std::fs::read_to_string(&spec)?)?;
            let rep = factors::run(s, &log)?;
            log(format!("{} factor x horizon series on {} dates; max |t| null 95th pct {:.2} (blocks of {})",
                rep.trials, rep.dates, rep.rc_null_p95, rep.block));
            for r in rep.results.iter().take(15) {
                log(format!("{:28} {:4}h rankIC {:+.4} t {:+6.2} IR {:+.3} LS {:+7.1} bp t {:+5.2} turn {:.2}/{:.2} net {} p_rc {:.4}",
                    r.factor, r.horizon_h, r.rank_ic, r.rank_ic_t, r.rank_ic_ir, r.ls_bp, r.ls_t, r.turnover_top,
                    r.turnover_bottom, r.ls_net_ann_pct.map(|x| format!("{x:+.1}%/yr")).unwrap_or("-".into()), r.p_rc));
            }
            log(format!("survivors (p_rc < alpha): {:?}", rep.survivors));
        }
    }
    Ok(())
}
