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
    truth, pred, level = rr.phenotype_predictions(inp)
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
