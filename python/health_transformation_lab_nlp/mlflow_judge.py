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

Databricks' judge feature set, all from mlflow.genai:
- custom judge: `make_perio_judge` (make_judge, the AAP criteria, quote gate);
- built-in Guidelines judge: `make_guidelines_judge`, plain-language AAP rules
  (pass/fail per chart, with a rationale);
- deterministic scorer: `no_phi_in_note`, the de-identification residual scan on
  the note the model read (no LLM; runs on every trace);
- alignment to reviewers: `align_to_reviewers`;
- production monitoring: `monitoring_plan` / `start_monitoring` register the
  scorers on an experiment and score a sample of live traces
  (scripts/25_judge_monitoring.py).
"""

from __future__ import annotations

import re
from typing import Literal

import pandas as pd

from .judge import CRITERIA, Verdict
from .telemetry import traced

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


GUIDELINES = [
    ("The predicted status is one of: healthy, gingivitis, periodontitis stage I, II, III or IV, "
     "or cannot_determine."),
    ("When the note records interdental clinical attachment loss, the stage follows it: 1-2 mm is "
     "stage I, 3-4 mm is stage II, 5 mm or more is stage III or IV."),
    ("When the note reports tooth loss due to periodontitis of five or more teeth, the stage is IV; "
     "one to four teeth means at least stage III."),
    ("When the note reports bleeding on probing with no attachment loss and no bone loss, the status "
     "is gingivitis, not periodontitis."),
    ("The prediction uses only what the note states; if the note can't settle the status, the "
     "prediction is cannot_determine."),
]


@traced
def make_guidelines_judge(model: str | None = None, name: str = "aap_guidelines"):
    """Databricks/MLflow built-in Guidelines judge over the AAP rules a note can show."""
    from mlflow.genai.scorers import Guidelines
    return Guidelines(name=name, guidelines=GUIDELINES, model=model)


def _no_phi_in_note(inputs):
    from mlflow.entities import Feedback

    from .deid import residual_scan
    found = residual_scan(str(inputs.get("note", "")))
    kinds = sorted({s["type"] for s in found})
    return Feedback(value="no" if found else "yes",
                    rationale=("PHI-like text: " + ", ".join(kinds)) if found else "no PHI-like text found")


def _make_phi_scorer():
    from mlflow.genai.scorers import scorer
    return scorer(name="no_phi_in_note")(_no_phi_in_note)


class _LazyPhiScorer:
    """`no_phi_in_note` built on first use, so importing this module doesn't need mlflow."""

    _s = None

    def _get(self):
        if self._s is None:
            type(self)._s = _make_phi_scorer()
        return self._s

    def __call__(self, **kw):
        return self._get()(**kw)

    def __getattr__(self, k):
        return getattr(self._get(), k)


no_phi_in_note = _LazyPhiScorer()


@traced
def monitoring_plan(model: str, sample_rate: float = 0.1) -> list[tuple[str, object, float]]:
    """(name, scorer, sample rate) for production monitoring. LLM judges score a sample of live
    traces (they cost tokens); the PHI scan is free and runs on every trace."""
    if not 0 < sample_rate <= 1:
        raise ValueError("sample_rate must be in (0, 1]")
    return [(JUDGE_NAME, make_perio_judge(model), sample_rate),
            ("aap_guidelines", make_guidelines_judge(model), sample_rate),
            ("no_phi_in_note", no_phi_in_note._get(), 1.0)]


@traced
def start_monitoring(model: str, experiment_id: str, sample_rate: float = 0.1) -> list[str]:  # pragma: no cover
    """Register each scorer on the experiment and start it on live traces (Databricks tracking)."""
    from mlflow.genai.scorers import ScorerSamplingConfig
    started = []
    for name, s, rate in monitoring_plan(model, sample_rate):
        reg = s.register(name=name, experiment_id=experiment_id)
        reg.start(name=name, experiment_id=experiment_id, sampling_config=ScorerSamplingConfig(sample_rate=rate))
        started.append(name)
    return started


@traced
def stop_monitoring(experiment_id: str) -> list[str]:  # pragma: no cover - needs Databricks tracking
    from mlflow.genai.scorers import list_scorers
    stopped = []
    for s in list_scorers(experiment_id=experiment_id):
        s.stop(name=s.name, experiment_id=experiment_id)
        stopped.append(s.name)
    return stopped


@traced
def make_perio_judge(model: str):
    from mlflow.genai.judges import make_judge
    return make_judge(name=JUDGE_NAME, instructions=INSTRUCTIONS, model=model,
                      feedback_value_type=Literal["correct", "incorrect", "not_determinable"])


@traced
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


@traced
def evaluate_predictions(rows: pd.DataFrame, judge=None, method: str = "", simulated: bool = False,
                         sim_sensitivity: float = 0.93, sim_specificity: float = 0.88, seed: int = 11,
                         extra_scorers: list | None = None) -> dict:
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
    for s in extra_scorers or []:
        scorers.append(s._get() if isinstance(s, _LazyPhiScorer) else s)
    with mlflow.start_run(run_name=f"judge:{method}") as run:
        mlflow.set_tags({"step": "15_judge", "method": method, "simulated": str(simulated or judge is None).lower(),
                         "git_commit": git_commit(), "dataset": dataset_fingerprint(), "judge": JUDGE_NAME})
        res = mlflow.genai.evaluate(data=data, scorers=scorers)
    return {"n": len(data), "metrics": dict(res.metrics), "run_id": run.info.run_id, "table": res.result_df}


@traced
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
