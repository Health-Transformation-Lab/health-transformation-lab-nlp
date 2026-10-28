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


def test_parse_skips_medgemma_thought_block():
    # MedGemma 1.5 may think first: <unused94>thought ... <unused95> then the answer.
    from dental_omop_nlp.llm_reader import parse_answer
    draft = _ans(status="healthy")
    out = parse_answer(f"<unused94>thought\nDraft: {draft}\nNo, it is stage II.<unused95>{_ans()}", NOTE)
    assert out["gate_ok"] and out["status"] == "periodontitis_stage_2"
    cut = parse_answer("<unused94>thought\nThe note says {stage} and then I ran out of tokens", NOTE)
    assert not cut["gate_ok"] and "thought not closed" in cut["error"]


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


# ---- dtype for the GPU the reader lands on (Kaggle T4 / P100 have no native bfloat16) -------------

def test_pick_dtype_matches_the_hardware(monkeypatch):
    from dental_omop_nlp.llm_reader import pick_dtype
    monkeypatch.delenv("DENTAL_LLM_DTYPE", raising=False)
    assert pick_dtype(cuda=True, capability=(8, 6), total_gb=24) == "bfloat16"     # A10 (Databricks)
    assert pick_dtype(cuda=True, capability=(7, 5), total_gb=30) == "float32"      # Kaggle T4 x2
    assert pick_dtype(cuda=True, capability=(6, 0), total_gb=16) == "float16"      # P100: last resort
    assert pick_dtype(cuda=False, capability=None, total_gb=0) == "float32"        # CPU


def test_pick_dtype_can_be_overridden(monkeypatch):
    from dental_omop_nlp.llm_reader import pick_dtype
    monkeypatch.setenv("DENTAL_LLM_DTYPE", "float16")
    assert pick_dtype(cuda=True, capability=(8, 0), total_gb=80) == "float16"


# ---- KerasHub backend: MedGemma from Kaggle Models, no Hugging Face token ----------------------------

def test_gemma_prompt_matches_the_hf_chat_template():
    # MedGemma 1.5's chat_template.jinja: the system text opens the first user turn, contents trimmed,
    # assistant turns are 'model'. <bos> is left to the KerasHub preprocessor (add_start_token).
    from dental_omop_nlp.llm_reader import gemma_prompt
    msgs = [{"role": "system", "content": "SYS"}, {"role": "user", "content": " note one \n"},
            {"role": "assistant", "content": "{}"}, {"role": "user", "content": "note two"}]
    assert gemma_prompt(msgs) == ("<start_of_turn>user\nSYS\n\nnote one<end_of_turn>\n"
                                  "<start_of_turn>model\n{}<end_of_turn>\n"
                                  "<start_of_turn>user\nnote two<end_of_turn>\n<start_of_turn>model\n")
    assert gemma_prompt([{"role": "user", "content": "x"}]) == "<start_of_turn>user\nx<end_of_turn>\n<start_of_turn>model\n"


def test_keras_backend_needs_no_hf_token(monkeypatch):
    from dental_omop_nlp.llm_reader import KerasChat, make_backend
    from dental_omop_nlp.registry import load_registry
    for v in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv("HF_HOME", "/nonexistent")
    entry = next(m for m in load_registry()["models"] if m["id"] == "medgemma-1.5-4b-it")
    assert entry["gated"] and entry["kaggle_model"] == "keras/medgemma/keras/medgemma_1.5_instruct_4b/1"
    be = make_backend(entry, "keras")
    assert isinstance(be, KerasChat) and be.name == "keras" and not be.simulated
    assert be.handle == entry["kaggle_model"] and be.model is None        # loads lazily, on the first note


def test_keras_backend_refuses_a_model_without_a_kaggle_handle():
    from dental_omop_nlp.llm_reader import make_backend
    with pytest.raises(RuntimeError, match="kaggle_model"):
        make_backend({"id": "x", "hf": "google/x"}, "keras")


