"""Spec 007: de-identification methods on a labeled fake-PHI challenge set, and their cost-effectiveness."""

import pandas as pd
import pytest

from dental_omop_nlp import deid, deid_eval
from dental_omop_nlp.phi import FIRST, LAST
from dental_omop_nlp.phi_challenge import CATEGORIES, CH_FIRST, CH_LAST, build_challenge


@pytest.fixture(scope="module")
def ch():
    return build_challenge(n_notes=120, seed=3)


# ---------------------------------------------------------------- US1 challenge set
def test_challenge_is_seeded_and_every_span_matches_its_text(ch):
    assert [r["text"] for r in build_challenge(n_notes=120, seed=3)] == [r["text"] for r in ch]
    for r in ch:
        for s in r["phi"] + r["decoys"]:
            assert r["text"][s["start"]:s["end"]] == s["text"]
    assert {r["tier"] for r in ch} == {"easy", "hard", "unseen"}


def test_challenge_covers_the_hipaa_and_i2b2_categories(ch):
    seen = {s["type"] for r in ch for s in r["phi"]}
    assert set(CATEGORIES) <= seen
    for c in ("PATIENT", "DOCTOR", "RELATIVE", "AGE", "DATE", "PHONE", "EMAIL", "URL", "SSN",
              "MEDICAL_RECORD", "HEALTH_PLAN", "STREET", "CITY", "ZIP", "ORGANIZATION"):
        assert c in CATEGORIES


def test_challenge_names_are_not_the_generator_names():
    from dental_omop_nlp.phi_challenge import UNSEEN_FIRST, UNSEEN_LAST
    assert not set(CH_FIRST + UNSEEN_FIRST) & set(FIRST) and not set(CH_LAST + UNSEEN_LAST) & set(LAST)


def test_hard_tier_has_dental_decoys_that_look_like_phi(ch):
    decoys = " ".join(s["text"] for r in ch for s in r["decoys"])
    for d in ("Glickman", "Miller", "D4341", "#"):
        assert d in decoys
    for r in ch:   # decoys and PHI never overlap
        phi = {i for s in r["phi"] for i in range(s["start"], s["end"])}
        assert not any(i in phi for s in r["decoys"] for i in range(s["start"], s["end"]))


# ---------------------------------------------------------------- US2 engines
def test_regex_v2_catches_shapes_v1_misses():
    t = "Spoke with her husband Kwame Oyelaran at kwame.o@example.org; SSN 123-45-6789; 92 yo."
    v1 = {t[s["start"]:s["end"]] for s in deid.detect_regex(t)}
    v2 = {t[s["start"]:s["end"]] for s in deid.detect_regex_v2(t)}
    assert "kwame.o@example.org" not in v1
    assert {"Kwame Oyelaran", "kwame.o@example.org", "123-45-6789", "92"} <= v2


def test_dental_guard_keeps_dental_terms():
    t = "Glickman class II furcation #19; Miller class I recession; SRP D4341; PD 6-5-6 mm"
    spans = [{"start": t.index("Glickman"), "end": t.index("Glickman") + 8, "type": "NAME"},
             {"start": t.index("6-5-6"), "end": t.index("6-5-6") + 5, "type": "DATE"}]
    assert deid.dental_guard(t, spans) == []


def test_ensemble_is_the_union_then_the_guard():
    t = "Pt Imani Featherstone, Glickman class II at #30, call 205.555.0147"
    out = deid.redact(t, deid.get_engine("regex+regex_v2+guard")(t))
    assert "Imani" not in out and "205.555.0147" not in out
    assert "Glickman class II" in out and "#30" in out


class _FakeIndex:
    def __init__(self, v):
        self.code_point = v


class _FakeEntity:
    def __init__(self, cat, off, ln):
        self.category, self.offset, self.length = cat, _FakeIndex(off), _FakeIndex(ln)


