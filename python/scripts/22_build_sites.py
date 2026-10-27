"""Site-level synthetic charts for every charted visit, and the derived measures (spec 006).

    python scripts/22_build_sites.py

For each charted visit: 32 teeth x 6 sites (PD, CAL, bleeding) and per-tooth
status, furcation and mobility, generated from that visit's recorded chart
(sites.draw_mouth). Then the derived measures and two classifications from
the sites: 2017 AAP/EFP stage and 2012 CDC/AAP category.

Writes data/sites/{sites,teeth}.parquet (gitignored), data/sites/derived.csv,
data/sites/parity_{sites,teeth}.csv (small sample for the R parity test) and
data/sites/aap_vs_cdc.csv.
"""

import random

import pandas as pd

from dental_omop_nlp.labels import PerioChart
from dental_omop_nlp.paths import DATASETS_DIR, REPO_ROOT
from dental_omop_nlp.sites import aap_from_derived, cdc_aap, derive_all, draw_mouth_columns

OUT = REPO_ROOT / "data" / "sites"
OUT.mkdir(parents=True, exist_ok=True)
v = pd.read_csv(DATASETS_DIR / "visits_structured.csv")
v = v[v["charted"].astype(str).str.lower() == "true"]
assert v["visit_id"].is_unique, "derive_all groups by visit_id: duplicate visits would merge"

# column lists for all visits, one table each at the end (thousands of small tables are slow)
site_cols = {c: [] for c in ("tooth", "site", "pd_mm", "cal_mm", "bop", "visit_id", "person_id")}
tooth_cols = {c: [] for c in ("tooth", "present", "missing_reason", "furcation_class", "mobility_degree",
                              "visit_id", "person_id")}
for r in v.itertuples():
    rng = random.Random(r.visit_id * 104729 + 7)
    chart = PerioChart(r.rec_max_probing_depth_mm, r.rec_bop_pct, r.rec_max_cal_mm, r.rec_rbl_pct,
                       int(r.rec_teeth_lost_perio))
    s, t = draw_mouth_columns(chart, r.rec_pct_teeth_involved, rng)
    for cols, part in ((site_cols, s), (tooth_cols, t)):
        n = len(part["tooth"])
        for c, x in part.items():
            cols[c].extend(x)
        cols["visit_id"].extend([r.visit_id] * n)
        cols["person_id"].extend([r.person_id] * n)

sites = pd.DataFrame(site_cols)
teeth = pd.DataFrame(tooth_cols)
d = derive_all(sites, teeth).to_dict("index")   # all visits in one pass, keyed by visit_id
rows = [{"visit_id": r.visit_id, "person_id": r.person_id, "clinic_id": r.clinic_id, "age": r.age,
         **d[r.visit_id], "aap_2017": aap_from_derived(d[r.visit_id], r.rec_rbl_pct),
         "cdc_aap_2012": cdc_aap(d[r.visit_id])}
        for r in v.itertuples()]
derived = pd.DataFrame(rows)
sites.to_parquet(OUT / "sites.parquet")
teeth.to_parquet(OUT / "teeth.parquet")
derived.to_csv(OUT / "derived.csv", index=False)
sample = derived["visit_id"].head(200)
sites[sites.visit_id.isin(sample)].to_csv(OUT / "parity_sites.csv", index=False)
teeth[teeth.visit_id.isin(sample)].to_csv(OUT / "parity_teeth.csv", index=False)
xt = pd.crosstab(derived["aap_2017"], derived["cdc_aap_2012"])
xt.to_csv(OUT / "aap_vs_cdc.csv")

print(f"SYNTHETIC: {len(derived)} charted exams, {len(sites):,} site rows, {len(teeth):,} tooth rows")
print("\n2017 AAP/EFP stage (rows) vs 2012 CDC/AAP category (columns), from the same sites:")
print(xt.to_string())
