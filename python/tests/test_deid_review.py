"""Label Studio review flows for de-identification (spec 008): gold annotation and QA."""

import pandas as pd
import pytest

from dental_omop_nlp import deid, deid_review
from dental_omop_nlp.phi_challenge import CATEGORIES, build_challenge

NOTE = "Pt Ann Lee seen 3/4/2021, call 555-123-4567."


def _rec(note_id="n1", text=NOTE, phi=None):
    phi = phi if phi is not None else [
        {"start": 3, "end": 10, "text": "Ann Lee", "type": "PATIENT"},
        {"start": 16, "end": 24, "text": "3/4/2021", "type": "DATE"},
        {"start": 31, "end": 43, "text": "555-123-4567", "type": "PHONE"}]
    return {"note_id": note_id, "tier": "easy", "text": text, "phi": phi, "decoys": []}


def _ann(note_id, who, spans, aided=True):
    """A Label Studio export task with one annotation of (start, end, label) spans."""
    res = [{"from_name": "phi", "to_name": "text", "type": "labels",
            "value": {"start": s, "end": e, "text": NOTE[s:e], "labels": [lab]}} for s, e, lab in spans]
    return {"data": {"note_id": note_id, "text": NOTE, "aided": aided},
            "annotations": [{"completed_by": {"email": who}, "result": res}]}


# ------------------------------------------------------------------ gold flow
def test_gold_tasks_carry_engine_spans_as_predictions_with_mapped_labels():
    detect = lambda t: [{"start": 3, "end": 10, "type": "NAME"}, {"start": 16, "end": 24, "type": "DATE"}]
    t = deid_review.gold_tasks([_rec()], detect, "regex_v2", unaided_share=0.0)[0]
    assert t["data"] == {"note_id": "n1", "tier": "easy", "text": NOTE, "aided": True}
    (pred,) = t["predictions"]
    assert pred["model_version"] == "regex_v2"
    vals = [r["value"] for r in pred["result"]]
    assert [v["labels"] for v in vals] == [["PHI_UNSPECIFIED"], ["DATE"]]   # NAME names no category
    assert vals[0]["text"] == "Ann Lee" and all(r["from_name"] == "phi" for r in pred["result"])


def test_gold_tasks_leave_a_seeded_share_unaided():
    recs = [_rec(f"n{i}") for i in range(50)]
    a = deid_review.gold_tasks(recs, lambda t: [], "e", unaided_share=0.2, seed=3)
    b = deid_review.gold_tasks(recs, lambda t: [], "e", unaided_share=0.2, seed=3)
    unaided = [t for t in a if not t["data"]["aided"]]
    assert len(unaided) == 10 and all("predictions" not in t for t in unaided)
    assert a == b


def test_every_category_is_a_gold_label():
    assert set(CATEGORIES) <= set(deid_review.GOLD_LABELS)


def test_parse_gold_export_and_agreement():
    exp = [_ann("n1", "a@x", [(3, 10, "PATIENT"), (16, 24, "DATE")]),
           _ann("n1", "b@x", [(3, 10, "DOCTOR"), (16, 24, "DATE"), (31, 43, "PHONE")])]
    spans = deid_review.parse_gold_export(exp)
    assert len(spans) == 5 and set(spans["annotator"]) == {"a@x", "b@x"}
    ag = deid_review.agreement(spans).iloc[0]
    assert ag["n_notes"] == 1
    assert ag["f1_span"] == pytest.approx(2 * 2 / (2 + 3))       # 2 shared spans of 2 and 3
    assert ag["f1_typed"] == pytest.approx(2 * 1 / (2 + 3))      # only DATE agrees on category


def test_consensus_keeps_characters_at_least_half_the_annotators_marked():
    exp = [_ann("n1", "a", [(3, 10, "PATIENT"), (31, 43, "PHONE")]),
           _ann("n1", "b", [(3, 10, "PATIENT")]),
           _ann("n1", "c", [(3, 6, "DOCTOR"), (16, 24, "DATE")])]
    gold = deid_review.consensus(deid_review.parse_gold_export(exp))
    assert [(s["start"], s["end"], s["type"]) for s in gold["n1"]] == [(3, 10, "PATIENT")]


