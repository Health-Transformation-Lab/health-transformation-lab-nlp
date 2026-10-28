"""Spec 005 US3-US5: clinic prevalence, data quality checks, progression prediction."""

import numpy as np
import pandas as pd
import pytest

from health_transformation_lab_nlp.prevalence import NHANES_2009_2014, prevalence_by, wilson_ci


def test_wilson_ci_known_values():
    lo, hi = wilson_ci(50, 100)
    assert abs(lo - 0.4038) < 1e-3 and abs(hi - 0.5962) < 1e-3
    assert wilson_ci(0, 10)[0] == 0.0 and 0 < wilson_ci(0, 10)[1] < 0.35
    assert np.isnan(wilson_ci(0, 0)[0])


def test_prevalence_by_clinic_person_level():
    v = pd.DataFrame({"person_id": [1, 1, 2, 3, 4], "clinic_id": [1, 1, 1, 2, 2],
                      "visit_date": ["2021-01-01", "2021-07-01", "2021-03-01", "2021-02-01", "2021-02-01"],
                      "status": ["gingivitis", "periodontitis_stage_3", "healthy", "periodontitis_stage_1", "unknown"]})
    t = prevalence_by(v, "status", by="clinic_id").set_index("clinic_id")
    # person-level, latest known visit: clinic 1 -> 1 of 2 periodontitis, 1 of 2 stage III-IV
    assert t.loc[1, "n_people"] == 2 and t.loc[1, "periodontitis"] == 0.5 and t.loc[1, "stage3_4"] == 0.5
    # clinic 2: person 4 has no known status -> excluded, reported as unknown
    assert t.loc[2, "n_people"] == 1 and t.loc[2, "n_unknown"] == 1
    assert {"periodontitis_ci_low", "periodontitis_ci_high"} <= set(t.columns)


def test_published_benchmark_rows():
    b = NHANES_2009_2014
    assert b.loc[b.group == "All adults 30+", "total_pct"].item() == 42.2
    assert b.loc[b.group == "All adults 30+", "severe_pct"].item() == 7.8


def test_data_quality_checks():
    from health_transformation_lab_nlp.dq import run_checks
    v = pd.DataFrame({
        "visit_id": [1, 2, 3], "person_id": [1, 1, 2], "clinic_id": [1, 1, 2],
        "visit_date": ["2021-01-01", "2021-07-01", "2030-01-01"], "age": [40, 40, 130],
        "charted": [True, True, False], "rec_max_probing_depth_mm": [4, 25, None],
        "rec_bop_pct": [20, 30, None], "rec_max_cal_mm": [3, 0.3, None], "rec_rbl_pct": [20, 2, None],
        "rec_teeth_lost_perio": [0, 0, None], "notes": ["periodontitis_stage_2", "unknown", "unknown"],
        "exam_form": ["unknown"] * 3, "proc_dx_completed": ["unknown"] * 3, "probing_chart": [
            "periodontitis_stage_2", "gingivitis", "unknown"]})
    r = run_checks(v, today="2026-10-25").set_index("check")
    assert r.loc["conformance:probing_depth_range", "n_fail"] == 1      # 25 mm
    assert r.loc["conformance:visit_not_future", "n_fail"] == 1
    assert r.loc["plausibility:age_range", "n_fail"] == 1
    assert r.loc["plausibility:temporal_cal_drop", "n_fail"] == 1       # 3 -> 0.3 mm
    assert abs(r.loc["completeness:probing_chart", "pass_rate"] - 2 / 3) < 1e-12
    assert set(r["category"]) == {"conformance", "completeness", "plausibility"}


@pytest.mark.filterwarnings("error")
def test_progression_model_learns_risk_factors():
    from health_transformation_lab_nlp.prediction import FEATURES, make_pairs, train_eval
    rng = np.random.default_rng(0)
    rows = []
    for pid in range(600):
        # every feature varies and none is a copy of another: constant or collinear columns make the
        # unpenalized fit singular (LinAlgWarning), which real visits don't produce
        smoke = int(rng.choice([0, 5, 15], p=[0.55, 0.15, 0.3]))   # 30% smoke 10+ a day, as before
        stage = int(rng.integers(2, 5))
        age, diabetes = int(rng.integers(30, 80)), bool(rng.random() < 0.2)
        for k in range(3):
            if k and rng.random() < (0.5 if smoke >= 10 else 0.1):
                stage = min(stage + 1, 5)
            rows.append({"visit_id": pid * 10 + k, "person_id": pid, "clinic_id": 1, "visit_seq": k,
                         "visit_date": f"202{k}-01-01", "age": age, "cigarettes_per_day": smoke,
                         "diabetes": diabetes, "treated_before": bool(rng.random() < 0.3),
                         "rec_max_probing_depth_mm": int(rng.integers(3, 8)), "rec_bop_pct": int(rng.integers(5, 60)),
                         "rec_max_cal_mm": stage + rng.normal(0, 0.5), "rec_rbl_pct": 10 * stage + rng.normal(0, 4),
                         "rec_teeth_lost_perio": int(rng.integers(0, 3)), "charted": bool(rng.random() < 0.9),
                         "phenotype": ["healthy", "gingivitis", "periodontitis_stage_1", "periodontitis_stage_2",
                                       "periodontitis_stage_3", "periodontitis_stage_4"][stage]})
    pairs = make_pairs(pd.DataFrame(rows), "phenotype")
    assert {"y_progress", *FEATURES} <= set(pairs.columns)
    res = train_eval(pairs, seed=0, n_boot=50)
    assert res["auroc"] > 0.65 and res["auroc_ci_low"] < res["auroc"] < res["auroc_ci_high"]
    imp = res["importance"].set_index("feature")
    assert imp.loc["smoker_10plus", "importance"] > 0


def test_progression_model_is_unpenalized_and_returns_test_predictions():
    """Plain (unpenalized) logistic regression, so R's glm() gives the same model (parity)."""
    from health_transformation_lab_nlp.prediction import FEATURES, train_eval
    rng = np.random.default_rng(1)
    n = 400
    pairs = pd.DataFrame({f: rng.normal(size=n) for f in FEATURES})
    pairs["person_id"] = np.arange(n) // 2
    pairs["visit_id"] = np.arange(n)
    pairs["y_progress"] = (pairs["max_cal_mm"] + rng.normal(size=n) > 0.5).astype(int)
    res = train_eval(pairs, seed=0, n_boot=10)
    tp = res["test_predictions"]
    assert {"visit_id", "person_id", "p"} <= set(tp.columns) and len(tp) == res["n_pairs_test"]
    assert set(tp["person_id"]).isdisjoint(set(pairs.loc[~pairs.visit_id.isin(tp.visit_id), "person_id"]))
    tr = pairs[~pairs.visit_id.isin(tp.visit_id)]          # reference: Newton-Raphson, no penalty (= R glm)
    X = np.column_stack([np.ones(len(tr)), tr[FEATURES].to_numpy()])
    y, beta = tr["y_progress"].to_numpy(), np.zeros(X.shape[1])
    for _ in range(50):
        mu = 1 / (1 + np.exp(-X @ beta))
        beta += np.linalg.solve(X.T @ (X * (mu * (1 - mu))[:, None]), X.T @ (y - mu))
    Xt = np.column_stack([np.ones(len(tp)), pairs.set_index("visit_id").loc[tp.visit_id, FEATURES].to_numpy()])
    assert np.allclose(tp["p"].to_numpy(), 1 / (1 + np.exp(-Xt @ beta)), atol=1e-4)
