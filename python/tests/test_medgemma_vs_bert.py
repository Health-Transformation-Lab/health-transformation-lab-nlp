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


def test_llm_summary_reports_fallback_and_gate_per_rung():
    d = pd.DataFrame({"gate_ok": [True, True, False, True], "fallback": [False, False, True, False],
                      "input_tokens": [400, 420, 410, 430], "output_tokens": [60, 50, 70, 60],
                      "latency_s": [1.0, 2.0, 3.0, 2.0]})
    s = llm_reader.summarize_details(d)
    assert s["gate_pass"] == pytest.approx(0.75) and s["fallback"] == pytest.approx(0.25)
    assert s["input_tokens_mean"] == pytest.approx(415) and s["latency_s_mean"] == pytest.approx(2.0)
