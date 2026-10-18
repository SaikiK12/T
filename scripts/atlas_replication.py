"""atlas_v1 (R185): score the frozen discovery lists on validation (same sign and |t| >= 2), as the PREREG says.

usage: python scripts/atlas_replication.py main+clock|flow
Reads results/discovery_lists_{tag}.csv and results/validation_{tag}_real.parquet, writes results/replication_{tag}.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

R = Path(__file__).resolve().parent.parent / "experiments" / "atlas_v1" / "results"
tag = sys.argv[1]
pd.set_option("display.width", 250)
lists = pd.read_csv(R / f"discovery_lists_{tag}.csv")
val = pd.read_parquet(R / f"validation_{tag}_real.parquet")
key = ["tensor", "view", "bin", "h", "measure", "group"]
lists["grouping"] = lists.source.str.split("_").str[-2]
lists["kind"] = np.where(lists.source.str.endswith("_real"), "real", "placebo")
v = val.rename(columns={"mean_bp": "v_bp", "t": "v_t", "edge_cost": "v_edge_cost", "eras_same_sign": "v_eras"})
m = lists.merge(v[key + ["grouping", "v_bp", "v_t", "v_edge_cost", "v_eras"]], on=key + ["grouping"], how="left")
m["same"] = np.sign(m.v_bp) == np.sign(m.mean_bp)
m["rep"] = m.same & (m.v_t.abs() >= 2)
m["level"] = np.where(m.group == "all", "CGE(all)", "conditional")
m = m.drop_duplicates(key + ["kind", "level", "source"])
print("replication on 2024-01..2025-06 (same sign and |t|>=2), with share keeping the sign:")
print(m.groupby(["level", "kind"]).agg(n=("rep", "size"), replicated=("rep", "mean"), same_sign=("same", "mean"),
      bp_disc=("mean_bp", lambda x: np.median(np.abs(x))), bp_val=("v_bp", lambda x: np.median(np.abs(x)))).round(3).to_string())
c = m[(m.level == "CGE(all)") & (m.kind == "real")].drop_duplicates(["tensor", "view", "bin", "h", "measure"]).copy()
c["family"] = c.name.str.extract(r"^([a-z_:]+)")[0]
print("\nCGE replication by measure x horizon:")
print(c.pivot_table(index="measure", columns="h", values="rep", aggfunc="mean").round(2).to_string())
print("\nCGE replication by family:")
f = c.groupby("family").agg(n=("rep", "size"), rep=("rep", "mean"), same=("same", "mean"),
                            disc_bp=("mean_bp", lambda x: np.median(np.abs(x))), val_bp=("v_bp", lambda x: np.median(np.abs(x))))
print(f.sort_values("rep", ascending=False).round(2).to_string())
m.to_csv(R / f"replication_{tag}.csv", index=False)
