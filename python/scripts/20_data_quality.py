"""Data quality checks on the structured record (spec 005, US4).

    python scripts/20_data_quality.py

Conformance, completeness and plausibility (incl. temporal) overall and per
clinic; plus, on synthetic data only, how many injected charting errors the
temporal checks catch. Writes data/datasets/data_quality/.
"""

import pandas as pd

from dental_omop_nlp.dq import run_checks
from dental_omop_nlp.paths import DATASETS_DIR
from dental_omop_nlp.plausibility import check_history

TODAY = "2026-10-25"   # fixed so reruns match; use the extract date on real data
v = pd.read_csv(DATASETS_DIR / "visits_structured.csv")
truth = pd.read_csv(DATASETS_DIR / "answer_key" / "visits_truth.csv")[["visit_id", "record_error"]]
out = DATASETS_DIR / "data_quality"
out.mkdir(exist_ok=True)

overall = run_checks(v, TODAY)
clinic = run_checks(v, TODAY, by="clinic_id")
overall.to_csv(out / "dq_overall.csv", index=False)
clinic.to_csv(out / "dq_by_clinic.csv", index=False)

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
print(f"\nSYNTHETIC check: {inj.sum()} injected charting errors, {caught:.0%} flagged; "
      f"{false_alarm:.1%} of other visits flagged")
