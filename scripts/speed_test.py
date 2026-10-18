import sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lab import research, search

u, bins, names = research.load_universe()
t0, t1 = 0, research.row_of(u.p, research.DISC_END)
print(f"universe {u.p.S} columns, bins {bins.shape}, discovery rows {t1} ({t1//24} days)")
t = time.time()
cat = search.condition_catalog(bins, u.elig, t0, t1)
print(f"catalog: {len(cat[0])} conditions over {len(set(cat[0].tolist()))} views in {time.time()-t:.0f}s")
rules = search.singles(cat)
print(f"singles: {len(rules)} rules")
sample = [rules[i] for i in np.random.default_rng(0).choice(len(rules), 512, replace=False)]
edges = search.half_year_edges(u.p, t0, t1)
t = time.time(); sc = search.score_rules(u, bins, sample, t0, t1, edges); dt = time.time() - t
print(f"512 single rules: {dt:.1f}s = {dt/512*1000:.0f} ms/rule  -> full singles ~ {len(rules)*dt/512/60:.1f} min")
print("eras:", len(edges)-1, "| peak t quantiles of the sample (50/90/99/max):", np.round(np.quantile(sc.peak, [.5, .9, .99, 1]), 2))
pairs = search.pairs([(int(a), int(b), int(c)) for a, b, c in zip(cat[0][:60], cat[1][:60], cat[2][:60])])
sample2 = [pairs[i] for i in np.random.default_rng(1).choice(len(pairs), 256, replace=False)]
t = time.time(); sc2 = search.score_rules(u, bins, sample2, t0, t1, edges); dt = time.time() - t
print(f"256 pair rules: {dt:.1f}s = {dt/256*1000:.0f} ms/rule")
