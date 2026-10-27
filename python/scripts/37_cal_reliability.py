"""Reliability of clinical attachment loss in repeated charts (spec 013 G5). SYNTHETIC.

    python scripts/37_cal_reliability.py [--seed 13]

Draws repeated full charts with placeholder variance components and probing error, estimates the
patient / tooth / site variance and the measurement error, and reports ICCs and how often the
worst-CAL stage band changes between two charts of the same untreated mouth, for a range of probing
errors. On a real extract, load the site table (patient_id, tooth, site, visit, years, cal_mm) and use
reliability_cal.reml_components instead (unbalanced data). Writes data/datasets/reliability_cal/.
"""

import argparse

import pandas as pd

from dental_omop_nlp import telemetry
from dental_omop_nlp.paths import DATASETS_DIR
from dental_omop_nlp.reliability_cal import (
    CalParams,
    draw_repeated_charts,
    icc_report,
    nested_components,
    stage_band_flips,
)

ap = argparse.ArgumentParser()
ap.add_argument("--seed", type=int, default=13)
ap.add_argument("--patients", type=int, default=100)
ap.add_argument("--teeth", type=int, default=12)
ap.add_argument("--visits", type=int, default=3)
args = ap.parse_args()
telemetry.setup()
telemetry.start_script("37_cal_reliability", data_label="simulated")
out = DATASETS_DIR / "reliability_cal"
out.mkdir(exist_ok=True)

rows = []
for sd_error in (0.0, 0.4, 0.8, 1.2):
    d = draw_repeated_charts(args.patients, args.teeth, args.visits, CalParams(sd_error=sd_error), seed=args.seed)
    c = nested_components(d)
    rows.append({"sd_error_true": sd_error, **c, **icc_report(c), **stage_band_flips(d)})
    if sd_error == 0.8:
        d.to_csv(out / "simulated_cal_charts.csv.gz", index=False)   # read by the R parity test
res = pd.DataFrame(rows)
res.to_csv(out / "simulated_cal_reliability.csv", index=False)
print("SIMULATED charts (placeholder variance components; whole-mm rounding):")
print(res[["sd_error_true", "var_patient", "var_tooth", "var_site", "var_error", "icc_site", "sem_mm",
           "flip_rate", "down_rate"]].round(3).to_string(index=False))
