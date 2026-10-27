"""Shared scorer (eval/score.py; eval/score.R is the R twin, checked by the parity test)."""

import sys

import pytest

from dental_omop_nlp.paths import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "eval"))
from score import score  # noqa: E402

H, G, S2, S4 = "healthy", "gingivitis", "periodontitis_stage_2", "periodontitis_stage_4"


def _m(res):
    return res[res["class"] == ""].set_index("metric")["value"]


def test_periodontitis_yes_no_sensitivity_specificity_ppv_npv():
    # truth:  P P P N N   (P = any periodontitis stage)
    # pred:   P P N P N   -> tp 2, fn 1, fp 1, tn 1; a wrong stage still counts as "yes"
    m = _m(score([S2, S4, S2, H, G], [S4, S2, G, S2, H], None, "t"))
    assert m["sensitivity"] == pytest.approx(2 / 3)
    assert m["specificity"] == pytest.approx(1 / 2)
    assert m["ppv"] == pytest.approx(2 / 3)
    assert m["npv"] == pytest.approx(1 / 2)


def test_no_prediction_counts_as_no_and_undefined_values_are_missing():
    m = _m(score([S2, H], ["none", "none"], None, "t"))   # "none": the system gave no status
    assert m["sensitivity"] == 0 and m["npv"] == pytest.approx(1 / 2)
    assert m["ppv"] is None or m["ppv"] != m["ppv"]   # no "yes" calls: undefined