class _FakeDeidClient:
    def deidentify_text(self, body):
        text = body["inputText"] if isinstance(body, dict) else body.input_text
        i = text.index("Kwame")

        class R:
            tagger_result = type("T", (), {"entities": [_FakeEntity("Patient", i, 5)]})()
        return R()


class _FakeLanguageClient:
    def recognize_pii_entities(self, docs, **kw):
        assert kw.get("domain_filter") in ("phi", "PHI") or str(kw.get("domain_filter")).lower().endswith("phi")
        text = docs[0]
        i = text.index("205")

        class E:
            category, offset, length = "PhoneNumber", i, 12

        class D:
            entities, is_error = [E()], False
        return [D()]


def test_azure_deid_parses_tagger_entities():
    t = "Pt Kwame seen today."
    assert deid.detect_azure_deid(t, client=_FakeDeidClient()) == [{"start": 3, "end": 8, "type": "PATIENT"}]


def test_azure_language_parses_pii_entities():
    t = "call 205.555.0147 today"
    assert deid.detect_azure_language(t, client=_FakeLanguageClient()) == [{"start": 5, "end": 17, "type": "PHONE"}]


def test_cloud_engine_without_endpoint_says_so(monkeypatch):
    monkeypatch.delenv("AZURE_DEID_ENDPOINT", raising=False)
    with pytest.raises(RuntimeError, match="AZURE_DEID_ENDPOINT"):
        deid.detect_azure_deid("x")


class _FakeComprehendMedical:
    def detect_phi(self, Text):
        i, j = Text.index("Kwame"), Text.index("205.555.0147")
        return {"Entities": [{"BeginOffset": i, "EndOffset": i + 5, "Type": "NAME", "Score": 0.99},
                             {"BeginOffset": j, "EndOffset": j + 12, "Type": "CONTACT_POINT", "Score": 0.97},
                             {"BeginOffset": 0, "EndOffset": 2, "Type": "PROFESSION", "Score": 0.30}]}


def test_aws_comprehend_parses_phi_entities_above_threshold():
    t = "Pt Kwame, call 205.555.0147"
    spans = deid.detect_aws_comprehend(t, client=_FakeComprehendMedical(), min_score=0.5)
    assert spans == [{"start": 3, "end": 8, "type": "NAME"}, {"start": 15, "end": 27, "type": "PHONE"}]


def test_aws_comprehend_is_registered_and_says_what_it_needs(monkeypatch):
    assert "aws_comprehend" in deid.ENGINES and "aws_comprehend" in deid.CLOUD_ENGINES
    monkeypatch.delenv("AWS_REGION", raising=False)
    with pytest.raises(RuntimeError, match="AWS_REGION"):
        deid.detect_aws_comprehend("x")


def test_service_billed_per_100_characters_with_a_one_unit_minimum():
    cfg = {"kind": "service", "unit": "record_100_chars", "usd_per_unit": 0.001, "free_units": 0}
    # 1,000 notes of 250 chars = 3 units each; 1,000 notes of 40 chars = 1 unit each (minimum)
    assert deid_eval.engine_cost(cfg, 1000, 250, {}) == pytest.approx(3.0)
    assert deid_eval.engine_cost(cfg, 1000, 40, {}) == pytest.approx(1.0)


# ---------------------------------------------------------------- US3 scores
def test_scores_on_a_hand_made_case():
    rec = {"note_id": 1, "tier": "hard", "text": "Pt Ana Ruiz, #3 MB",
           "phi": [{"start": 3, "end": 11, "text": "Ana Ruiz", "type": "PATIENT"}],
           "decoys": [{"start": 13, "end": 15, "text": "#3", "type": "TOOTH"}]}
    full = deid_eval.score_records([rec], lambda t: [{"start": 3, "end": 11, "type": "NAME"}])
    half = deid_eval.score_records([rec], lambda t: [{"start": 3, "end": 6, "type": "NAME"},
                                                     {"start": 13, "end": 15, "type": "ID"}])
    f, h = full["summary"].iloc[0], half["summary"].iloc[0]
    assert f.entity_recall == 1 and f.decoy_damage == 0 and f.char_precision == 1
    assert h.entity_recall == 0 and h.leaked_per_1k_notes == 1000 and h.decoy_damage == 1
    assert h.char_recall == pytest.approx(3 / 8)


