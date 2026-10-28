"""Spec 013 G1-G3: ACES (Holtfreter et al. 2024) staging from site and tooth tables, as applied by
Tay et al. 2025 (PMC12176459), Holde et al. 2025 (PMC12003053) and Nafz et al. 2026 (PMC13263721)."""

import pandas as pd
import pytest

from dental_omop_nlp.aces import AcesRules, aces, occluding_pairs

ALL = [t for t in range(1, 33) if t not in (1, 16, 17, 32)]     # no third molars


def mouth(cal=None, pd_=None, bop=None, present=ALL, lost_perio=()):
    """Every present tooth healthy (CAL 0, PD 2) unless overridden: cal/pd_ = {(tooth, site): mm}."""
    cal, pd_, bop = cal or {}, pd_ or {}, bop or set()
    s = [{"tooth": t, "site": x, "cal_mm": cal.get((t, x), 0.0), "pd_mm": pd_.get((t, x), 2.0),
          "bop": (t, x) in bop} for t in present for x in ("MB", "B", "DB", "ML", "L", "DL")]
    teeth = [{"tooth": t, "present": t in present,
              "missing_reason": "" if t in present else ("perio" if t in lost_perio else "other")}
             for t in range(1, 33)]
    return pd.DataFrame(s, columns=["tooth", "site", "cal_mm", "pd_mm", "bop"]), pd.DataFrame(teeth)


def test_occluding_pairs_count_opposing_natural_teeth_without_third_molars():
    _, t = mouth()
    assert occluding_pairs(t) == 14
    _, t = mouth(present=[x for x in ALL if x not in (3, 14, 19)])   # 3 opposes 30, 14 opposes 19
    assert occluding_pairs(t) == 12


def test_healthy_and_gingivitis_by_bleeding():
    s, t = mouth()
    assert aces(s, t)["status"] == "healthy"
    bleed = {(tt, x) for tt in ALL[:6] for x in ("MB", "B", "DB")}      # 18 of 168 sites, > 10%
    s, t = mouth(bop=bleed)
    assert aces(s, t)["status"] == "gingivitis"


def test_case_needs_two_non_adjacent_teeth():
    s, t = mouth(cal={(3, "MB"): 2, (4, "DB"): 2})              # adjacent: not a case
    assert aces(s, t)["status"] == "healthy"
    s, t = mouth(cal={(3, "MB"): 2, (5, "DB"): 2})
    assert aces(s, t)["status"] == "periodontitis_stage_1"


def test_buccal_or_oral_cal_with_pocketing_also_makes_a_case():
    s, t = mouth(cal={(3, "B"): 3, (8, "L"): 3}, pd_={(3, "B"): 4, (8, "L"): 4})
    r = aces(s, t)
    assert r["status"] == "periodontitis_stage_1" and r["case_route"] == "buccal_oral"
    s, t = mouth(cal={(3, "B"): 3, (8, "L"): 3}, pd_={(3, "B"): 3, (8, "L"): 3})
    assert aces(s, t)["status"] == "healthy"                   # Tay: PD > 3 mm
    assert aces(s, t, AcesRules(buccal_pd_min_mm=3))["status"] == "periodontitis_stage_1"   # Holde: >= 3


def test_stage_two_and_pd6_complexity_moves_to_three():
    s, t = mouth(cal={(3, "MB"): 4, (12, "DL"): 3})
    assert aces(s, t)["status"] == "periodontitis_stage_2"
    s, t = mouth(cal={(3, "MB"): 4, (12, "DL"): 3}, pd_={(3, "B"): 6, (12, "L"): 6})
    assert aces(s, t)["status"] == "periodontitis_stage_3"
    assert aces(s, t, AcesRules(complexity=False))["status"] == "periodontitis_stage_2"
    # PD 6 on the distal of second molars (2, 15, 18, 31) does not count
    s, t = mouth(cal={(3, "MB"): 4, (12, "DL"): 3}, pd_={(2, "DB"): 6, (15, "DL"): 6})
    assert aces(s, t)["status"] == "periodontitis_stage_2"


