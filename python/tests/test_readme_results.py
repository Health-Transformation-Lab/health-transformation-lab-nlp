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
    assert len(summary.splitlines()) <= 40


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
    scores = [int(_cell(r, 3)) for r in rows]   # correct (higher first), or PHI left in (lower first)
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
        for col in ("Correct", rr.COL_ASSIGNED, rr.COL_NOT_ASSIGNED, "Incorrect stage", rr.COL_NO_ANSWER):
            assert col in ph, col
        assert "Incorrect diagnosis" not in ph
        for h in headers:
            assert not any(w in h for w in ("System", "Tool", "Engine")), h
        for col in (rr.COL_LEAKED, rr.COL_SCRUBBED):
            assert col in de, col
        assert "left in" not in de and "Valid text" not in de


def test_sensitivity_and_specificity_sit_next_to_the_counts_they_summarise(summary):
    header = next(x for x in _section(summary, rr.PHENOTYPE_TITLE).splitlines() if x.startswith("| Question"))
    cols = [c.strip() for c in header.split("|")]
    assert cols[4:8] == [rr.COL_ASSIGNED, "Specificity", rr.COL_NOT_ASSIGNED, "Sensitivity"]


def test_readme_says_method_in_both_tables(summary):
    ph = next(x for x in _section(summary, rr.PHENOTYPE_TITLE).splitlines() if x.startswith("| Question"))
    assert "| Method |" in ph and "| Total charts |" in ph
    de = next(x for x in _section(summary, rr.DEID_TITLE).splitlines() if x.startswith("| Group"))
    assert "| Best method |" in de and "| Methods in group |" in de and "| Total " in de


def test_dental_word_count_matches_the_scored_challenge_set(inp):
    allt = inp["deid"].query("tier == 'all'")
    damaged = allt["decoy_damage"] * inp["n_decoys"]
    assert (damaged - damaged.round()).abs().max() < 1e-9     # the scored set: every rate is k / n_decoys


def _other_sets_rows(summary):
    sec = _section(summary, rr.OTHER_SETS_TITLE)
    return [r for r in sec.splitlines() if r.startswith("| ") and not r.startswith("| Note set")]


def test_readme_has_one_row_per_other_note_set_linking_to_its_table(inp, summary):
    rows = _other_sets_rows(summary)
    d, mac, clin = inp["deid"], inp["maccrobat"].set_index("method"), inp["maccrobat_clinical"]

    def of(k, n):
        return f"{round(k):,} of {int(n):,}"
    assert len(rows) == 4                                  # John Snow Labs, ASQ-PHI, MACCROBAT, Michigan course
    for key in ("jsl48", "external", "maccrobat"):
        t = mac if key == "maccrobat" else d[d.tier == key].set_index("method")
        best = t.sort_values("entity_recall", ascending=False, kind="stable").index[0]
        row = next(r for r in rows if f"docs/results.md#{rr.anchor(rr.DEID_SETS[key])}" in r)
        assert _cell(row, 2) == rr.plain_tool(best), key
        assert _cell(row, 3) == of(t.loc[best, "n_phi"] * (1 - t.loc[best, "entity_recall"]), t.loc[best, "n_phi"])
    for r in rows:                                         # every row drills down
        assert "docs/results.md#" in _cell(r, 5), r
    course = next(r for r in rows if "Michigan" in _cell(r, 1))
    c = inp["course"]
    assert f"{c['missed']} of {c['total']}" in _cell(course, 3)


def test_course_tagger_counts(inp, md):
    c = inp["course"]
    assert c["total"] == 195 and c["tag"] == "course_lr5e-5_e3"          # chosen on validation
    assert (c["missed"], c["wrong_tags"]) == (33, 45)
    assert c["found"] == c["total"] - c["missed"]
    sec = _section(md, rr.COURSE_TITLE)
    assert "University of Michigan" in sec and "162" in sec and "195" in sec


def test_readme_mentions_the_course_files(summary):
    assert "University of Michigan course files" in _section(summary, rr.OTHER_SETS_TITLE)


def test_readme_other_sets_table_is_narrow(summary):
    header = next(x for x in _section(summary, rr.OTHER_SETS_TITLE).splitlines() if x.startswith("| Note set"))
    assert header.count("|") - 1 == 5


