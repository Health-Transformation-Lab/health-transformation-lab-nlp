"""The README's results leaderboards are generated from committed results and stay in sync."""

import pandas as pd
import pytest

from dental_omop_nlp import readme_results as rr
from dental_omop_nlp.paths import REPO_ROOT


@pytest.fixture(scope="module")
def inp():
    return rr.load_inputs()


@pytest.fixture(scope="module")
def md(inp):
    return rr.results_markdown(inp)


def _rows(section):
    return [r for r in section.splitlines() if r.startswith("| ") and not r.startswith("| Rank")]


def _section(md, title):
    return md.split(title, 1)[1].split("\n### ", 1)[0]


def test_readme_block_matches_the_committed_results(md):
    readme = (REPO_ROOT / "README.md").read_text()
    assert readme.count(rr.START) == 1 and readme.count(rr.END) == 1
    assert rr.update_readme(readme, md) == readme, "README results are stale: run python scripts/35_readme_results.py"


def test_ci_rank_only_separates_non_overlapping_intervals():
    # b's CI overlaps a's, so they tie; c is clearly below both
    assert rr.ci_rank([0.9, 0.85, 0.5], [0.8, 0.75, 0.4], [0.95, 0.9, 0.6]) == [1, 1, 3]


def test_wilson_interval():
    lo, hi = rr.wilson(90, 100)
    assert 0.82 < lo < 0.83 and 0.94 < hi < 0.95
    assert all(pd.isna(x) for x in rr.wilson(0, 0))


def test_note_reader_leaderboard_has_every_system_by_rank_then_score(inp, md):
    sec = _section(md, rr.READERS_TITLE)
    rows, ladder = _rows(sec), inp["ladder"]
    assert len(rows) == len(ladder)
    acc = ladder.set_index("method")["accuracy"]
    order = []
    for r in rows:
        m = next(m for m in ladder["method"] if f"`{m}`" in r.split("|")[2])
        assert f"{acc[m]:.1%}" in r, m
        order.append((int(r.split("|")[1]), -acc[m]))
    assert len(order) == len(set(ladder["method"]))
    assert order == sorted(order)
    assert order[0][0] == 1


def test_macro_f1_matches_sklearn(inp):
    from sklearn.metrics import f1_score
    from dental_omop_nlp.labels import LABELS
    p = inp["preds"]
    want = f1_score(p["truth"], p["note_rules"].fillna("none"), labels=LABELS, average="macro", zero_division=0)
    assert rr.macro_f1(p["truth"], p["note_rules"]) == pytest.approx(want)


def test_medgemma_row_shows_difficulty_levels(inp, md):
    row = next(r for r in _rows(_section(md, rr.READERS_TITLE)) if "`medgemma-1.5-4b-it`" in r)
    lv = inp["by_diff"].query("method == 'medgemma-1.5-4b-it'").set_index("difficulty")["accuracy"]
    assert f"{lv['L1']:.0%} / {lv['L2']:.0%} / {lv['L3']:.0%}" in row
    assert "zero-shot" in row


def test_models_not_run_are_listed_not_dropped(inp, md):
    scored = {rr.base_id(m) for m in inp["ladder"]["method"]}
    not_run = md.split(rr.NOT_RUN, 1)[1].split("\n\n", 1)[0]
    for m in inp["registry"]["models"]:
        if m["id"] not in scored:
            assert f"`{m['id']}`" in not_run, m["id"]


def test_phenotype_leaderboard_covers_the_rule_phenotypes_and_each_evidence_type(md):
    rows = _rows(_section(md, rr.PHENOTYPE_TITLE))
    for system in (*rr.PHENOTYPES, *rr.EVIDENCE):
        assert sum(f"`{system}`" in r for r in rows) == 1, system


def test_deid_leaderboard_has_every_engine_and_the_external_sets(inp, md):
    sec = _section(md, rr.DEID_TITLE)
    rows = _rows(sec)
    engines = inp["deid"].query("tier == 'all'")["method"]
    assert len(rows) == len(engines)
    for e in engines:
        assert sum(f"`{e}`" in r.split("|")[2] and r.split("|")[2].strip() == f"`{e}`" for r in rows) == 1, e
    assert "ASQ-PHI" in sec and "MACCROBAT" in sec
    for e in inp["deid_not_run"]["method"]:
        assert f"`{e}`" in sec, e


def test_block_says_synthetic_and_not_clinical(md):
    assert "synthetic" in md.lower() and "not clinical performance" in md


def test_update_readme_replaces_only_the_block():
    text = f"intro\n{rr.START}\nold\n{rr.END}\noutro\n"
    assert rr.update_readme(text, "new") == f"intro\n{rr.START}\nnew\n{rr.END}\noutro\n"
