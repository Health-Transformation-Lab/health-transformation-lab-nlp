"""Data quality checks on the structured record (spec 005, US4).

    python scripts/20_data_quality.py

Conformance, completeness and plausibility (incl. temporal) overall and per
clinic; plus, on synthetic data only, how many injected charting errors the
temporal checks catch. Writes data/datasets/data_quality/.
"""

import pandas as pd

from health_transformation_lab_nlp import telemetry
from health_transformation_lab_nlp.completeness import (
    CHART_INPUTS,
    column_completeness,
    prevalence_by_scale,
    row_completeness,
)
from health_transformation_lab_nlp.dq import run_checks
from health_transformation_lab_nlp.paths import DATASETS_DIR
from health_transformation_lab_nlp.plausibility import check_history, transition_pairs, transition_summary

telemetry.setup()
telemetry.start_script("20_data_quality", data_label="synthetic")
TODAY = "2026-10-25"   # fixed so reruns match; use the extract date on real data
v = pd.read_csv(DATASETS_DIR / "visits_structured.csv")
truth = pd.read_csv(DATASETS_DIR / "answer_key" / "visits_truth.csv")[["visit_id", "record_error"]]
out = DATASETS_DIR / "data_quality"
out.mkdir(exist_ok=True)

overall = run_checks(v, TODAY)
clinic = run_checks(v, TODAY, by="clinic_id")
overall.to_csv(out / "dq_overall.csv", index=False)
clinic.to_csv(out / "dq_by_clinic.csv", index=False)
for r in overall.itertuples():                       # one point per check per run: trend and anomaly input
    telemetry.record_value("data_quality.pass_rate", r.pass_rate, check=r.check, category=r.category)

# temporal plausibility of each method's calls over time
rates = []
hist = v.rename(columns={"rec_max_cal_mm": "max_cal_mm", "rec_rbl_pct": "rbl_pct",
                         "rec_teeth_lost_perio": "teeth_lost_perio"})
for m in ("algorithm_design", "algorithm_v0", "notes", "probing_chart", "exam_form", "proc_dx_completed"):
    f = check_history(hist, status_col=m)
    later = f[f["visit_id"].isin(v.loc[v.duplicated("person_id"), "visit_id"])]
    rates.append({"method": m, "n_later_visits": len(later),
                  **{k: float(later[k].mean()) for k in ("perio_resolved", "stage_drop")}})
pd.DataFrame(rates).to_csv(out / "temporal_by_method.csv", index=False)

# transitions 1-2 years on, untreated people only (spec 013 G8): improvement is implausible
trans = []
for m in ("algorithm_design", "algorithm_v0", "notes", "probing_chart", "exam_form", "proc_dx_completed"):
    pairs = transition_pairs(v, status_col=m)
    matrix, shares = transition_summary(pairs)
    trans.append({"method": m, **shares})
    if m == "algorithm_design":
        matrix.to_csv(out / "transitions_algorithm_design.csv")      # Sankey input
        pairs.to_csv(out / "transition_pairs_algorithm_design.csv", index=False)   # read by the R parity test
pd.DataFrame(trans).to_csv(out / "transitions_by_method.csv", index=False)

# completeness after Zozus et al. (spec 013 G7): column values, rows, and prevalence on three scales
METHODS = ["algorithm_design", "notes", "exam_form", "proc_dx_planned", "probing_chart"]
column_completeness(v, METHODS + CHART_INPUTS).to_csv(out / "completeness_columns.csv", index=False)
row = row_completeness(v, CHART_INPUTS)
pd.DataFrame([{"calculation": "probing_chart_algorithm", **row}]).to_csv(out / "completeness_rows.csv", index=False)
scales = pd.concat([prevalence_by_scale(v, m) for m in METHODS], ignore_index=True)
scales.to_csv(out / "prevalence_by_scale.csv", index=False)       # also read by the R parity test

# injected errors caught (synthetic only: the error flag lives in the answer key)
f = check_history(hist, status_col="probing_chart")
f.to_csv(out / "flags_probing_chart.csv", index=False)      # also read by the R parity test
f = f.merge(truth, on="visit_id")
inj = f["record_error"].fillna("") != ""
caught = f.loc[inj, "any_flag"].mean() if inj.any() else float("nan")
false_alarm = f.loc[~inj, "any_flag"].mean()
pd.DataFrame([{"injected_errors": int(inj.sum()), "caught_share": caught, "flag_rate_without_error": false_alarm}]) \
    .to_csv(out / "injected_error_recall.csv", index=False)

print(overall.round(3).to_string(index=False))
print("\ntemporal plausibility of each method's calls (share of follow-up visits flagged):")
print(pd.DataFrame(rates).round(3).to_string(index=False))
print("\nphenotype 1-2 years later, untreated (share of pairs better / same / worse):")
print(pd.DataFrame(trans).round(3).to_string(index=False))
print(f"\nchart rows with every input: {row['pct_complete']:.1f}% of {row['n_rows']} charted visits")
print(scales.pivot(index="status_col", columns="scale", values="periodontitis").round(3).to_string())
print(f"\nSYNTHETIC check: {inj.sum()} injected charting errors, {caught:.0%} flagged; "
      f"{false_alarm:.1%} of other visits flagged")
