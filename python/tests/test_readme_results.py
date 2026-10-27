"""Results leaderboards (one per capability) are generated from committed results and stay in sync:
a short summary in the README (best system per group) and the full tables in docs/results.md."""

import re

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
    return [r for r in section.splitlines() if r.startswith("| ") and not r.startswith(("| Rank", "| Group", "| Question"))]


def _section(md, title):
    """From a heading to the next heading (### or ####)."""
    return re.split(r"\n#{3,4} ", md.split(title, 1)[1], maxsplit=1)[0]


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
    assert len(summary.splitlines()) <= 70


def _best_by_group(full_rows, group_of):
    best = {}
    for r in full_rows:        # full tables are sorted best first
        name = _cell(r, 2).split("]")[0].strip("[`")
        best.setdefault(group_of(name), name)
    return best


@pytest.mark.parametrize("title, groups, group_of", [(rr.DEID_TITLE, rr.DEID_GROUPS, rr.deid_group)])
def test_summary_shows_the_best_system_of_each_group_and_links_the_full_table(summary, md, title, groups, group_of):
    rows = _rows(_section(summary, title))
    assert sorted(_cell(r, 1) for r in rows) == sorted(groups)
    scores = [int(_cell(r, 3).split(" of ")[0].replace(",", "")) for r in rows]   # fewest leaked first
    assert scores == sorted(scores, reverse=title == rr.PHENOTYPE_TITLE)
    best = _best_by_group(_rows(_section(md, title)), group_of)
    assert set(best) == set(groups)
    plain = rr.plain_system if title == rr.PHENOTYPE_TITLE else rr.plain_tool
    for r in rows:
        assert _cell(r, 2) == plain(best[_cell(r, 1)]), r
        assert not any(c in _cell(r, i) for c in "`_" for i in (1, 2)), r     # no code names in the README
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
    acc = [float(_cell(r, 5).split("**")[1]) for r in rows]   # correct, out of 100
    assert acc == sorted(acc, reverse=True)
    assert _cell(rows[0], 1).startswith("1")


def test_note_model_accuracy_and_ci_match_the_ladder_file(inp, md):
    rows = _rows(_section(md, rr.PHENOTYPE_TITLE))
    for _, r in inp["ladder"].iterrows():
        row = next(x for x in rows if _cell(x, 2) in (f"`{r['method']}`",) or _cell(x, 2).startswith(f"[`{r['method']}`]"))
        assert f"**{100 * r['accuracy']:.1f}** ({100 * r['acc_lo']:.1f}–{100 * r['acc_hi']:.1f})" in row, r["method"]


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
        assert [_cell(row, i) for i in (11, 12, 13, 14)] == [rr._pct(m[k]) for k in ("sensitivity", "specificity", "ppv", "npv")], s


def test_plain_column_names_say_correct_or_incorrect(summary, md):
    for text in (summary, md):
        headers = [line for line in text.splitlines() if line.startswith(("| Rank", "| Group", "| Question"))]
        assert len(headers) == 2
        for h in headers:
            for jargon in ("accuracy", "recall", "precision", "macro", "f1", "false alarm"):
                assert jargon not in h.lower(), (jargon, h)
        ph, de = headers
        for col in ("Correct", "Periodontitis incorrectly assigned", "Periodontitis incorrectly ruled out",
                    "Incorrect stage", "No answer"):
            assert col in ph, col
        assert "Incorrect diagnosis" not in ph
        for h in headers:
            assert not any(w in h for w in ("System", "Tool", "Engine")), h
        for col in (rr.COL_LEAKED, rr.COL_SCRUBBED):
            assert col in de, col
        assert "left in" not in de and "Valid text" not in de


def test_readme_phenotyping_table_is_narrow_and_each_cell_carries_its_total(summary):
    """Eight columns, so it fits a laptop screen; every count says what it is out of ("219 of 240"), the
    yes/no errors carry their specificity and sensitivity, and each row adds up to the charts counted."""
    sec = _section(summary, rr.PHENOTYPE_TITLE)
    lines = sec.splitlines()
    i = next(k for k, x in enumerate(lines) if x.startswith("| Question"))
    cols = [c.strip() for c in lines[i].split("|")[1:-1]]
    assert cols == ["Question", "Method", "Correct", "Periodontitis incorrectly assigned",
                    "Periodontitis incorrectly ruled out", "Incorrect stage", "No answer", "Rank"]
    rows = [[c.strip() for c in x.split("|")[1:-1]] for x in lines[i + 2:] if x.startswith("|")]
    assert rows
    of = re.compile(r"^(\d+) of (\d+)")
    for r in rows:
        right, yes, no, stage, na = (of.match(c) for c in r[2:7])
        assert all((right, yes, no, stage, na)), r
        n = int(right.group(2))
        assert int(yes.group(2)) + int(no.group(2)) == n                      # without + with periodontitis
        assert sum(int(m.group(1)) for m in (right, yes, no, stage, na)) == n, r
        assert "specificity" in r[3] and "sensitivity" in r[4], r
    assert f"adds up to the {n}" in sec


def test_readme_says_method_in_both_tables(summary):
    ph = next(x for x in _section(summary, rr.PHENOTYPE_TITLE).splitlines() if x.startswith("| Question"))
    assert "| Method |" in ph and "Total" not in ph                # totals sit in the cells ("219 of 240")
    de = next(x for x in _section(summary, rr.DEID_TITLE).splitlines() if x.startswith("| Group"))
    assert "| Best method |" in de and "| Methods in group |" in de
    assert "Total" not in de                                   # totals sit in the cells ("115 of 2,714")


def test_readme_explains_the_questions_and_columns_as_lists(summary):
    ph = _section(summary, rr.PHENOTYPE_TITLE)
    numbered = [x for x in ph.splitlines() if re.match(r"[123]\. \*\*", x)]
    assert len(numbered) == 3
    bullets = [x for x in ph.splitlines() if x.startswith("- **")]
    for term in ("Correct", "Periodontitis incorrectly assigned", "Specificity", "Periodontitis incorrectly ruled out",
                 "Sensitivity", "Incorrect stage", "No answer (evidence not available)", "Rank", "Stage 4 rule"):
        assert sum(x.startswith(f"- **{term}**") for x in bullets) == 1, term
    de = _section(summary, rr.DEID_TITLE)
    for term in (rr.COL_LEAKED, rr.COL_SCRUBBED, "Rank"):
        assert sum(x.startswith(f"- **{term}**") for x in de.splitlines()) == 1, term
    # no definition left inline in a paragraph
    for sec in (ph, de):
        for x in sec.splitlines():
            if not x.startswith(("- **", "|")):
                assert "**Correct**" not in x and f"**{rr.COL_LEAKED}**" not in x, x


def test_full_page_explains_columns_as_lists(md):
    ph = _section(md, rr.PHENOTYPE_TITLE)
    for term in ("Correct", "Incorrect stage", "Unsafe errors", "Stage 4 correct", "Easy / medium / hard"):
        assert sum(x.startswith(f"- **{term}**") for x in ph.splitlines()) == 1, term
    de = md.split(rr.DEID_TITLE, 1)[1]
    assert sum(x.startswith(f"- **{rr.COL_LEAKED}**") for x in de.splitlines()) >= 1