def test_regex_v2_beats_v1_on_the_hard_tier(ch):
    s1 = deid_eval.score_records(ch, deid.get_engine("regex"))["summary"].set_index("tier")
    s2 = deid_eval.score_records(ch, deid.get_engine("regex_v2+guard"))["summary"].set_index("tier")
    assert s2.loc["hard", "entity_recall"] > s1.loc["hard", "entity_recall"]
    assert s2.loc["hard", "decoy_damage"] <= s1.loc["hard", "decoy_damage"]


# ---------------------------------------------------------------- US4 cost-effectiveness
def test_service_cost_uses_size_and_free_allowance():
    cfg = {"kind": "service", "unit": "mb", "usd_per_unit": 2.0, "free_units": 50}
    assert deid_eval.engine_cost(cfg, n_notes=1_000_000, avg_chars=1000, compute={}) == pytest.approx(
        (1_000_000 * 1000 / 1e6 - 50) * 2.0)
    rec = {"kind": "service", "unit": "record_1k_chars", "usd_per_unit": 1.0 / 1000, "free_units": 0}
    assert deid_eval.engine_cost(rec, n_notes=10, avg_chars=1500, compute={}) == pytest.approx(20 / 1000)
    loc = {"kind": "local", "notes_per_sec": 100}
    assert deid_eval.engine_cost(loc, n_notes=360_000, avg_chars=1, compute={"cpu_node_usd_per_hour": 2.0}) == pytest.approx(2.0)


def test_frontier_marks_dominated_and_prices_leaks_avoided():
    t = pd.DataFrame({"method": ["a", "b", "c"], "cost_usd": [10.0, 30.0, 50.0],
                      "leaked_per_1m_notes": [500.0, 100.0, 200.0]})
    f = deid_eval.deid_frontier(t).set_index("method")
    assert not f.loc["a", "dominated"] and not f.loc["b", "dominated"] and f.loc["c", "dominated"]
    assert f.loc["b", "icer_usd_per_leak_avoided"] == pytest.approx(20 / 400)
    assert f.loc["b", "compared_to"] == "a"


def test_frontier_prefers_less_dental_damage_at_a_tie():
    t = pd.DataFrame({"method": ["plain", "guarded"], "cost_usd": [5.0, 5.0],
                      "leaked_per_1m_notes": [100.0, 100.0], "decoy_damage": [0.4, 0.05]})
    f = deid_eval.deid_frontier(t).set_index("method")
    assert f.loc["plain", "dominated"] and not f.loc["guarded", "dominated"]


# ---------------------------------------------------------------- external test sets (spec 007 T009)
def test_external_set_loads_spans_or_finds_listed_values(tmp_path):
    import json

    from dental_omop_nlp.phi_challenge import load_external
    f = tmp_path / "ext.jsonl"
    rows = [{"query": "find notes for Ana Ruiz seen 3/4/2024", "phi": [{"value": "Ana Ruiz", "type": "NAME"},
                                                                       {"value": "3/4/2024", "type": "DATE"}]},
            {"query": "patients with stage III periodontitis", "phi": []},                      # hard negative
            {"text": "Pt Bo Li", "phi": [{"start": 3, "end": 8, "type": "NAME"}]}]
    f.write_text("\n".join(json.dumps(r) for r in rows))
    recs = load_external(f)
    assert [r["tier"] for r in recs] == ["external"] * 3
    assert recs[0]["phi"][0] == {"start": 15, "end": 23, "text": "Ana Ruiz", "type": "NAME"}
    assert recs[1]["phi"] == [] and recs[2]["phi"][0]["text"] == "Bo Li"
    s = deid_eval.score_records(recs, deid.get_engine("regex_v2"))["summary"]
    assert set(s.tier) == {"external", "all"}


