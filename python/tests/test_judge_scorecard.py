"""Spec 012: judge-backed scorecard. Every system's answer on the 240 review charts, the judge's
queue, a resumable judge run (simulated here, no network), and every README phenotyping metric
against the truth and against the judge."""

import pandas as pd
import pytest

from dental_omop_nlp import judge_scorecard as js
from dental_omop_nlp import readme_results as rr
from dental_omop_nlp.labels import LABELS


@pytest.fixture(scope="module")
def inp():
    return rr.load_inputs()


@pytest.fixture(scope="module")
def answers(inp):
    return js.chart_answers(inp)


def test_chart_answers_cover_every_readme_system_on_every_review_chart(inp, answers):
    truth, pred, _ = rr.phenotype_predictions(inp)
    assert set(answers["system"]) == set(pred)
    assert len(answers) == 240 * len(pred) and not answers.duplicated(["visit_id", "system"]).any()
    assert set(answers["answer"].dropna()) <= set(LABELS)
    assert set(answers["difficulty"]) == {"L1", "L2", "L3"}
    one = answers[answers.system == "algorithm_v0"].set_index("visit_id")["answer"]
    pd.testing.assert_series_equal(one.reindex(truth.index), pred["algorithm_v0"], check_names=False)


def test_queue_has_one_status_call_per_chart_and_one_verdict_per_distinct_answer(inp, answers):
    q = js.judge_queue(answers, inp["key"])
    status, verdict = q[q.kind == "status"], q[q.kind == "verdict"]
    assert len(status) == 240 and status["answer"].isna().all()
    distinct = answers.dropna(subset=["answer"]).drop_duplicates(["visit_id", "answer"])
    assert len(verdict) == len(distinct) < 240 * 6
    assert not q.duplicated(["visit_id", "kind", "answer"]).any()
    notes = inp["key"]["note_text"]
    assert (q["note_text"].to_numpy() == notes.reindex(q["visit_id"]).to_numpy()).all()


def test_cost_estimate_prices_every_call():
    q = pd.DataFrame({"note_text": ["x" * 400] * 10})
    est = js.estimate_cost(q, usd_per_1m_in=1.0, usd_per_1m_out=2.0, system_tokens=1000, out_tokens=100)
    assert est["calls"] == 10
    assert est["usd"] == pytest.approx(10 * (1100 / 1e6 * 1.0 + 100 / 1e6 * 2.0))


NOTE = "S: bleeding gums. O: max CAL 4 mm interproximal, PD 5 mm. A: Generalized periodontitis stage II, grade B."


def test_status_prompt_shows_no_answer_and_uses_the_aap_criteria():
    from dental_omop_nlp import judge
    assert judge.CRITERIA in judge.STATUS_SYSTEM
    prompt = judge.STATUS_USER.format(note=NOTE)
    assert NOTE in prompt and "Predicted" not in prompt and "{pred}" not in judge.STATUS_USER
    assert judge.STATUS_PROMPT_VERSION != judge.PROMPT_VERSION


@pytest.mark.parametrize(("out", "ok", "why"), [
    ({"supported_status": "periodontitis_stage_2", "quote": "max CAL 4 mm interproximal"}, True, ""),
    ({"supported_status": None, "quote": ""}, True, ""),                      # can't tell is allowed
    ({"supported_status": "stage two", "quote": "max CAL 4 mm"}, False, "bad status"),
    ({"supported_status": "periodontitis_stage_2", "quote": "CAL of 4mm"}, False, "quote not in note"),
    ({"supported_status": "periodontitis_stage_2"}, False, "quote not in note"),
])
def test_status_gate(out, ok, why):
    from dental_omop_nlp import judge
    assert judge.gate_status(NOTE, out) == (ok, why)


def test_simulated_judge_gives_a_status_and_a_verbatim_quote():
    from dental_omop_nlp import judge
    j = judge.SimulatedJudge({1: "periodontitis_stage_2"}, seed=0)
    v = j.status(NOTE, visit_id=1)
    assert v.supported_status in (None, *LABELS) and v.quote_ok
    assert v.supported_status is None or v.quote in NOTE


def test_openai_judge_status_call_sends_no_answer_and_gates_the_reply(monkeypatch):
    """The HTTP path, with the endpoint faked: the request carries the status prompt, the reply is gated."""
    import io
    import json

    from dental_omop_nlp import judge
    sent = {}

    def fake_urlopen(req, timeout):
        sent["body"] = json.loads(req.data)
        reply = {"supported_status": "periodontitis_stage_2", "quote": "max CAL 4 mm interproximal",
                 "rationale": "CAL 3-4 mm"}
        return io.BytesIO(json.dumps({"choices": [{"message": {"content": json.dumps(reply)}}],
                                      "usage": {"prompt_tokens": 900, "completion_tokens": 40}}).encode())

    monkeypatch.setattr(judge.urllib.request, "urlopen", fake_urlopen)
    j = judge.OpenAIJudge(model="m", base_url="https://example.invalid/serving-endpoints", api_key="k")
    v = j.status(NOTE)
    assert sent["body"]["messages"][0]["content"] == judge.STATUS_SYSTEM
    assert "Predicted" not in sent["body"]["messages"][1]["content"]
    assert (v.verdict, v.supported_status, v.quote_ok, v.input_tokens) == ("status", "periodontitis_stage_2", True, 900)
