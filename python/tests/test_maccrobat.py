"""Spec 009: a de-identification test pass on MACCROBAT (original brat files and BIO labels). Fixtures are invented sentences."""

import json

from dental_omop_nlp import deid_eval, maccrobat


def _doc(pairs):
    """[(token, tag), ...] -> (tokens, tags)."""
    return [t for t, _ in pairs], [g for _, g in pairs]


DOC = _doc([("A", "O"), ("71", "B-Age"), ("-", "I-Age"), ("year", "I-Age"), ("-", "I-Age"), ("old", "I-Age"),
            ("man", "B-Sex"), ("had", "O"), ("fever", "B-Sign_symptom"), ("in", "O"), ("March", "B-Date"),
            ("2015", "I-Date"), (".", "O"), ("\n", "O"), ("Aspirin", "B-Medication"), ("81", "B-Dosage"),
            ("mg", "I-Dosage"), ("(", "O"), ("daily", "B-Frequency"), (")", "O"), ("was", "O"),
            ("started", "O"), ("3", "B-Date"), ("days", "I-Date"), ("later", "I-Date"), (".", "O")])


# ---------------------------------------------------------------- US1 BIO -> spans
def test_bio_spans_rebuild_text_and_match_every_slice():
    text, spans = maccrobat.bio_spans(*DOC)
    assert text == "A 71-year-old man had fever in March 2015.\nAspirin 81 mg (daily) was started 3 days later."
    assert [(s["type"], s["text"]) for s in spans] == [
        ("Age", "71-year-old"), ("Sex", "man"), ("Sign_symptom", "fever"), ("Date", "March 2015"),
        ("Medication", "Aspirin"), ("Dosage", "81 mg"), ("Frequency", "daily"), ("Date", "3 days later")]
    for s in spans:
        assert text[s["start"]:s["end"]] == s["text"]


def test_stray_inside_tag_starts_a_new_entity():
    _, spans = maccrobat.bio_spans(["chest", "pain", "and", "rash"],
                                      ["I-Sign_symptom", "I-Sign_symptom", "O", "I-Disease_disorder"])
    assert [(s["type"], s["text"]) for s in spans] == [("Sign_symptom", "chest pain"), ("Disease_disorder", "rash")]
    _, spans = maccrobat.bio_spans(["left", "knee"], ["B-Biological_structure", "I-Sign_symptom"])
    assert [s["text"] for s in spans] == ["left", "knee"]


# ---------------------------------------------------------------- US2 roles and records
def test_role_follows_safe_harbor_for_dates_and_ages():
    assert maccrobat.role("Date", "March 2015") == "phi"
    assert maccrobat.role("Date", "12/03/2014") == "phi"
    assert maccrobat.role("Date", "on 4 Sept") == "phi"
    assert maccrobat.role("Date", "2012") == "other"            # a year alone is allowed
    assert maccrobat.role("Date", "3 days later") == "other"
    assert maccrobat.role("Date", "may have") == "other"       # "may" the verb is not a month
    assert maccrobat.role("Date", "previous decade") == "other"  # "dec" inside a word is not December
    assert maccrobat.role("Date", "end of May") == "phi"
    assert maccrobat.role("Age", "93-year-old") == "phi"
    assert maccrobat.role("Age", "71-year-old") == "other"
    assert maccrobat.role("Sign_symptom", "fever") == "clinical"
    assert maccrobat.role("Nonbiological_location", "emergency department") == "other"


def test_load_bio_builds_challenge_records_and_drops_duplicate_copies(tmp_path):
    other = _doc([("Cough", "B-Sign_symptom"), ("began", "O"), ("in", "O"), ("2019", "B-Date"), (".", "O")])
    changed = (DOC[0], [g if g != "B-Frequency" else "O" for g in DOC[1]])  # a later copy, one tag dropped
    p = tmp_path / "bio.jsonl"
    p.write_text("".join(json.dumps({"tokens": t, "tags": g}) + "\n" for t, g in (DOC, other, changed)))
    recs = maccrobat.load_bio(p)
    assert len(recs) == 2 and {r["tier"] for r in recs} == {"maccrobat"}
    r = next(r for r in recs if r["text"].startswith("A 71"))
    assert [s["text"] for s in r["phi"]] == ["March 2015"]
    assert [s["text"] for s in r["decoys"]] == ["fever", "Aspirin", "81 mg"]
    assert "daily" not in [s["text"] for s in r["entities"]]            # the later copy won
    assert {s["role"] for s in r["entities"]} == {"phi", "clinical", "other"}
    assert next(r for r in recs if r["text"].startswith("Cough"))["phi"] == []


def test_phi_span_is_trimmed_to_the_date_itself(tmp_path):
    tokens, tags = _doc([("Seen", "O"), ("in", "B-Date"), ("October", "I-Date"), ("2014", "I-Date"), (".", "O")])
    p = tmp_path / "bio.jsonl"
    p.write_text(json.dumps({"tokens": tokens, "tags": tags}) + "\n")
    r = maccrobat.load_bio(p)[0]
    assert [s["text"] for s in r["phi"]] == ["October 2014"]
    assert r["text"][r["phi"][0]["start"]:r["phi"][0]["end"]] == "October 2014"
    assert [s["text"] for s in r["entities"]] == ["in October 2014"]     # the label itself is kept as is