# ---------------------------------------------------------------- AI engines: transformer NER and LLM
class _FakeHFPipe:
    """Mimics transformers' token-classification pipeline with aggregation_strategy='simple'."""

    def __init__(self, ents):
        self.ents = ents

    def __call__(self, text):
        return [dict(e) for e in self.ents]


def test_transformer_engine_maps_i2b2_labels_and_joins_pieces():
    t = "Pt Kwame Oyelaran seen 3/4/2024 by Dr Lindqvist"
    ents = [{"entity_group": "U-PATIENT", "start": 3, "end": 8, "score": 0.99},          # BILOU prefixes (OBI model)
            {"entity_group": "PATIENT", "start": 9, "end": 17, "score": 0.98},           # next word, same type
            {"entity_group": "DATE", "start": 23, "end": 31, "score": 0.97},
            {"entity_group": "STAFF", "start": 38, "end": 47, "score": 0.40}]            # below threshold
    spans = deid.detect_transformer(t, pipe=_FakeHFPipe(ents), min_score=0.5)
    assert [(t[s["start"]:s["end"]], s["type"]) for s in spans] == [("Kwame Oyelaran", "NAME"), ("3/4/2024", "DATE")]


def test_llm_engine_locates_listed_values_and_drops_invented_ones():
    t = "Pt Kwame Oyelaran, call 205.555.0147. Kwame prefers mornings."
    reply = '[{"text": "Kwame Oyelaran", "type": "NAME"}, {"text": "205.555.0147", "type": "PHONE"},' \
            ' {"text": "Kwame", "type": "NAME"}, {"text": "Jane Doe", "type": "NAME"}]'
    spans = deid.detect_llm(t, complete=lambda system, user: reply)
    got = {t[s["start"]:s["end"]] for s in spans}
    assert got == {"Kwame Oyelaran", "205.555.0147", "Kwame"}            # both Kwames; Jane Doe isn't in the note
    assert deid.LLM_DEID_SYSTEM.count("verbatim") >= 1 and "Glickman" in deid.LLM_DEID_SYSTEM


def test_ai_engines_are_registered_and_say_what_they_need(monkeypatch):
    for e in ("hf_stanford", "hf_obi", "llm"):
        assert e in deid.ENGINES
    monkeypatch.delenv("DEID_LLM_BASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DEID_LLM_BASE_URL"):
        deid.detect_llm("x")


def test_llm_cost_counts_prompt_and_output_tokens():
    cfg = {"kind": "llm", "usd_per_1m_input_tokens": 1.0, "usd_per_1m_output_tokens": 4.0,
           "prompt_overhead_tokens": 300, "output_tokens": 100}
    # 1,000 notes x 400 chars: (300 + 100) input tokens and 100 output tokens per note
    assert deid_eval.engine_cost(cfg, n_notes=1000, avg_chars=400, compute={}) == pytest.approx(
        1000 * 400 / 1e6 * 1.0 + 1000 * 100 / 1e6 * 4.0)


# ---------------------------------------------------------------- John Snow Labs; i2b2/n2c2 2014 corpus
class _Ann:
    def __init__(self, begin, end, result, entity):
        self.begin, self.end, self.result, self.metadata = begin, end, result, {"entity": entity}


class _FakeLight:
    """Mimics Spark NLP LightPipeline.fullAnnotate: chunk 'end' is INCLUSIVE."""

    def fullAnnotate(self, text):  # noqa: N802 - Spark NLP's method name
        i = text.index("Kwame")
        return [{"ner_chunk": [_Ann(i, i + 13, "Kwame Oyelaran", "PATIENT"), _Ann(0, 1, "Pt", "O")]}]


def test_jsl_engine_reads_chunks_with_inclusive_ends():
    t = "Pt Kwame Oyelaran seen today"
    assert deid.detect_jsl(t, light=_FakeLight()) == [{"start": 3, "end": 17, "type": "NAME"}]
    assert "jsl" in deid.ENGINES and "jsl" in deid.CLOUD_ENGINES


