"""The README's results leaderboards (one per capability) are generated from committed results and stay in sync."""

import numpy as np
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


def _cell(row, i):
    return row.split("|")[i].strip()


def test_readme_block_matches_the_committed_results(md):
    readme = (REPO_ROOT / "README.md").read_text()
    assert readme.count(rr.START) == 1 and readme.count(rr.END) == 1
    assert rr.update_readme(readme, md) == readme, "README results are stale: run python scripts/35_readme_results.py"


def test_one_leaderboard_per_capability_and_no_overall_rank(md):
    assert [line for line in md.splitlines() if line.startswith("### ")] == [rr.PHENOTYPE_TITLE, rr.DEID_TITLE]
    assert "overall" not in md.lower()


def test_paired_rank_range():
    rng = np.random.default_rng(1)
    strong = rng.random(200) < 0.95
    correct = {"a": strong, "a_copy": strong.copy(), "b": rng.random(200) < 0.5}
    rr_ = rr.paired_rank_range(correct, n_boot=200, seed=0)
    assert rr_["a"] == rr_["a_copy"] == (1, 1)     # identical systems tie; ties share the better rank
    assert rr_["b"] == (3, 3)


def test_interval_rank_range():
    # b overlaps a, so it could be 1st or 2nd; c is clearly last
    assert rr.interval_rank_range([0.8, 0.75, 0.4], [0.95, 0.9, 0.6]) == [(1, 2), (1, 2), (3, 3)]


def test_wilson_interval():
    lo, hi = rr.wilson(90, 100)
    assert 0.82 < lo < 0.83 and 0.94 < hi < 0.95
    assert all(pd.isna(x) for x in rr.wilson(0, 0))


def test_phenotype_leaderboard_has_every_system_best_first(inp, md):
    rows = _rows(_section(md, rr.PHENOTYPE_TITLE))
    systems = [*inp["ladder"]["method"], *rr.PHENOTYPES, *rr.EVIDENCE]
    assert len(rows) == len(systems) == len(set(systems))
    names = [_cell(r, 2) for r in rows]
    for s in systems:
        assert sum(f"`{s}`" == n or n.startswith(f"[`{s}`]") for n in names) == 1, s
    acc = [float(_cell(r, 5).split("**")[1].rstrip("%")) for r in rows]
    assert acc == sorted(acc, reverse=True)
    assert _cell(rows[0], 1).startswith("1")


def test_note_model_accuracy_and_ci_match_the_ladder_file(inp, md):
    rows = _rows(_section(md, rr.PHENOTYPE_TITLE))
    for _, r in inp["ladder"].iterrows():
        row = next(x for x in rows if _cell(x, 2) in (f"`{r['method']}`",) or _cell(x, 2).startswith(f"[`{r['method']}`]"))
        assert f"**{r['accuracy']:.1%}** ({r['acc_lo']:.1%}–{r['acc_hi']:.1%})" in row, r["method"]


def test_macro_f1_matches_sklearn(inp):
    from sklearn.metrics import f1_score
    from dental_omop_nlp.labels import LABELS
    p = inp["preds"]
    want = f1_score(p["truth"], p["note_rules"].fillna("none"), labels=LABELS, average="macro", zero_division=0)
    assert rr.macro_f1(p["truth"], p["note_rules"]) == pytest.approx(want)


def test_difficulty_levels_match_the_medgemma_comparison(inp, md):
    rows = _rows(_section(md, rr.PHENOTYPE_TITLE))
    lv = inp["by_diff"].pivot(index="method", columns="difficulty", values="accuracy")
    for m in lv.index:
        row = next(x for x in rows if _cell(x, 2).startswith(f"[`{m}`]") or _cell(x, 2) == f"`{m}`")
        assert f"{lv.loc[m, 'L1']:.0%} / {lv.loc[m, 'L2']:.0%} / {lv.loc[m, 'L3']:.0%}" in row, m
    assert "zero-shot" in next(x for x in rows if "`medgemma-1.5-4b-it`" in x)


def test_models_not_run_are_listed_not_dropped(inp, md):
    scored = {rr.base_id(m) for m in inp["ladder"]["method"]}
    not_run = _section(md, rr.PHENOTYPE_TITLE).split(rr.NOT_RUN, 1)[1]
    for m in inp["registry"]["models"]:
        if m["id"] not in scored:
            assert f"`{m['id']}`" in not_run, m["id"]


def test_deid_leaderboard_has_every_engine_and_the_external_sets(inp, md):
    sec = _section(md, rr.DEID_TITLE)
    rows = _rows(sec)
    engines = list(inp["deid"].query("tier == 'all'")["method"])
    assert sorted(_cell(r, 2).strip("`") for r in rows) == sorted(engines)
    assert "ASQ-PHI" in sec and "MACCROBAT" in sec
    for e in inp["deid_not_run"]["method"]:
        assert f"`{e}`" in sec, e


def test_block_says_synthetic_and_not_clinical(md):
    assert "synthetic" in md.lower() and "not clinical performance" in md


def test_update_readme_replaces_only_the_block():
    text = f"intro\n{rr.START}\nold\n{rr.END}\noutro\n"
    assert rr.update_readme(text, "new") == f"intro\n{rr.START}\nnew\n{rr.END}\noutro\n"