def test_full_page_has_one_table_per_note_set_in_x_of_n(inp, md):
    d, mac, clin = inp["deid"], inp["maccrobat"].set_index("method"), inp["maccrobat_clinical"]

    def of(k, n):
        return f"{round(k):,} of {int(n):,}"
    for key, title in rr.DEID_SETS.items():
        sec = _section(md, title)
        header = next(x for x in sec.splitlines() if x.startswith("| Code name"))
        assert rr.COL_LEAKED in header and rr.COL_SCRUBBED in header, title
        rows = {_cell(r, 1).strip("`"): r for r in sec.splitlines()
                if r.startswith("| `")}
        t = mac if key == "maccrobat" else d[d.tier == key].set_index("method")
        assert set(rows) == set(t.index), title
        for m, r in rows.items():
            assert _cell(r, 2) == rr.plain_tool(m)
            assert _cell(r, 3) == of(t.loc[m, "n_phi"] * (1 - t.loc[m, "entity_recall"]), t.loc[m, "n_phi"]), (title, m)
            want = {"unseen": lambda: of(inp["n_decoys_by_tier"]["unseen"] * t.loc[m, "decoy_damage"],
                                         inp["n_decoys_by_tier"]["unseen"]),
                    "jsl48": lambda: "not labelled",
                    "external": lambda: of(t.loc[m, "n_hard_negatives"] * t.loc[m, "hard_negative_damage"],
                                           t.loc[m, "n_hard_negatives"]),
                    "maccrobat": lambda: of(clin.loc[m, "n_touched"], clin.loc[m, "n"])}[key]()
            assert _cell(r, 4) == want, (title, m)


def test_maccrobat_table_says_which_methods_were_not_recorded_and_why(inp, md):
    sec = _section(md, rr.DEID_SETS["maccrobat"])
    for _, r in inp["maccrobat_not_run"].iterrows():
        assert f"`{r['method']}`" in sec and r["reason"] in sec, r["method"]


def test_full_synthetic_table_is_counts_with_the_95_range(inp, md):
    allt = inp["deid"].query("tier == 'all'").set_index("method")
    for r in _rows(_section(md, rr.DEID_TITLE)):
        m = _cell(r, 2).strip("`")
        n, k = int(allt.loc[m, "n_phi"]), round(allt.loc[m, "n_phi"] * (1 - allt.loc[m, "entity_recall"]))
        assert _cell(r, 4).startswith(f"{k:,} of {n:,} (95% range "), r
        assert _cell(r, 3) == rr.plain_tool(m)
        assert _cell(r, 5) == f"{round(inp['n_decoys'] * allt.loc[m, 'decoy_damage']):,} of {inp['n_decoys']:,}"


def test_breakdown_buckets():
    truth = pd.Series(["periodontitis_stage_2", "periodontitis_stage_2", "healthy", "periodontitis_stage_3",
                       "gingivitis", "healthy"])
    pred = pd.Series(["periodontitis_stage_2", "healthy", "periodontitis_stage_1", "periodontitis_stage_4",
                      "healthy", None])
    b = rr.breakdown(truth, pred)
    assert b == pytest.approx({"correct": 1 / 6, "dx_said_no": 1 / 6, "dx_said_yes": 1 / 6,
                               "stage": 2 / 6, "no_answer": 1 / 6})


def test_out_of_100_adds_to_100():
    assert rr.out_of_100([0.912, 0.004, 0.017, 0.067]) == [91, 0, 2, 7]
    assert sum(rr.out_of_100([1 / 3, 1 / 3, 1 / 3])) == 100


def test_readme_phenotype_table_answers_three_questions(inp, summary):
    rows = _rows(_section(summary, rr.PHENOTYPE_TITLE))
    picks = rr.readme_phenotype_rows(inp)
    assert len(rows) == len(picks)
    questions = [q for q, _ in picks]
    assert list(dict.fromkeys(questions)) == list(rr.PHENOTYPE_QUESTIONS)
    systems = [s for _, s in picks]
    assert systems[0] == "algorithm_v0"                              # whole record: the best rule phenotype
    assert "note_rules" in systems                                    # the simple baseline is always shown
    assert any(s.startswith("medgemma") for s in systems)
    assert systems[questions.index(rr.PHENOTYPE_QUESTIONS[2])] == "probing_chart"
    shown = [_cell(r, 1) for r in rows]                               # question named once, on its first row
    assert [q for q in shown if q] == list(rr.PHENOTYPE_QUESTIONS)
    preds, key = inp["preds"], inp["key"].reindex(inp["preds"].index)
    for r, s in zip(rows, systems):
        assert _cell(r, 2) == rr.readme_label(s)
        nums = [int(_cell(r, i)) for i in (3, 4, 6, 8, 9)]
        total = int(_cell(r, 10))
        assert total == len(preds) == 240 and sum(nums) == total, r
        pred = preds[s] if s in preds else key[s]
        b = rr.breakdown(preds["truth"], pred.where(pred.isin(rr.LABELS)))
        assert nums == [round(total * b[k]) for k in ("correct", "dx_said_yes", "dx_said_no", "stage", "no_answer")]
        yn = rr.yes_no(preds["truth"], pred.where(pred.isin(rr.LABELS)))
        assert (_cell(r, 5), _cell(r, 7)) == (rr._pct(yn["specificity"]), rr._pct(yn["sensitivity"])), r