def test_i2b2_2014_loader_reads_xml_tags(tmp_path):
    from dental_omop_nlp.phi_challenge import load_i2b2_2014
    note = "Record date: 2090-01-02\\nMr. Bo Li seen at Oak Clinic."
    text = note.replace("\\\\n", "\\n")
    s1, s2 = text.index("2090-01-02"), text.index("Bo Li")
    xml = (f'<?xml version="1.0" encoding="UTF-8" ?><deIdi2b2><TEXT><![CDATA[{text}]]></TEXT><TAGS>'
           f'<DATE id="P0" start="{s1}" end="{s1 + 10}" text="2090-01-02" TYPE="DATE" comment="" />'
           f'<NAME id="P1" start="{s2}" end="{s2 + 5}" text="Bo Li" TYPE="PATIENT" comment="" />'
           f'</TAGS></deIdi2b2>')
    (tmp_path / "100-01.xml").write_text(xml)
    recs = load_i2b2_2014(tmp_path)
    assert len(recs) == 1 and recs[0]["tier"] == "i2b2_2014"
    assert [(p["text"], p["type"]) for p in recs[0]["phi"]] == [("2090-01-02", "DATE"), ("Bo Li", "PATIENT")]


def test_external_set_reads_the_asq_phi_text_format(tmp_path):
    """ASQ-PHI ships as delimited text: ===QUERY=== line, ===PHI_TAGS===, one JSON tag per line."""
    from dental_omop_nlp.phi_challenge import load_external
    f = tmp_path / "queries.txt"
    f.write_text('===QUERY===\nDose advice for Ana Ruiz, seen at Oak Clinic 3/4/2024?\n===PHI_TAGS===\n'
                 '{"identifier_type": "NAME", "value": "Ana Ruiz"}\n'
                 '{"identifier_type": "GEOGRAPHIC_LOCATION", "value": "Oak Clinic"}\n'
                 '{"identifier_type": "DATE", "value": "3/4/2024"}\n\n'
                 '===QUERY===\nFirst-line therapy for stage III periodontitis in a 50-year-old?\n===PHI_TAGS===\n\n')
    recs = load_external(f)
    assert len(recs) == 2 and recs[0]["tier"] == "external"
    assert [(p["text"], p["type"]) for p in recs[0]["phi"]] == [
        ("Ana Ruiz", "NAME"), ("Oak Clinic", "GEOGRAPHIC_LOCATION"), ("3/4/2024", "DATE")]
    assert recs[1]["phi"] == [] and recs[1]["text"].startswith("First-line")


def test_hard_negative_damage_counts_phi_free_notes_with_anything_removed():
    recs = [{"note_id": 1, "tier": "external", "text": "Stage III in a 50-year-old", "phi": [], "decoys": []},
            {"note_id": 2, "tier": "external", "text": "Plaque control advice", "phi": [], "decoys": []},
            {"note_id": 3, "tier": "external", "text": "Pt Bo Li", "decoys": [],
             "phi": [{"start": 3, "end": 8, "text": "Bo Li", "type": "NAME"}]}]
    s = deid_eval.score_records(recs, lambda t: [{"start": 0, "end": 5, "type": "NAME"}] if "Stage" in t else [])
    ext = s["summary"].set_index("tier").loc["external"]
    assert ext.n_hard_negatives == 2 and ext.hard_negative_damage == 0.5


# ---------------------------------------------------------------- Databricks ai_mask
def test_ai_mask_recovers_spans_from_masked_text():
    t = "Pt Kwame Oyelaran seen 3/4/2024; Glickman class II on #19."
    masked = "Pt [MASKED] seen [MASKED]; Glickman class II on #19."
    spans = deid.detect_ai_mask(t, mask=lambda text, labels: masked)
    assert [t[s["start"]:s["end"]] for s in spans] == ["Kwame Oyelaran", "3/4/2024"]
    assert {s["type"] for s in spans} == {"PHI"}


