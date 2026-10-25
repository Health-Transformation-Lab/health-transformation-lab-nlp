"""The LLM judge as an MLflow GenAI judge (MLflow >= 3.4; docs/mlops.md).

    judge = make_perio_judge("databricks:/<serving endpoint>")     # or "openai:/gpt-4o-mini", ...
    evaluate_predictions(rows, judge, method="ai:tfidf_logreg")   # mlflow.genai.evaluate

Same criteria as judge.py (judge.CRITERIA, AAP worksheet rules). The judge answers
correct / incorrect / not_determinable and must start its rationale with a verbatim
quote from the note; `verdict_from_feedback` applies the same quote gate as judge.py.

`mlflow.genai.evaluate` logs one trace per chart with the judge's assessment, plus a
deterministic `agrees_with_reviewers` scorer when reviewer consensus is given, so
the judge's agreement with people is visible next to its verdicts. Calibration
against reviewers (sensitivity/specificity, bake-off, Rogan-Gladen) stays in
cost_effectiveness.py. On Databricks with MLflow >= 3.14 the judge can also be
aligned to reviewer labels with `judge.align(traces)` (human feedback logged
under the judge's name): see `align_to_reviewers`.

With judge=None a simulated judge scorer is used (dry runs; tagged simulated).
"""

from __future__ import annotations

import re
from typing import Literal

import pandas as pd

from .judge import CRITERIA, Verdict

JUDGE_NAME = "perio_status_supported"
VERDICTS = ("correct", "incorrect", "not_determinable")

INSTRUCTIONS = (
    "You are a periodontist auditing an automated classifier. Decide whether the dental chart note "
    "in {{ inputs }} supports the predicted periodontal status in {{ outputs }} under the 2017 AAP/EFP "
    "classification.\n\n" + CRITERIA + "\n\n"
    "Answer correct if the note supports the predicted status, incorrect if it supports a different "
    "status, not_determinable if the note alone can't settle it. Begin your rationale with "
    'QUOTE: "<the exact sentence from the note that decides it, copied verbatim>" then one sentence.'
)

_QUOTE = re.compile(r'QUOTE:\s*"([^"]*)"')


def make_perio_judge(model: str):
    from mlflow.genai.judges import make_judge
    return make_judge(name=JUDGE_NAME, instructions=INSTRUCTIONS, model=model,
                      feedback_value_type=Literal["correct", "incorrect", "not_determinable"])


def verdict_from_feedback(fb, note: str) -> Verdict:
    """MLflow Feedback -> judge.Verdict, with the quote gate."""
    value = str(getattr(fb, "value", "") or "")
    rationale = str(getattr(fb, "rationale", "") or "")
    m = _QUOTE.search(rationale)
    quote = m.group(1).strip() if m else ""
    ok = value in VERDICTS and (value == "not_determinable" or (bool(quote) and quote in note))
    return Verdict(value, None, quote, rationale, ok, 0, 0, 0.0, "" if ok else "quote gate or bad verdict")


class MLflowJudgeAdapter:
    """A make_judge() judge behind judge.py's interface: judge(note, pred) -> Verdict."""

    def __init__(self, model: str):
        self.model = model
        self.judge = make_perio_judge(model)

    def __call__(self, note: str, pred: str) -> Verdict:
        try:
            fb = self.judge(inputs={"note": note}, outputs={"status": pred})
        except Exception as e:  # noqa: BLE001 - endpoint/network error: record, don't stop the batch
            return Verdict("", None, "", "", False, 0, 0, 0.0, f"{type(e).__name__}: {e}")
        return verdict_from_feedback(fb, note)


def evaluate_predictions(rows: pd.DataFrame, judge=None, method: str = "", simulated: bool = False,
                         sim_sensitivity: float = 0.93, sim_specificity: float = 0.88, seed: int = 11) -> dict:
    """rows: visit_id, note, pred, and optionally truth (reviewer consensus). Logs an MLflow GenAI
    evaluation run; returns metrics, run id and the per-chart result table."""
    import random

    import mlflow
    from mlflow.entities import Feedback
    from mlflow.genai.scorers import scorer

    from .tracking import _setup, dataset_fingerprint, git_commit
    _setup()
    data = [{"inputs": {"note": r.note, "visit_id": int(r.visit_id)}, "outputs": {"status": r.pred},
             **({"expectations": {"status": r.truth}} if "truth" in rows and pd.notna(r.truth) else {})}
            for r in rows.itertuples()]
    scorers = []
    if "truth" in rows:
        @scorer
        def agrees_with_reviewers(outputs, expectations):
            return Feedback(value=outputs["status"] == expectations["status"], rationale="vs reviewer consensus")
        scorers.append(agrees_with_reviewers)
    if judge is not None:
        scorers.append(judge)
    else:
        rng = random.Random(seed)

        @scorer(name=JUDGE_NAME)
        def simulated_judge(outputs, expectations):
            right = outputs["status"] == expectations["status"]
            ok = rng.random() < (sim_sensitivity if right else sim_specificity)
            return Feedback(value=("correct" if right == ok else "incorrect"), rationale="SIMULATED judge")
        scorers.append(simulated_judge)
    with mlflow.start_run(run_name=f"judge:{method}") as run:
        mlflow.set_tags({"step": "15_judge", "method": method, "simulated": str(simulated or judge is None).lower(),
                         "git_commit": git_commit(), "dataset": dataset_fingerprint(), "judge": JUDGE_NAME})
        res = mlflow.genai.evaluate(data=data, scorers=scorers)
    return {"n": len(data), "metrics": dict(res.metrics), "run_id": run.info.run_id, "table": res.result_df}


def align_to_reviewers(judge, experiment_id: str, traces_and_labels: list[tuple[str, str]],
                       optimizer=None):  # pragma: no cover - needs Databricks + MLflow >= 3.14 + an LLM
    """Log each reviewer label as HUMAN feedback under the judge's name, then align the judge.
    traces_and_labels: (trace_id, 'correct' | 'incorrect') from reviewed charts."""
    import mlflow
    from mlflow.entities import AssessmentSource, AssessmentSourceType
    for trace_id, label in traces_and_labels:
        mlflow.log_feedback(trace_id=trace_id, name=judge.name, value=label, rationale="reviewer consensus",
                            source=AssessmentSource(source_type=AssessmentSourceType.HUMAN, source_id="reviewers"))
    traces = mlflow.search_traces(experiment_ids=[experiment_id], max_results=500, return_type="list")
    aligned = judge.align(traces, optimizer) if optimizer else judge.align(traces)
    aligned.register(experiment_id=experiment_id, name=f"{judge.name}_aligned")
    return aligned