def test_stage_three_or_four_by_the_chosen_rule():
    cal = {(3, "MB"): 6, (12, "DL"): 5}
    full = mouth(cal=cal)
    gone = [3, 4, 5, 6, 7]                     # upper only: 23 teeth (>= 20) but 9 opposing pairs (< 10)
    few = mouth(cal={(8, "MB"): 6, (11, "DL"): 5}, present=[x for x in ALL if x not in gone], lost_perio=gone[:3])
    assert aces(*full)["status"] == "periodontitis_stage_3"
    assert aces(*few)["status"] == "periodontitis_stage_4"                       # < 10 opposing pairs
    assert aces(*few, AcesRules(stage4_rule="teeth20"))["status"] == "periodontitis_stage_3"
    assert aces(*few, AcesRules(stage4_rule="teeth_lost_perio"))["status"] == "periodontitis_stage_3"
    assert aces(*few, AcesRules(stage4_rule="all_missing_perio"))["status"] == "periodontitis_stage_4"
    assert aces(*few, AcesRules(complexity=False))["status"] == "periodontitis_stage_3_4"


def test_tokede_threshold_needs_cal_above_2mm():
    s, t = mouth(cal={(3, "MB"): 2, (8, "DB"): 2})
    assert aces(s, t)["status"] == "periodontitis_stage_1"
    assert aces(s, t, AcesRules(case_cal_min_mm=3))["status"] == "healthy"


def test_edentulous_non_classified_and_extent():
    s, t = mouth(present=[])
    assert aces(s, t)["status"] == "edentulous"
    s, t = mouth(present=[8])
    assert aces(s, t)["status"] == "non_classified"
    s, t = mouth(cal={(3, "MB"): 2, (8, "DB"): 2})
    assert aces(s, t)["extent"] == "localized"
    s, t = mouth(cal={(tt, "MB"): 2 for tt in ALL[:9]})                  # 9 of 28 teeth >= 30%
    assert aces(s, t)["extent"] == "generalized"


def test_unknown_rule_is_an_error():
    with pytest.raises(ValueError):
        AcesRules(stage4_rule="guess")


@pytest.mark.parametrize("rules", [AcesRules(), AcesRules(stage4_rule="teeth20"), AcesRules(complexity=False),
                                   AcesRules(case_cal_min_mm=3), AcesRules(stage4_rule="all_missing_perio")])
def test_vectorized_matches_one_exam_at_a_time(rules):
    import random

    from dental_omop_nlp.aces import aces_all
    sites, teeth = [], []
    for k in range(120):
        rng = random.Random(k)
        present = [t for t in ALL if rng.random() > rng.choice([0.05, 0.3, 0.7, 0.97])]
        cal = {(t, x): rng.choice([0, 0, 1, 2, 3, 4, 5, 6]) for t in present for x in ("MB", "B", "DL", "L")
               if rng.random() < 0.3}
        pd_ = {(t, x): rng.choice([3, 4, 5, 6, 7]) for t in present for x in ("B", "DB", "L") if rng.random() < 0.2}
        bop = {(t, "B") for t in present if rng.random() < 0.3}
        s, t = mouth(cal, pd_, bop, present, lost_perio=[x for x in ALL if x not in present][:rng.randint(0, 6)])
        sites.append(s.assign(visit_id=k))
        teeth.append(t.assign(visit_id=k))
    S, T = pd.concat(sites), pd.concat(teeth)
    v = aces_all(S, T, rules).set_index("visit_id")
    for k in range(120):
        one = aces(sites[k], teeth[k], rules)
        for c in ("status", "extent", "occluding_pairs", "n_teeth", "case_route"):
            assert v.loc[k, c] == one[c], (k, c, v.loc[k, c], one[c])
