"""Results leaderboards (one per capability) are generated from committed results and stay in sync:
a short summary in the README (best system per group) and the full tables in docs/results.md."""

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
    """The full tables (docs/results.md)."""
    return rr.details_markdown(inp)


@pytest.fixture(scope="module")
def summary(inp):
    """The README block."""
    return rr.results_markdown(inp)


def _rows(section):
    return [r for r in section.splitlines() if r.startswith("| ") and not r.startswith(("| Rank", "| Group"))]


def _section(md, title):
    return md.split(title, 1)[1].split("\n### ", 1)[0]


def _cell(row, i):
    return row.split("|")[i].strip()


def test_readme_and_results_page_match_the_committed_results(summary, md):
    readme = (REPO_ROOT / "README.md").read_text()
    assert readme.count(rr.START) == 1 and readme.count(rr.END) == 1
    stale = "results are stale: run python scripts/35_readme_results.py"
    assert rr.update_readme(readme, summary) == readme, stale
    assert rr.RESULTS_DOC.read_text() == md, stale


def test_one_leaderboard_per_capability_and_no_overall_rank(summary, md):
    for text in (summary, md):
        assert [line for line in text.splitlines() if line.startswith("### ")] == [rr.PHENOTYPE_TITLE, rr.DEID_TITLE]
        assert "overall" not in text.lower()


def test_readme_summary_is_short(summary):
    assert len(summary.splitlines()) <= 30


def _best_by_group(full_rows, group_of):
    best = {}
    for r in full_rows:        # full tables are sorted best first
        name = _cell(r, 2).split("]")[0].strip("[`")
        best.setdefault(group_of(name), name)
    return best


@pytest.mark.parametrize("title, groups, group_of", [
    (rr.PHENOTYPE_TITLE, rr.PHENOTYPE_GROUPS, rr.phenotype_group),
    (rr.DEID_TITLE, rr.DEID_GROUPS, rr.deid_group)])
def test_summary_shows_the_best_system_of_each_group_and_links_the_full_table(summary, md, title, groups, group_of):
    rows = _rows(_section(summary, title))
    assert sorted(_cell(r, 1) for r in rows) == sorted(groups)
    scores = [float(_cell(r, 3).split("**")[1].rstrip("%")) for r in rows]
    assert scores == sorted(scores, reverse=True)
    best = _best_by_group(_rows(_section(md, title)), group_of)
    assert set(best) == set(groups)
    for r in rows:
        assert f"`{best[_cell(r, 1)]}`" in _cell(r, 2), r
    link = f"docs/results.md#{rr.anchor(title)}"
    assert link in _section(summary, title)
    assert f"\n{title}\n" in "\n" + md


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
    acc = [float(_cell(r, 5).split("**")[1].rstrip("%")) for r in rows]   # exact status right
    assert acc == sorted(acc, reverse=True)
    assert _cell(rows[0], 1).startswith("1")


def test_note_model_accuracy_and_ci_match_the_ladder_file(inp, md):
    rows = _rows(_section(md, rr.PHENOTYPE_TITLE))
    for _, r in inp["ladder"].iterrows():
        row = next(x for x in rows if _cell(x, 2) in (f"`{r['method']}`",) or _cell(x, 2).startswith(f"[`{r['method']}`]"))
        assert f"**{r['accuracy']:.1%}** ({r['acc_lo']:.1%}–{r['acc_hi']:.1%})" in row, r["method"]


def test_periodontitis_yes_no_columns_match_the_shared_scorer(inp, md):
    import sys
    sys.path.insert(0, str(REPO_ROOT / "eval"))
    from score import score
    rows = _rows(_section(md, rr.PHENOTYPE_TITLE))
    for s in ("note_rules", "medgemma-1.5-4b-it", "algorithm_v0", "exam_form"):
        pred = inp["preds"][s] if s in inp["preds"] else inp["key"].reindex(inp["preds"].index)[s]
        res = score(inp["preds"]["truth"], pred.where(pred.isin(rr.LABELS)).fillna("none"), None, s)
        m = res[res["class"] == ""].set_index("metric")["value"]
        row = next(r for r in rows if _cell(r, 2) == f"`{s}`" or _cell(r, 2).startswith(f"[`{s}`]"))
        assert [_cell(row, i) for i in (6, 7, 8, 9)] == [rr._pct(m[k]) for k in ("sensitivity", "specificity", "ppv", "npv")], s


def test_plain_column_names_and_a_key_for_false_alarms(summary, md):
    for text in (summary, md):
        headers = [line.lower() for line in text.splitlines() if line.startswith(("| Rank", "| Group"))]
        assert len(headers) == 2
        for h in headers:
            for jargon in ("accuracy", "recall", "precision", "macro", "f1"):
                assert jargon not in h, (jargon, h)
        for title in (rr.PHENOTYPE_TITLE, rr.DEID_TITLE):
            sec = _section(text, title)
            assert "missed" in sec and "false alarm" in sec, title


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
