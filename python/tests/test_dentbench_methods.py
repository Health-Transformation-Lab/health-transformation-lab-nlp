"""Spec 002: methods reused from GlobalDentBench (arXiv 2605.24636)."""

import pandas as pd
import pytest

from dental_omop_nlp.cost_effectiveness import bakeoff
from dental_omop_nlp.harm import severity, unsafe_rates
from dental_omop_nlp.study import difficulty

H, G = "healthy", "gingivitis"
P1, P2, P3, P4 = (f"periodontitis_stage_{i}" for i in range(1, 5))


@pytest.mark.parametrize("truth,pred,sev", [
    (P3, G, "S2"), (P4, H, "S2"),          # missed advanced disease: irreversible risk
    (P2, H, "S1"), (P1, G, "S1"),          # missed early disease
    (P4, P3, "S1"), (P3, P2, "S1"),        # under-staged advanced disease
    (P2, P1, "S0"),                        # under-staged early disease, same care pathway
    (H, G, "S0"), (G, H, "S0"),            # health vs gingivitis
    (G, P2, "S1"), (H, P1, "S1"),          # over-called: unneeded SRP
    (P1, P2, "S0"), (P1, P3, "S1"),        # over-staged by 1 vs 2+
    (P3, P3, "S0"),
])
def test_severity_matrix(truth, pred, sev):
    assert severity(truth, pred) == sev


def test_unsafe_rates_ignore_non_answers():
    truth = pd.Series([P3, P3, H, G])
    pred = pd.Series([G, P3, "unknown", H])
    r = unsafe_rates(truth, pred)
    assert r["n"] == 3 and abs(r["unsafe_rate"] - 1 / 3) < 1e-12 and abs(r["s2_rate"] - 1 / 3) < 1e-12


@pytest.mark.parametrize("dx_pattern,stated,chart,copy_forward,level", [
    ("d_ext_stage_grade_label", P2, P2, False, "L1"),
    ("legacy_2017", G, G, False, "L1"),
    ("pre2017_severity", P2, P2, False, "L2"),
    ("legacy_old", P2, P2, False, "L2"),
    ("title_case_diagnosis", P3, P3, True, "L2"),
    ("none", P2, P2, False, "L3"),
    ("d_stage_grade_label", P2, P3, False, "L3"),
])
def test_difficulty(dx_pattern, stated, chart, copy_forward, level):
    assert difficulty(dx_pattern, stated, chart, copy_forward) == level


def _gold(judge, n_pos, n_neg, sens, spec):
    rows = []
    for i in range(n_pos):
        rows.append({"judge_model": judge, "truly_correct": True, "gate_ok": True,
                     "verdict": "correct" if i < round(n_pos * sens) else "incorrect"})
    for i in range(n_neg):
        rows.append({"judge_model": judge, "truly_correct": False, "gate_ok": True,
                     "verdict": "incorrect" if i < round(n_neg * spec) else "correct"})
    return rows


def test_bakeoff_picks_best_kappa():
    g = pd.DataFrame(_gold("good", 200, 100, 0.95, 0.92) + _gold("lenient", 200, 100, 0.99, 0.60)
                     + _gold("weak", 200, 100, 0.80, 0.80))
    t = bakeoff(g, classifier_families={"gpt"}, judge_families={"good": "claude", "lenient": "gpt", "weak": "x"})
    assert t.iloc[0]["judge_model"] == "good" and t.iloc[0]["selected"]
    assert {"kappa", "kappa_ci_low", "kappa_ci_high", "same_family_as_classifier"} <= set(t.columns)
    assert t.set_index("judge_model").loc["lenient", "same_family_as_classifier"]
    assert t.iloc[0]["kappa_ci_low"] <= t.iloc[0]["kappa"] <= t.iloc[0]["kappa_ci_high"]
