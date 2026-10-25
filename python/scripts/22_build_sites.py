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
from dental_omop_nlp.sites import aap_from_derived, cdc_aap, derive, draw_mouth

OUT = REPO_ROOT / "data" / "sites"
OUT.mkdir(parents=True, exist_ok=True)
v = pd.read_csv(DATASETS_DIR / "visits_structured.csv")
v = v[v["charted"].astype(str).str.lower() == "true"]

site_parts, tooth_parts, rows = [], [], []
for r in v.itertuples():
    rng = random.Random(r.visit_id * 104729 + 7)
    chart = PerioChart(r.rec_max_probing_depth_mm, r.rec_bop_pct, r.rec_max_cal_mm, r.rec_rbl_pct,
                       int(r.rec_teeth_lost_perio))
    sites, teeth = draw_mouth(chart, r.rec_pct_teeth_involved, rng)
    ids = {"visit_id": r.visit_id, "person_id": r.person_id}
    site_parts.append(sites.assign(**ids))
    tooth_parts.append(teeth.assign(**ids))
    d = derive(sites, teeth)
    rows.append({**ids, "clinic_id": r.clinic_id, "age": r.age, **d,
                 "aap_2017": aap_from_derived(d, r.rec_rbl_pct), "cdc_aap_2012": cdc_aap(d)})

sites = pd.concat(site_parts, ignore_index=True)
teeth = pd.concat(tooth_parts, ignore_index=True)
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
