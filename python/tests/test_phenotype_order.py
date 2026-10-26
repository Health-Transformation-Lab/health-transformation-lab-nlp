"""Spec 005 US1: five-category integrated phenotype with a configurable source order."""

import pandas as pd

from dental_omop_nlp.phenotype import (
    DESIGN_GROUPS,
    FIVE,
    RULES_DESIGN,
    collapse5,
    phenotype,
    rules_for_order,
    score_orders,
)

U = "unknown"


def test_collapse5():
    s = pd.Series(["healthy", "gingivitis", "periodontitis_stage_3", U, "no_consensus"])
    assert list(collapse5(s)) == ["healthy_gingivitis", "healthy_gingivitis", "periodontitis_stage_3", U,
                                  "no_consensus"]
    assert FIVE[0] == "healthy_gingivitis" and len(FIVE) == 5


def test_design_order_is_exam_form_then_dx_code_then_notes_then_chart():
    assert RULES_DESIGN["priority"] == ["exam_form", "proc_dx_completed", "proc_dx_planned", "notes", "probing_chart"]
    row = pd.Series({"exam_form": U, "proc_dx_completed": "periodontitis_stage_2", "notes": "periodontitis_stage_3",
                     "probing_chart": "periodontitis_stage_4", "radiograph_ai": U})
    assert phenotype(row, RULES_DESIGN) == ("periodontitis_stage_2", "proc_dx_completed")
    row["exam_form"] = "gingivitis"
    assert phenotype(row, RULES_DESIGN)[1] == "exam_form"


def test_rules_for_order_expands_groups():
    r = rules_for_order(["probing_chart", "notes", "dx_code", "exam_form"])
    assert r["priority"] == ["probing_chart", "notes", "proc_dx_completed", "proc_dx_planned", "exam_form"]
    assert set(DESIGN_GROUPS) == {"exam_form", "dx_code", "notes", "probing_chart"}


def test_score_orders_selects_on_one_half_and_reports_the_other():
    n = 120
    truth = ["periodontitis_stage_2" if i % 2 else "gingivitis" for i in range(n)]
    key = pd.DataFrame({"visit_id": range(n), "exam_form": [U] * n,
                        "proc_dx_completed": ["periodontitis_stage_1"] * n,      # always wrong-ish
                        "proc_dx_planned": [U] * n, "notes": truth, "probing_chart": truth,
                        "radiograph_ai": [U] * n}).set_index("visit_id")
    wide = pd.DataFrame({f"r{j}": truth for j in range(3)}, index=key.index)
    t = score_orders(key, wide, n_boot=0, seed=1)
    assert len(t) == 24 and {"order", "select_kappa", "holdout_kappa", "selected"} <= set(t.columns)
    best = t[t["selected"]].iloc[0]
    assert not best["order"].startswith("dx_code")
    assert t["select_kappa"].max() == best["select_kappa"]


def test_split_is_exposed_so_r_can_reuse_it():
    from dental_omop_nlp.phenotype import split_halves
    ids = list(range(10, 50))
    sel, hold = split_halves(ids, seed=4)
    assert sel | hold == set(ids) and not sel & hold and len(sel) == 20
    assert split_halves(ids, seed=4) == (sel, hold)
