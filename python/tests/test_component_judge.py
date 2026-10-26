"""Spec 002 T011: status, grade and extent judged as separate verdicts (GlobalDentBench's key points)."""

import pandas as pd

from dental_omop_nlp import judge
from dental_omop_nlp.cost_effectiveness import calibrate_components

NOTE = "Perio charting: CAL 6 mm #3.\nDx: generalized periodontitis stage III grade B."


def test_component_prompt_asks_for_each_component_and_carries_the_rules():
    assert judge.COMPONENTS == ("status", "grade", "extent")
    for c in judge.COMPONENTS:
        assert f'"{c}"' in judge.COMPONENT_SYSTEM
    assert judge.CRITERIA in judge.COMPONENT_SYSTEM
    u = judge.COMPONENT_USER.format(note=NOTE, status="periodontitis_stage_3", grade="B", extent="generalized")
    assert "grade: B" in u and "extent: generalized" in u


def test_component_gate_checks_each_quote_and_value():
    out = {"status": {"verdict": "correct", "supported": "periodontitis_stage_3", "quote": "CAL 6 mm #3."},
           "grade": {"verdict": "correct", "supported": "B", "quote": "grade B"},
           "extent": {"verdict": "incorrect", "supported": "localized", "quote": "localized disease"}}
    ok = judge.gate_components(NOTE, out, pred_status="periodontitis_stage_3")
    assert ok == {"status": (True, ""), "grade": (True, ""), "extent": (False, "quote not in note")}
    bad = {**out, "grade": {"verdict": "correct", "supported": "Z", "quote": "grade B"}}
    assert judge.gate_components(NOTE, bad, "periodontitis_stage_3")["grade"] == (False, "bad grade")


def test_grade_and_extent_not_applicable_unless_periodontitis():
    out = {"status": {"verdict": "correct", "supported": "gingivitis", "quote": "CAL 6 mm #3."},
           "grade": {"verdict": "not_applicable", "supported": None, "quote": ""},
           "extent": {"verdict": "not_applicable", "supported": None, "quote": ""}}
    ok = judge.gate_components(NOTE, out, pred_status="gingivitis")
    assert ok["grade"] == (True, "") and ok["extent"] == (True, "")


def test_simulated_component_judge_errs_per_component():
    truth = {1: {"status": "periodontitis_stage_3", "grade": "B", "extent": "generalized"}}
    j = judge.SimulatedComponentJudge(truth, seed=0)
    v = j(NOTE, {"status": "periodontitis_stage_3", "grade": "C", "extent": "generalized"}, visit_id=1)
    assert set(v) == set(judge.COMPONENTS) and all(x.verdict in ("correct", "incorrect", "not_determinable")
                                                    for x in v.values())


def test_calibration_per_component():
    gold = pd.DataFrame({"component": ["status"] * 4 + ["grade"] * 4,
                         "verdict": ["correct", "correct", "incorrect", "incorrect"] * 2,
                         "truly_correct": [True, False, False, False, True, False, True, False],
                         "gate_ok": True})
    c = calibrate_components(gold).set_index("component")
    assert c.loc["status", "sensitivity"] == 1.0 and c.loc["status", "specificity"] == 2 / 3
    assert c.loc["grade", "sensitivity"] == 0.5 and c.loc["grade", "specificity"] == 0.5