# ---------------------------------------------------------------- US3 scores
def _redact_words(*words):
    def detect(text):
        out = []
        for w in words:
            i = text.find(w)
            if i >= 0:
                out.append({"start": i, "end": i + len(w), "type": "X"})
        return out
    return detect


def test_existing_scorer_reads_recall_on_dates_and_damage_on_clinical_text(tmp_path):
    p = tmp_path / "bio.jsonl"
    p.write_text(json.dumps({"tokens": DOC[0], "tags": DOC[1]}) + "\n")
    recs = maccrobat.load_bio(p)
    s = deid_eval.score_records(recs, _redact_words("March 2015", "Aspirin"))["summary"].set_index("tier")
    assert s.loc["maccrobat", "entity_recall"] == 1.0
    assert abs(s.loc["maccrobat", "decoy_damage"] - 1 / 3) < 1e-12


def test_damage_by_type_counts_entities_touched_per_type(tmp_path):
    p = tmp_path / "bio.jsonl"
    p.write_text(json.dumps({"tokens": DOC[0], "tags": DOC[1]}) + "\n")
    recs = maccrobat.load_bio(p)
    t = deid_eval.damage_by_type(recs, _redact_words("71", "Aspirin", "days")).set_index(["role", "type"])
    assert t.loc[("clinical", "Medication"), "n"] == 1 and t.loc[("clinical", "Medication"), "touched"] == 1.0
    assert t.loc[("phi", "Date"), "touched"] == 0.0 and t.loc[("other", "Date"), "touched"] == 1.0
    assert t.loc[("other", "Age"), "n_touched"] == 1 and t.loc[("clinical", "Sign_symptom"), "touched"] == 0.0
    assert set(t.columns) >= {"n", "n_touched", "touched", "chars_removed"}


# ---------------------------------------------------------------- T007 original brat files
TXT = "A 93-year-old woman had a cough since June 2014.\nShe took codeine."
ANN = ("T1\tAge 2 13\t93-year-old\nT2\tSex 14 19\twoman\nT3\tSign_symptom 26 31\tcough\nE1\tSign_symptom:T3 \n"
       "T4\tDate 32 48\tsince June 2014\nT5\tMedication 58 65\tcodeine\nR1\tMODIFY Arg1:T3 Arg2:E1\t\n"
       "T6\tBiological_structure 2 4;14 19\t93 woman\n")


def test_load_brat_reads_exact_offsets_from_a_folder_or_zip(tmp_path):
    import zipfile
    (tmp_path / "d").mkdir()
    (tmp_path / "d" / "111.txt").write_text(TXT)
    (tmp_path / "d" / "111.ann").write_text(ANN)
    with zipfile.ZipFile(tmp_path / "m.zip", "w") as z:
        z.writestr("111.txt", TXT)
        z.writestr("111.ann", ANN)
    for src in (tmp_path / "d", tmp_path / "m.zip"):
        [r] = maccrobat.load_brat(src)
        assert r["note_id"] == "111" and r["text"] == TXT and r["tier"] == "maccrobat"
        assert [s["text"] for s in r["phi"]] == ["93", "June 2014"]          # trimmed to the identifying part
        assert [s["text"] for s in r["decoys"]] == ["93", "woman", "cough", "codeine"]   # fragments kept apart
        for s in r["entities"]:
            assert TXT[s["start"]:s["end"]] == s["text"]


def test_role_ignores_decimal_ranges_and_ages_not_in_years():
    assert maccrobat.role("Date", "0.5-1 years later") == "other"
    assert maccrobat.role("Date", "1.5-2.5 years") == "other"
    assert maccrobat.role("Date", "12.03.2014") == "phi"
    assert maccrobat.role("Age", "100-day-old") == "other"
    assert maccrobat.role("Age", "96 weeks") == "other"
    assert maccrobat.role("Age", "92 months") == "other"
    assert maccrobat.role("Age", "aged 91") == "phi"


def test_load_brat_folder_keeps_windows_line_endings_so_offsets_hold(tmp_path):
    (tmp_path / "1.txt").write_bytes(b"Seen\r\nin June 2014.")
    (tmp_path / "1.ann").write_bytes(b"T1\tDate 9 18\tJune 2014\n")
    [r] = maccrobat.load_brat(tmp_path)
    assert [s["text"] for s in r["phi"]] == ["June 2014"]


def test_routes_from_table_keeps_only_precise_types():
    import pandas as pd
    from dental_omop_nlp import deid_eval
    table = pd.DataFrame({"engine": ["a", "a", "b", "c"], "type": ["DATE", "NAME", "ID", "AGE"],
                          "chars": [10, 10, 10, 10], "precision": [1.0, 0.5, 0.9, 0.1],
                          "kept": [True, False, True, False]})
    assert deid_eval.routes_from_table(table) == {"a": {"DATE"}, "b": {"ID"}}


def test_maccrobat_runs_every_method_scored_on_the_synthetic_notes():
    """Its engine list once lagged the synthetic benchmark's, leaving the two best methods unscored."""
    import ast
    import pandas as pd
    from dental_omop_nlp.paths import DEID_DIR, REPO_ROOT
    src = (REPO_ROOT / "python" / "scripts" / "32_maccrobat_deid.py").read_text()
    default = next(ast.literal_eval(n.value) for n in ast.walk(ast.parse(src))
                   if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "DEFAULT")
    scored = set(pd.read_csv(DEID_DIR / "scores.csv").query("tier == 'all'")["method"])
    assert scored <= set(default), scored - set(default)