def test_annotator_recall_against_the_generator_split_by_aided():
    exp = [_ann("n1", "a", [(3, 10, "PATIENT"), (16, 24, "DATE")], aided=True),
           _ann("n2", "a", [(3, 10, "PATIENT")], aided=False)]
    r = deid_review.annotator_recall(deid_review.parse_gold_export(exp), [_rec("n1"), _rec("n2")])
    r = r.set_index(["annotator", "aided"])["entity_recall"]
    assert r[("a", True)] == pytest.approx(2 / 3) and r[("a", False)] == pytest.approx(1 / 3)


# ------------------------------------------------------------------ QA flow
def test_redact_map_tracks_where_kept_characters_land():
    red, pos = deid_review.redact_map("ab CD ef", [{"start": 3, "end": 5, "type": "X"}])
    assert red == "ab [X] ef"
    assert pos[0] == 0 and pos[3] == -1 and pos[6] == 7 and red[pos[7]] == "f"


def test_qa_tasks_show_only_redacted_text_and_key_the_true_leaks():
    detect = lambda t: [{"start": 3, "end": 10, "type": "NAME"}]          # misses the date and phone
    tasks, key = deid_review.qa_tasks([_rec()], detect, "e", n=1, seed=0)
    (t,) = tasks
    assert "Ann Lee" not in t["data"]["text"] and "555-123-4567" in t["data"]["text"]
    assert "phi" not in t["data"] and "n_true_leaks" not in t["data"]           # the key stays out of the task
    assert key.set_index("note_id").loc["n1", "n_true_leaks"] == 2


def test_qa_sample_takes_every_flagged_note_first_then_a_seeded_sample():
    recs = [_rec(f"n{i}") for i in range(30)]
    detect = lambda t: deid.detect_regex_v2(t)
    tasks, key = deid_review.qa_tasks(recs, lambda t: [], "none", n=5, seed=1)   # nothing removed: all flagged
    assert len(tasks) == 5 and key["residual_flag"].all()
    t2, _ = deid_review.qa_tasks(recs, detect, "regex_v2", n=5, seed=1)
    t3, _ = deid_review.qa_tasks(recs, detect, "regex_v2", n=5, seed=1)
    assert t2 == t3


def test_wilson_interval():
    p, lo, hi = deid_review.wilson(0, 100)
    assert p == 0 and lo == 0 and hi == pytest.approx(0.0370, abs=1e-4)
    p, lo, hi = deid_review.wilson(5, 50)
    assert p == pytest.approx(0.1) and lo == pytest.approx(0.0435, abs=1e-4) and hi == pytest.approx(0.2136, abs=1e-4)


def test_qa_summary_pools_reviewers_and_scores_them_against_the_key():
    labels = pd.DataFrame({"note_id": ["n1", "n1", "n2", "n2", "n3", "n3"],
                           "reviewer": ["r1", "r2"] * 3,
                           "leak": ["yes", "no", "no", "no", "yes", "yes"],
                           "over_redaction": ["no"] * 5 + ["yes"]})
    key = pd.DataFrame({"note_id": ["n1", "n2", "n3"], "n_true_leaks": [1, 0, 0]})
    s = deid_review.qa_summary(labels, key).set_index("scope")
    assert s.loc["pooled", "n_notes"] == 3 and s.loc["pooled", "leak_notes"] == 2      # any reviewer
    assert s.loc["r2", "leak_notes"] == 1
    assert s.loc["r1", "sensitivity"] == 1.0 and s.loc["r2", "sensitivity"] == 0.0
    assert s.loc["r1", "specificity"] == pytest.approx(0.5)
    assert s.loc["pooled", "over_redaction_rate"] == pytest.approx(1 / 3)


def test_parse_qa_export():
    exp = [{"data": {"note_id": "n1", "text": "x"}, "annotations": [{"completed_by": 7, "result": [
        {"from_name": "leak", "type": "choices", "value": {"choices": ["yes"]}},
        {"from_name": "over_redaction", "type": "choices", "value": {"choices": ["no"]}},
        {"from_name": "leaks", "to_name": "text", "type": "labels",
         "value": {"start": 0, "end": 1, "text": "x", "labels": ["LEAK"]}}]}]}]
    lab = deid_review.parse_qa_export(exp).iloc[0]
    assert (lab["note_id"], lab["reviewer"], lab["leak"], lab["over_redaction"], lab["n_leak_spans"]) == \
        ("n1", "7", "yes", "no", 1)


