//! qx: the lab's fast engine. Families of strategies run from a spec file, decided together.
//!
//! usage: qx events <spec.toml>      run an event family (see engine/README.md)

mod data;
mod events;
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
    }
    Ok(())
}
