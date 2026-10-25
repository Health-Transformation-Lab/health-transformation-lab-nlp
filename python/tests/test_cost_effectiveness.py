import pandas as pd

from dental_omop_nlp.cost_effectiveness import (
    calibrate_judge,
    frontier,
    judge_cost,
    method_cost,
    rogan_gladen,
)
from dental_omop_nlp.judge import gate


def test_quote_gate():
    note = "Dx: Generalized periodontitis Stage III Grade B."
    ok, _ = gate(note, {"verdict": "correct", "supported_status": "periodontitis_stage_3",
                        "quote": "periodontitis Stage III"})
    assert ok
    bad, why = gate(note, {"verdict": "correct", "supported_status": "periodontitis_stage_3",
                           "quote": "Stage 3 periodontitis"})
    assert not bad and why == "quote not in note"
    nd, _ = gate(note, {"verdict": "not_determinable", "supported_status": None, "quote": ""})
    assert nd


def test_rogan_gladen():
    # a perfect judge leaves p unchanged
    assert abs(rogan_gladen(0.8, 1.0, 1.0) - 0.8) < 1e-12
    # sens .9 spec .9, true acc .8 -> observed p = .8*.9 + .2*.1 = .74 -> recovers .8
    assert abs(rogan_gladen(0.74, 0.9, 0.9) - 0.8) < 1e-12
    # judge at chance: undefined
    assert rogan_gladen(0.5, 0.5, 0.5) != rogan_gladen(0.5, 0.5, 0.5)  # nan


def test_calibrate_judge():
    g = pd.DataFrame({"truly_correct": [True, True, False, False], "gate_ok": [True] * 4,
                      "verdict": ["correct", "incorrect", "incorrect", "incorrect"]})
    c = calibrate_judge(g)
    assert c["sensitivity"] == 0.5 and c["specificity"] == 1.0


def test_costs():
    llm = {"kind": "llm", "usd_per_1m_input_tokens": 1.0, "usd_per_1m_output_tokens": 2.0,
           "prompt_overhead_tokens": 100, "output_tokens": 10}
    assert abs(method_cost(llm, 1_000_000, 400, {})["cost_usd"] - (500 + 20)) < 1e-9
    loc = {"kind": "local", "hardware": "cpu", "throughput_source": "assumed", "notes_per_sec": 1000 / 3.6}
    c = method_cost(loc, 1_000_000, 400, {"cpu_node_usd_per_hour": 2.0, "gpu_node_usd_per_hour": 5.0})
    assert abs(c["node_hours"] - 1.0) < 1e-9 and abs(c["cost_usd"] - 2.0) < 1e-9
    assert judge_cost(1000, 400, {"usd_per_1m_input_tokens": 1, "usd_per_1m_output_tokens": 1,
                                  "prompt_overhead_tokens": 100, "output_tokens": 0}) == 0.5


def test_frontier_dominance_and_icer():
    t = pd.DataFrame({"method": ["cheap", "mid", "pricey_worse", "best"],
                      "accuracy_est": [0.80, 0.90, 0.85, 0.95], "cost_usd": [10.0, 110.0, 500.0, 1110.0]})
    f = frontier(t, 1000).set_index("method")
    assert f.loc["pricey_worse", "dominated"]
    assert abs(f.loc["mid", "icer_usd_per_extra_correct_note"] - 1.0) < 1e-9     # 100 $ / 100 notes
    assert abs(f.loc["best", "icer_usd_per_extra_correct_note"] - 20.0) < 1e-9   # 1000 $ / 50 notes
    assert f.loc["best", "compared_to"] == "mid"
