"""Spec 004: MedGemma (or any LLM) as a note reader."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import ClassVar

import pandas as pd
import pytest

from dental_omop_nlp import judge
from dental_omop_nlp.labels import LABELS

NOTE = ("perio charting done: BOP 49%, PD up to 5mm, attachment loss 2-3 mm.\n"
        "Diagnosis: Localized Periodontitis Stage II Grade B.\n")


def _ans(status="periodontitis_stage_2", quote="Diagnosis: Localized Periodontitis Stage II Grade B.", **kw):
    return json.dumps({"status": status, "grade": "B", "extent": "localized", "quote": quote,
                       "rationale": "stated", **kw})


# ---------------------------------------------------------------- prompt + parse
def test_judge_prompt_unchanged_after_sharing_criteria():
    assert judge.SYSTEM.startswith("You are a periodontist auditing")
    assert judge.CRITERIA in judge.SYSTEM
    assert judge.PROMPT_VERSION == "judge-v2"
    assert "use radiographic bone loss only when CAL is not recorded" in " ".join(judge.CRITERIA.split())


def test_reader_prompt_shares_criteria_and_has_note():
    from dental_omop_nlp.llm_reader import build_messages
    msgs = build_messages(NOTE)
    assert msgs[0]["role"] == "system" and judge.CRITERIA in msgs[0]["content"]
    assert NOTE in msgs[-1]["content"]
    terse = build_messages(NOTE, variant="reader-v2-terse")
    assert terse[0]["content"] != msgs[0]["content"]


def test_parse_valid_answer():
    from dental_omop_nlp.llm_reader import parse_answer
    out = parse_answer("Sure!\n```json\n" + _ans() + "\n```", NOTE)
    assert out["gate_ok"] and out["status"] == "periodontitis_stage_2"
    assert out["grade"] == "B" and out["extent"] == "localized"


@pytest.mark.parametrize("raw,why", [
    ("not json at all", "parse"),
    (_ans(status="stage_two"), "bad status"),
    (_ans(quote="Periodontitis Stage III"), "quote not in note"),
    (_ans(quote=""), "quote not in note"),
])
def test_parse_failures_are_flagged(raw, why):
    from dental_omop_nlp.llm_reader import parse_answer
    out = parse_answer(raw, NOTE)
    assert not out["gate_ok"] and why in out["error"]


def test_parse_normalizes_grade_and_extent():
    from dental_omop_nlp.llm_reader import parse_answer
    out = parse_answer(_ans(status="healthy", grade=None, extent=None), NOTE)
    assert out["grade"] == "NA" and out["extent"] == "NA"


# ---------------------------------------------------------------- reader rung
class _Fixed:
    """Backend stub: returns canned raw text."""
    name, simulated = "stub", False

    def __init__(self, raw):
        self.raw, self.calls = raw, []

    def __call__(self, messages, visit_id=None):
        self.calls.append(messages)
        return {"raw": self.raw, "input_tokens": 100, "output_tokens": 30, "latency_s": 0.01}


def _reader(raw, **kw):
    from dental_omop_nlp.llm_reader import LLMReader
    be = _Fixed(raw)
    return LLMReader("medgemma-4b-it", backend=be, **kw), be


def test_reader_predicts_and_records_details():
    r, _ = _reader(_ans())
    pred, proba = r.fit(pd.DataFrame()).predict(pd.DataFrame({"visit_id": [1], "note_text": [NOTE]}))
    assert pred == ["periodontitis_stage_2"] and proba is None
    d = r.details.iloc[0]
    assert d["gate_ok"] and not d["fallback"] and d["input_tokens"] == 100


def test_reader_falls_back_to_note_rules_on_bad_output():
    from dental_omop_nlp.note_reader import read_note
    r, _ = _reader("garbage")
    pred, _ = r.predict(pd.DataFrame({"visit_id": [1], "note_text": [NOTE]}))
    assert pred == [read_note(NOTE)] and r.details.iloc[0]["fallback"]


def test_reader_never_sends_note_with_residual_phi():
    r, be = _reader(_ans())
    leaky = NOTE + "Call pt at 555-867-5309 re: appt.\n"
    pred, _ = r.predict(pd.DataFrame({"visit_id": [1], "note_text": [leaky]}))
    assert be.calls == [] and r.details.iloc[0]["fallback"]
    assert "residual PHI" in r.details.iloc[0]["error"] and pred[0] in LABELS


def test_few_shot_examples_seeded_k_per_status():
    from dental_omop_nlp.llm_reader import pick_examples
    train = pd.DataFrame({"note_text": [f"note {i}" for i in range(60)],
                          "label": [LABELS[i % len(LABELS)] for i in range(60)]})
    a, b = pick_examples(train, 2, seed=1), pick_examples(train, 2, seed=1)
    assert a == b and len(a) == 2 * len(LABELS)
    assert sorted({json.loads(ans)["status"] for _, ans in a}) == sorted(LABELS)
    r, be = _reader(_ans(), shots=1)
    r.fit(train).predict(pd.DataFrame({"visit_id": [1], "note_text": [NOTE]}))
    assert len(be.calls[0]) == 1 + 2 * len(LABELS) + 1   # system + (user, assistant) per example + note


def test_make_rung_builds_llm_reader_for_llm_models():
    from dental_omop_nlp.llm_reader import LLMReader
    from dental_omop_nlp.registry import load_registry
    from dental_omop_nlp.rungs import make_rung
    reg = load_registry()
    r = make_rung("medgemma-4b-it", reg, backend=_Fixed(_ans()))
    assert isinstance(r, LLMReader)
    assert {m["id"] for m in reg["models"] if m["role"] == "llm"} >= {
        "medgemma-4b-it", "medgemma-1.5-4b-it", "medgemma-27b-text-it"}


# ---------------------------------------------------------------- backends
class _FakeOpenAI(BaseHTTPRequestHandler):
    seen: ClassVar[list] = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        _FakeOpenAI.seen.append((self.path, self.headers["Authorization"], body))
        out = json.dumps({"choices": [{"message": {"content": _ans()}}],
                          "usage": {"prompt_tokens": 321, "completion_tokens": 45}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


def test_openai_backend_round_trip():
    from dental_omop_nlp.llm_reader import LLMReader, OpenAIChat
    srv = HTTPServer(("127.0.0.1", 0), _FakeOpenAI)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        be = OpenAIChat(model="medgemma-endpoint", base_url=f"http://127.0.0.1:{srv.server_port}/v1",
                        api_key="tok")
        r = LLMReader("medgemma-4b-it", backend=be)
        pred, _ = r.predict(pd.DataFrame({"visit_id": [7], "note_text": [NOTE]}))
    finally:
        srv.shutdown()
    path, auth, body = _FakeOpenAI.seen[-1]
    assert path == "/v1/chat/completions" and auth == "Bearer tok"
    assert body["model"] == "medgemma-endpoint" and body["temperature"] == 0
    assert pred == ["periodontitis_stage_2"] and r.details.iloc[0]["input_tokens"] == 321


def test_simulated_backend_is_labelled_and_seeded():
    from dental_omop_nlp.llm_reader import LLMReader, SimulatedReader
    truth = {i: LABELS[i % len(LABELS)] for i in range(200)}
    level = {i: ["L1", "L2", "L3"][i % 3] for i in range(200)}
    df = pd.DataFrame({"visit_id": list(truth), "note_text": [NOTE] * 200})
    p1, _ = LLMReader("medgemma-4b-it", backend=SimulatedReader(truth, level, seed=3)).predict(df)
    p2, _ = LLMReader("medgemma-4b-it", backend=SimulatedReader(truth, level, seed=3)).predict(df)
    assert p1 == p2 and SimulatedReader.simulated
    acc = sum(p == truth[i] for i, p in zip(truth, p1)) / 200
    assert 0.7 < acc < 0.95


# ---------------------------------------------------------------- judge family rule, fine-tune data
def test_families_of_evaluated_llms():
    from dental_omop_nlp.registry import families_of, load_registry
    reg = load_registry()
    assert families_of(reg, ["tfidf_logreg", "medgemma-4b-it", "sim:medgemma-27b-text-it"]) == {"gemma"}
    assert families_of(reg, ["note_rules"]) == set()


def test_sft_records_use_reader_format():
    from dental_omop_nlp.llm_reader import parse_answer, sft_records
    train = pd.DataFrame({"note_text": [NOTE], "label": ["periodontitis_stage_2"], "grade": ["B"],
                          "extent": ["localized"]})
    rec = sft_records(train)[0]
    assert [m["role"] for m in rec["messages"]] == ["system", "user", "assistant"]
    target = parse_answer(rec["messages"][-1]["content"], NOTE)
    assert target["gate_ok"] and target["status"] == "periodontitis_stage_2"