def test_keras_dtype_defaults_to_bfloat16_and_can_be_overridden(monkeypatch):
    # float32 4B doesn't fit one 15 GB T4, and KerasHub has no Gemma 3 layout map to split it over two
    from dental_omop_nlp.llm_reader import keras_dtype
    monkeypatch.delenv("DENTAL_LLM_DTYPE", raising=False)
    assert keras_dtype() == "bfloat16"
    monkeypatch.setenv("DENTAL_LLM_DTYPE", "float32")
    assert keras_dtype() == "float32"


def test_compare_backends_on_the_same_notes():
    from dental_omop_nlp.llm_reader import compare_backends
    new = pd.DataFrame({"visit_id": [1, 2, 3], "backend": "keras", "status": ["healthy", "gingivitis", None],
                        "pred": ["healthy", "gingivitis", "healthy"], "gate_ok": [True, True, False],
                        "fallback": [False, False, True], "latency_s": [2.0, 4.0, 3.0]})
    base = pd.DataFrame({"visit_id": [3, 2, 1, 9], "backend": "hf",
                         "status": ["healthy", "healthy", "healthy", "gingivitis"],
                         "pred": ["healthy", "healthy", "healthy", "gingivitis"], "gate_ok": True,
                         "fallback": False, "latency_s": 30.0})
    truth = {1: "healthy", 2: "gingivitis", 3: "healthy", 9: "gingivitis"}
    per_note, s = compare_backends(new, base, truth)
    assert list(per_note.visit_id) == [1, 2, 3]                 # only the notes both runs read
    assert list(per_note.same_pred) == [True, False, True]
    assert s["notes"] == 3 and s["new_backend"] == "keras" and s["base_backend"] == "hf"
    assert s["pred_agreement"] == pytest.approx(2 / 3)
    assert s["status_agreement"] == pytest.approx(1 / 2)        # both answered (gate passed): notes 1 and 2
    assert s["new_gate_pass"] == pytest.approx(2 / 3) and s["base_gate_pass"] == 1.0
    assert s["new_accuracy"] == 1.0 and s["base_accuracy"] == pytest.approx(2 / 3)
    assert s["new_latency_s"] == 3.0 and s["base_latency_s"] == 30.0


def test_compare_backends_refuses_runs_with_no_notes_in_common():
    from dental_omop_nlp.llm_reader import compare_backends
    a = pd.DataFrame({"visit_id": [1], "backend": "keras", "status": ["healthy"], "pred": ["healthy"],
                      "gate_ok": [True], "fallback": [False], "latency_s": [1.0]})
    with pytest.raises(ValueError, match="no notes in common"):
        compare_backends(a, a.assign(visit_id=[2], backend="hf"), {1: "healthy", 2: "healthy"})


def test_compare_script_prints_the_backends_side_by_side(tmp_path):
    import subprocess
    import sys

    from dental_omop_nlp.paths import REPO_ROOT
    cols = {"status": ["healthy", "gingivitis"], "pred": ["healthy", "gingivitis"], "gate_ok": True,
            "fallback": False}
    pd.DataFrame({"visit_id": [1, 2], "backend": "keras", "latency_s": 2.0, **cols}).to_csv(tmp_path / "new.csv")
    pd.DataFrame({"visit_id": [1, 2, 3], "backend": "hf", "latency_s": 30.0, "status": ["healthy", "healthy", "x"],
                  "pred": ["healthy", "healthy", "x"], "gate_ok": True, "fallback": False}).to_csv(tmp_path / "base.csv")
    pd.DataFrame({"visit_id": [1, 2, 3], "truth_status": ["healthy", "gingivitis", "x"]}).to_csv(tmp_path / "key.csv")
    out = subprocess.run([sys.executable, str(REPO_ROOT / "python" / "scripts" / "40_compare_backends.py"),
                          "--new", str(tmp_path / "new.csv"), "--base", str(tmp_path / "base.csv"),
                          "--key", str(tmp_path / "key.csv")], check=True, capture_output=True, text=True,
                         env={**__import__("os").environ, "DENTAL_TELEMETRY": "off"}).stdout
    assert "keras vs hf on 2 notes" in out and "same prediction 50%" in out
    assert "accuracy keras 100% / hf 50%" in out
