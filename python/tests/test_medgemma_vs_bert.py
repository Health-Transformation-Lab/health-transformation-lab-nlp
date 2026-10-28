"""MedGemma vs the fine-tuned BERT encoders on the same review charts (spec 004 T018)."""

import pandas as pd
import pytest

from dental_omop_nlp import llm_reader
from dental_omop_nlp.rungs import output_tag


def test_output_tag_keeps_each_variant_in_its_own_file():
    assert output_tag() == ""
    assert output_tag(class_weight="sqrt", seed=1) == "+cw+s1"
    assert output_tag(adapter="runs/medgemma-lora") == "+lora"
    assert output_tag(shots=2) == "+k2"
    assert output_tag(variant="reader-v2-terse") == "+terse"
    assert output_tag(adapter="runs/x", shots=1, variant="reader-v2-terse") == "+lora+k1+terse"


def test_output_tag_names_the_backend_unless_it_is_hf():
    # hf files keep their names (the committed results); a KerasHub run of the same rung gets its own file
    assert output_tag(backend="hf") == "" and output_tag(backend="openai") == ""
    assert output_tag(backend="keras") == "+keras"
    assert output_tag(shots=2, backend="keras") == "+k2+keras"


def test_llm_summary_reports_fallback_and_gate_per_rung():
    d = pd.DataFrame({"gate_ok": [True, True, False, True], "fallback": [False, False, True, False],
                      "input_tokens": [400, 420, 410, 430], "output_tokens": [60, 50, 70, 60],
                      "latency_s": [1.0, 2.0, 3.0, 2.0]})
    s = llm_reader.summarize_details(d)
    assert s["gate_pass"] == pytest.approx(0.75) and s["fallback"] == pytest.approx(0.25)
    assert s["input_tokens_mean"] == pytest.approx(415) and s["latency_s_mean"] == pytest.approx(2.0)


def test_gated_model_without_token_names_the_licence(monkeypatch, tmp_path):
    for v in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv("HF_HOME", str(tmp_path))                 # no cached `huggingface-cli login` either
    entry = {"id": "medgemma-1.5-4b-it", "hf": "google/medgemma-1.5-4b-it", "gated": True,
             "license": "HAI-DEF terms of use, https://example.org/terms"}
    with pytest.raises(RuntimeError, match="HAI-DEF terms"):
        llm_reader.make_backend(entry, "hf")
    monkeypatch.setenv("HF_TOKEN", "x")
    assert llm_reader.make_backend(entry, "hf").hf_id == "google/medgemma-1.5-4b-it"


def test_gated_model_accepts_a_cached_cli_login(monkeypatch, tmp_path):
    for v in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv("HF_HOME", str(tmp_path))
    (tmp_path / "token").write_text("cached")                   # what `huggingface-cli login` writes
    entry = {"hf": "google/medgemma-1.5-4b-it", "gated": True}
    assert llm_reader.make_backend(entry, "hf").hf_id == "google/medgemma-1.5-4b-it"


def test_output_tag_marks_a_non_default_learning_rate():
    from dental_omop_nlp.rungs import output_tag
    assert output_tag(lr=5e-5) == ""
    assert output_tag(lr=2e-5) == "+lr2e-05"
    assert output_tag(class_weight="sqrt", seed=1, lr=1e-5) == "+cw+s1+lr1e-05"