def test_ai_mask_falls_back_to_a_diff_when_the_model_also_rewrites_text():
    t = "Pt Kwame Oyelaran seen 3/4/2024 for SRP."
    masked = "Pt [MASKED] seen [MASKED] for scaling."           # 'SRP' rewritten: no exact piece match
    spans = deid.detect_ai_mask(t, mask=lambda text, labels: masked)
    got = [t[s["start"]:s["end"]] for s in spans]
    assert "Kwame Oyelaran" in got and "3/4/2024" in got


def test_ai_mask_is_registered_and_says_what_it_needs(monkeypatch):
    assert "ai_mask" in deid.ENGINES and "ai_mask" in deid.CLOUD_ENGINES
    assert "person" in deid.AI_MASK_LABELS and "date" in deid.AI_MASK_LABELS
    monkeypatch.delenv("DATABRICKS_WAREHOUSE_ID", raising=False)
    with pytest.raises(RuntimeError, match="DATABRICKS_WAREHOUSE_ID"):
        deid.detect_ai_mask("x")


# ---------------------------------------------------------------- routed combination
def _route_records():
    t = "Pt Ana Ruiz seen 3/4/2024, BOP 6-5-6"
    return [{"note_id": 1, "tier": "hard", "text": t, "decoys": [],
             "phi": [{"start": 3, "end": 11, "text": "Ana Ruiz", "type": "PATIENT"},
                     {"start": 17, "end": 25, "text": "3/4/2024", "type": "DATE"}]}]


def _engine_a(t):   # names right; its "dates" are probing readings (wrong)
    return [{"start": 3, "end": 11, "type": "NAME"}, {"start": 31, "end": 36, "type": "DATE"}]


def _engine_b(t):   # dates right
    return [{"start": 17, "end": 25, "type": "DATE"}]


def test_routes_keep_only_engine_types_that_were_precise_on_the_training_tiers():
    routes, table = deid_eval.choose_routes(_route_records(), {"a": _engine_a, "b": _engine_b}, min_precision=0.8,
                                            guard=False)
    assert routes == {"a": {"NAME"}, "b": {"DATE"}}
    row = table.set_index(["engine", "type"]).loc[("a", "DATE")]
    assert row.precision == 0.0 and not row.kept


def test_routed_engine_unions_only_the_routed_types():
    detect = deid.routed_engine({"a": {"NAME"}, "b": {"DATE"}}, {"a": _engine_a, "b": _engine_b}, guard=False)
    t = _route_records()[0]["text"]
    assert [t[s["start"]:s["end"]] for s in detect(t)] == ["Ana Ruiz", "3/4/2024"]


def test_service_price_tiers_apply_by_volume_after_the_free_allowance():
    # Comprehend Medical DetectPHI (AWS price list, us-east-1): 0.0014 to 1M units, 0.0005 to 2M, then 0.00025
    cfg = {"kind": "service", "unit": "record_100_chars", "free_units": 0,
           "tiers": [[1_000_000, 0.0014], [2_000_000, 0.0005], [None, 0.00025]]}
    # 1M notes of 410 chars = 5 units each = 5M units
    assert deid_eval.engine_cost(cfg, 1_000_000, 410, {}) == pytest.approx(1400 + 500 + 3_000_000 * 0.00025)
    # the tier string written to cost_inputs.csv round-trips
    assert deid_eval.parse_tiers(deid_eval.format_tiers(cfg["tiers"])) == cfg["tiers"]
    free = dict(cfg, free_units=500_000)
    assert deid_eval.engine_cost(free, 100_000, 410, {}) == pytest.approx(0.0)