def test_plain_names():
    assert rr.plain_system("algorithm_v0") == "Gum measurements first"
    assert rr.plain_system("modernbert-base+cw+s2+rules4") == "ModernBERT"
    assert rr.plain_system("fusion_tfidf_rad+rules4") == "Word counts + X-ray reading"
    assert rr.plain_system("probing_chart") == "Gum measurements (probing chart)"
    assert rr.plain_system("medgemma-1.5-4b-it+rules4") == "MedGemma 1.5 4B"
    assert rr.plain_system("medgemma-27b-text-it") == "MedGemma 27B text"


def test_readme_names_the_medgemma_version_that_ran(summary):
    rows = [r for r in _rows(_section(summary, rr.PHENOTYPE_TITLE)) if "MedGemma" in r]
    assert rows and all("MedGemma 1.5 4B" in _cell(r, 2) for r in rows)
    assert rr.plain_tool("hf_stanford+hf_obi+regex_v2+guard") == "Stanford AI + OBI AI + patterns + dental-word guard"
    assert rr.plain_tool("regex_v2") == "Patterns"


def test_every_system_and_tool_has_a_plain_name(inp):
    for s in [*inp["ladder"]["method"], *rr.PHENOTYPES, *rr.EVIDENCE]:
        assert rr.plain_system(s) and "_" not in rr.plain_system(s), s
    for m in inp["deid"]["method"].unique():
        assert rr.plain_tool(m) and "_" not in rr.plain_tool(m), m


def test_periodontitis_column_names():
    assert rr.COL_ASSIGNED == "Periodontitis incorrectly assigned (when not present)"
    assert rr.COL_NOT_ASSIGNED == "Periodontitis incorrectly ruled out (when present)"
    assert rr.COL_NO_ANSWER == "No answer (evidence not available)"


def test_full_table_uses_the_same_two_column_names(md):
    header = next(line for line in _section(md, rr.PHENOTYPE_TITLE).splitlines() if line.startswith("| Rank"))
    cols = [c.strip() for c in header.split("|")]
    assert cols[6:8] == [rr.COL_ASSIGNED, rr.COL_NOT_ASSIGNED]


def test_readme_deid_rows_are_counts_with_their_totals(inp, summary, md):
    allt = inp["deid"].query("tier == 'all'").set_index("method")
    best = _best_by_group(_rows(_section(md, rr.DEID_TITLE)), rr.deid_group)
    for r in _rows(_section(summary, rr.DEID_TITLE)):
        m = best[_cell(r, 1)]
        n_phi, n_words = int(allt.loc[m, "n_phi"]), inp["n_decoys"]
        assert int(_cell(r, 3)) == round(n_phi * (1 - allt.loc[m, "entity_recall"])) and _cell(r, 4) == f"{n_phi:,}"
        assert int(_cell(r, 5)) == round(n_words * allt.loc[m, "decoy_damage"]) and _cell(r, 6) == f"{n_words:,}"


def test_difficulty_levels_match_the_medgemma_comparison(inp, md):
    rows = _rows(_section(md, rr.PHENOTYPE_TITLE))
    lv = inp["by_diff"].pivot(index="method", columns="difficulty", values="accuracy")
    for m in lv.index:
        row = next(x for x in rows if _cell(x, 2).startswith(f"[`{m}`]") or _cell(x, 2) == f"`{m}`")
        assert " / ".join(f"{100 * lv.loc[m, k]:.0f}" for k in ("L1", "L2", "L3")) in row, m
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
    rest = md.split(rr.DEID_TITLE, 1)[1]
    assert "ASQ-PHI" in rest and "MACCROBAT" in rest
    for e in inp["deid_not_run"]["method"]:
        assert f"`{e}`" in sec, e


def test_block_says_synthetic_and_not_clinical(md):
    assert "synthetic" in md.lower() and "not clinical performance" in md


def test_update_readme_replaces_only_the_block():
    text = f"intro\n{rr.START}\nold\n{rr.END}\noutro\n"
    assert rr.update_readme(text, "new") == f"intro\n{rr.START}\nnew\n{rr.END}\noutro\n"
