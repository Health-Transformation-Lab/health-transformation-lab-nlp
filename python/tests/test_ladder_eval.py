"""Model ladder against the synthetic truth: accuracy with paired bootstrap CIs, stage IV recall,
unsafe errors, calibration, and the rules-decide-stage-IV hybrid (spec 002 T015)."""

import numpy as np
import pandas as pd
import pytest

from dental_omop_nlp import ladder_eval
from dental_omop_nlp.labels import LABELS

S4 = "periodontitis_stage_4"


def test_rules_override_takes_the_rule_answer_only_for_stage_iv():
    model = pd.Series(["healthy", "periodontitis_stage_3", "gingivitis"])
    rules = pd.Series([S4, "healthy", "gingivitis"])
    assert list(ladder_eval.rules_override(model, rules)) == [S4, "periodontitis_stage_3", "gingivitis"]


def test_expected_calibration_error():
    truth = pd.Series(["healthy", "healthy", "gingivitis", "gingivitis"])
    proba = pd.DataFrame(0.0, index=truth.index, columns=LABELS)
    proba["healthy"] = [0.9, 0.9, 0.9, 0.9]                   # always 90% sure of healthy; right half the time
    proba["gingivitis"] = [0.1, 0.1, 0.1, 0.1]
    assert ladder_eval.expected_calibration_error(truth, proba) == pytest.approx(0.4)


def test_ladder_table_point_estimates_and_paired_difference():
    truth = pd.Series(["healthy"] * 6 + [S4] * 4)
    perfect = truth.copy()
    misses_s4 = pd.Series(["healthy"] * 10)
    t = ladder_eval.ladder_table(truth, {"note_rules": perfect, "m": misses_s4}, n_boot=200, seed=1,
                                 reference="note_rules").set_index("method")
    assert t.loc["m", "accuracy"] == pytest.approx(0.6)
    assert t.loc["m", "stage4_recall"] == 0.0 and t.loc["note_rules", "stage4_recall"] == 1.0
    assert t.loc["m", "s2_rate"] == pytest.approx(0.4)        # stage IV called healthy: irreversible harm
    assert t.loc["m", "diff_vs_ref"] == pytest.approx(-0.4)
    assert t.loc["m", "diff_hi"] < 0                         # clearly worse, even allowing for resampling
    assert t.loc["m", "acc_lo"] <= 0.6 <= t.loc["m", "acc_hi"]
    assert np.isnan(t.loc["m", "ece"])                        # no probabilities given


def test_ladder_table_is_seeded():
    truth = pd.Series(["healthy", "gingivitis"] * 20)
    pred = pd.Series(["healthy"] * 40)
    a = ladder_eval.ladder_table(truth, {"note_rules": truth, "m": pred}, n_boot=100, seed=3)
    b = ladder_eval.ladder_table(truth, {"note_rules": truth, "m": pred}, n_boot=100, seed=3)
    pd.testing.assert_frame_equal(a, b)