# ------------------------------------------------------------------ dry run
def test_simulated_exports_are_seeded_and_parse_back():
    recs = build_challenge(40, seed=7)
    detect = deid.get_engine("regex_v2+guard")
    gt = deid_review.gold_tasks(recs, detect, "regex_v2+guard", seed=0)
    a = deid_review.simulate_gold_export(gt, recs, n_annotators=3, seed=11)
    assert a == deid_review.simulate_gold_export(gt, recs, n_annotators=3, seed=11)
    spans = deid_review.parse_gold_export(a)
    assert spans["annotator"].nunique() == 3
    rec = deid_review.annotator_recall(spans, recs)
    assert rec["entity_recall"].between(0.5, 1.0).all()
    qt, key = deid_review.qa_tasks(recs, detect, "regex_v2+guard", n=20, seed=0)
    q = deid_review.parse_qa_export(deid_review.simulate_qa_export(qt, key, n_reviewers=2, seed=13))
    assert len(q) == 40 and set(q["leak"]) <= {"yes", "no"}


def test_label_studio_configs_match_the_parser():
    import xml.etree.ElementTree as ET

    from dental_omop_nlp.paths import REPO_ROOT
    gold = ET.parse(REPO_ROOT / "labelstudio" / "deid_gold.xml").getroot()
    labels = gold.find("Labels")
    assert (labels.get("name"), labels.get("toName")) == ("phi", "text")
    assert [x.get("value") for x in labels] == deid_review.GOLD_LABELS
    qa = ET.parse(REPO_ROOT / "labelstudio" / "deid_qa.xml").getroot()
    assert {c.get("name") for c in qa.iter("Choices")} == {"leak", "over_redaction"}
    assert qa.find("Labels").get("name") == "leaks"
    assert {c.get("value") for c in qa.iter("Choice")} == {"yes", "no"}


def test_qa_summary_leak_span_recall():
    labels = pd.DataFrame({"note_id": ["n1", "n1"], "reviewer": ["r1", "r2"], "leak": ["yes", "yes"],
                           "over_redaction": ["no", "no"],
                           "leak_spans": [[(0, 3)], [(10, 12)]]})
    key = pd.DataFrame({"note_id": ["n1"], "n_true_leaks": [3],
                        "leak_spans": [[{"start": 0, "end": 3}, {"start": 9, "end": 12}, {"start": 20, "end": 25}]]})
    s = deid_review.qa_summary(labels, key).set_index("scope")["leak_span_recall"]
    assert s["r1"] == pytest.approx(1 / 3) and s["r2"] == pytest.approx(1 / 3)
    assert s["pooled"] == pytest.approx(2 / 3)                    # union of what the reviewers marked


def test_consensus_counts_annotators_not_spans():
    exp = [_ann("n1", "a", [(0, 5, "PATIENT"), (0, 5, "PATIENT")]), _ann("n1", "b", []), _ann("n1", "c", [])]
    assert deid_review.consensus(deid_review.parse_gold_export(exp))["n1"] == []   # 1 of 3 is under half


def test_true_leaks_are_surviving_runs_without_tags_or_bare_titles():
    text = "Seen by Dr. Ann O'Neil today; also Dr. Bo on 3/4."
    phi = [{"start": 8, "end": 22, "text": "Dr. Ann O'Neil", "type": "DOCTOR"},
           {"start": 35, "end": 41, "text": "Dr. Bo", "type": "DOCTOR"}]
    detect = lambda t: [{"start": 12, "end": 15, "type": "NAME"}, {"start": 39, "end": 41, "type": "NAME"}]
    tasks, key = deid_review.qa_tasks([_rec(text=text, phi=phi)], detect, "e", n=1)
    red = tasks[0]["data"]["text"]
    leaks = [red[s["start"]:s["end"]] for s in key.iloc[0]["leak_spans"]]
    assert leaks == ["O'Neil"]                       # "Dr." alone is no leak; the tag is never inside one


def test_leak_spans_round_trip_as_text():
    assert deid_review.format_spans([(0, 3), (9, 12)]) == "0-3;9-12"
    assert deid_review.parse_spans("0-3;9-12") == [(0, 3), (9, 12)] and deid_review.parse_spans("") == []