def test_llm_that_returns_the_whole_note_pays_output_tokens_for_it():
    cfg = {"kind": "llm", "usd_per_1m_input_tokens": 1.0, "usd_per_1m_output_tokens": 4.0,
           "prompt_overhead_tokens": 100, "output_tokens": 10, "output_echoes_note": 1}
    # 1,000 notes x 400 chars: input 100 + 100 tokens; output 10 + 100 tokens (the masked note)
    assert deid_eval.engine_cost(cfg, 1000, 400, {}) == pytest.approx(1000 * (200 * 1.0 + 110 * 4.0) / 1e6)


class _TruncatingPipe:
    """Like a 512-token model: sees only the first 200 characters; finds 'Kwame' there."""

    def __init__(self):
        self.calls = []

    def __call__(self, text):
        self.calls.append(len(text))
        seen = text[:200]
        i = seen.find("Kwame")
        return [{"entity_group": "PATIENT", "start": i, "end": i + 5, "score": 0.99}] if i >= 0 else []


def test_transformer_reads_long_notes_in_windows_and_maps_offsets_back():
    t = ("Perio maintenance visit, no change. " * 100) + "Pt Kwame seen today."   # Kwame past 3,600 chars
    pipe = _TruncatingPipe()
    spans = deid.detect_transformer(t, pipe=pipe, window_chars=150)
    assert [t[s["start"]:s["end"]] for s in spans] == ["Kwame"]
    assert max(pipe.calls) <= 150


def test_external_set_reads_the_jsl_benchmark_csv(tmp_path):
    """John Snow Labs' benchmark CSV: one row per labeled chunk, the full text repeated, end exclusive."""
    import pandas as pd

    from dental_omop_nlp.phi_challenge import load_external
    t1, t2 = "Pt Ana Ruiz seen 3/4/2024 .", "No identifiers here ."
    pd.DataFrame([{"doc_id": 1, "text": t1, "begin": 3, "end": 11, "chunk": "Ana Ruiz", "chunk_label": "NAME"},
                  {"doc_id": 1, "text": t1, "begin": 17, "end": 25, "chunk": "3/4/2024", "chunk_label": "DATE"},
                  {"doc_id": 2, "text": t2, "begin": None, "end": None, "chunk": None, "chunk_label": None}]
                 ).to_csv(tmp_path / "gt.csv", index=False)
    recs = load_external(tmp_path / "gt.csv", tier="jsl48")
    assert [r["tier"] for r in recs] == ["jsl48", "jsl48"]
    assert [(p["text"], p["type"]) for p in recs[0]["phi"]] == [("Ana Ruiz", "NAME"), ("3/4/2024", "DATE")]
    assert recs[1]["phi"] == []


def test_token_level_phi_scores_follow_the_jsl_rule():
    """A token is PHI if it starts inside a span (gold or predicted); precision/recall/F1 on the PHI class."""
    t = "Pt Ana Ruiz seen 3/4/2024 ."
    rec = {"note_id": 1, "tier": "jsl48", "text": t, "decoys": [],
           "phi": [{"start": 3, "end": 11, "text": "Ana Ruiz", "type": "NAME"},
                   {"start": 17, "end": 25, "text": "3/4/2024", "type": "DATE"}]}
    # finds Ana Ruiz (2 tokens), misses the date (3/4/2024 = 5 tokens), wrongly flags 'seen'
    s = deid_eval.score_records([rec], lambda x: [{"start": 3, "end": 16, "type": "NAME"}])["summary"]
    row = s.set_index("tier").loc["jsl48"]
    assert row.token_recall == pytest.approx(2 / 7) and row.token_precision == pytest.approx(2 / 3)


def test_all_tier_is_the_challenge_set_only():
    recs = [{"note_id": i, "tier": tier, "text": "Pt Bo Li", "decoys": [],
             "phi": [{"start": 3, "end": 8, "text": "Bo Li", "type": "NAME"}]}
            for i, tier in enumerate(["easy", "external", "jsl48"])]
    s = deid_eval.score_records(recs, lambda t: [])["summary"].set_index("tier")
    assert s.loc["all"].n_notes == 1
