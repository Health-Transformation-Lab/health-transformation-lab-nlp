"""Judge-backed scorecard (spec 012): every README phenotyping metric against the truth and the judge.

On synthetic charts the truth is known; on real notes it isn't. An LLM judge can stand in for an
answer key only as far as it agrees with the truth where both exist, so every metric is computed
twice, once against each, and the gap is reported.

    answers = chart_answers(readme_results.load_inputs())   # every system x review chart
    queue = judge_queue(answers, key)                        # 1 status call per chart,
                                                             # 1 verdict call per distinct answer
    judgments = run_judge(queue, judge)                      # resumable; quote gate applied
    metrics = judge_metrics(...)                             # computed here, never by the LLM

Notes come from answer_key/review_key.csv: de-identified and leak-gated when the study was built
(constitution I). A *status* call shows the judge no answer, so its own status isn't anchored on
any system; a *verdict* call is the existing judge.py prompt.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import judge as jg
from . import readme_results as rr
from .cost_effectiveness import corrected_accuracy
from .harm import unsafe_rates
from .ladder_eval import STAGE4
from .phenotype import cohen_kappa

# Rough token counts for the cost estimate printed before a run (judge.SYSTEM is ~1,000 tokens).
SYSTEM_TOKENS = 1000
OUT_TOKENS = 100
CHARS_PER_TOKEN = 4


def chart_answers(inp: dict) -> pd.DataFrame:
    """One row per (visit_id, system): the system's status on that review chart (NaN = none) and
    the note's difficulty (L1/L2/L3). Same systems and answers as the README leaderboard."""
    _, pred, level = rr.phenotype_predictions(inp)
    parts = [pd.DataFrame({"visit_id": p.index, "system": s, "answer": p.to_numpy(),
                           "difficulty": level.reindex(p.index).to_numpy()})
             for s, p in pred.items()]
    return pd.concat(parts, ignore_index=True)


def judge_queue(answers: pd.DataFrame, key: pd.DataFrame) -> pd.DataFrame:
    """kind='status': one per chart, no answer shown. kind='verdict': one per distinct (chart, answer),
    since a verdict depends only on the note and the answer, not on which system gave it."""
    charts = sorted(answers["visit_id"].unique())
    status = pd.DataFrame({"visit_id": charts, "kind": "status", "answer": None})
    verdict = (answers.dropna(subset=["answer"]).drop_duplicates(["visit_id", "answer"])
               [["visit_id", "answer"]].assign(kind="verdict"))
    q = pd.concat([status, verdict[["visit_id", "kind", "answer"]]], ignore_index=True)
    q["note_text"] = key["note_text"].reindex(q["visit_id"]).to_numpy()
    return q.sort_values(["visit_id", "kind", "answer"], na_position="first").reset_index(drop=True)


def estimate_cost(queue: pd.DataFrame, usd_per_1m_in: float, usd_per_1m_out: float,
                  system_tokens: int = SYSTEM_TOKENS, out_tokens: int = OUT_TOKENS) -> dict:
    """Tokens and US$ for judging the queue, printed (and checked against SC-005) before calling."""
    tok_in = float(sum(system_tokens + len(n) // CHARS_PER_TOKEN for n in queue["note_text"]))
    tok_out = float(out_tokens * len(queue))
    return {"calls": len(queue), "input_tokens": tok_in, "output_tokens": tok_out,
            "usd": tok_in / 1e6 * usd_per_1m_in + tok_out / 1e6 * usd_per_1m_out}


JUDGMENT_COLS = ["visit_id", "kind", "answer", "verdict", "judge_status", "quote", "gate_ok", "gate_reason",
                 "endpoint", "prompt_version", "prompt_tokens", "completion_tokens", "simulated", "api_error"]


def _key(r) -> tuple:
    return (int(r.visit_id), r.kind, "" if pd.isna(r.answer) else r.answer)


def run_judge(queue: pd.DataFrame, judge, endpoint: str, done: pd.DataFrame | None = None,
              trace=None) -> pd.DataFrame:
    """One judgment per queue row, in queue order. Rows already in `done` are kept, not re-asked, so a
    run cut short by rate limits resumes. A failed gate counts as not determinable (verdict) or no
    status; an endpoint error is kept with api_error=True and retried. `trace(row, verdict)` is called after each new call (MLflow on Databricks)."""
    have = {_key(r): r._asdict() for r in (done.itertuples(index=False) if done is not None else [])
            if not r.api_error}                       # an endpoint error isn't a judgment: ask again
    sim = bool(getattr(judge, "simulated", False))
    extra = (lambda r: {"visit_id": int(r.visit_id)}) if sim else (lambda r: {})
    rows = []
    for r in queue.itertuples(index=False):
        k = _key(r)
        if k in have:
            rows.append({c: have[k][c] for c in JUDGMENT_COLS})
            continue
        if r.kind == "status":
            v = judge.status(r.note_text, **extra(r))
            version = jg.STATUS_PROMPT_VERSION
        else:
            v = judge(r.note_text, r.answer, **extra(r))
            version = jg.PROMPT_VERSION
        ok = bool(v.quote_ok)
        api_error = bool(v.error) and not ok and v.input_tokens == 0   # judge.py's retry loop gave up
        rows.append({"visit_id": int(r.visit_id), "kind": r.kind, "answer": None if pd.isna(r.answer) else r.answer,
                     "verdict": None if r.kind == "status" else (v.verdict if ok else "not_determinable"),
                     "judge_status": (v.supported_status if ok else None) if r.kind == "status" else None,
                     "quote": v.quote, "gate_ok": ok, "gate_reason": v.error, "endpoint": endpoint,
                     "prompt_version": version, "prompt_tokens": int(v.input_tokens),
                     "completion_tokens": int(v.output_tokens), "simulated": sim,
                     "api_error": api_error})
        if trace is not None:
            trace(r, v)
    return pd.DataFrame(rows, columns=JUDGMENT_COLS)


LEVELS = ("L1", "L2", "L3")
LEVEL_NAMES = {"L1": "easy", "L2": "medium", "L3": "hard"}   # the README's Easy / medium / hard

# The README's own names (readme_results), so tables and the dashboard read like the README.
METRIC_LABELS = {"exact_status": "Exact status right", "sensitivity": "Sensitivity", "specificity": "Specificity",
                 "ppv": "PPV", "npv": "NPV", "stage4_caught": "Stage IV caught", "unsafe_rate": "Unsafe errors",
                 **{f"exact_{lv}": f"Exact status right: {n} note" for lv, n in LEVEL_NAMES.items()}}
STATUS_NAMES = {"healthy": "Healthy", "gingivitis": "Gingivitis", "periodontitis_stage_1": "Stage I",
                "periodontitis_stage_2": "Stage II", "periodontitis_stage_3": "Stage III",
                "periodontitis_stage_4": "Stage IV"}


def _point(ref: pd.Series, p: pd.Series, level: pd.Series, score) -> dict:
    """Every README phenotyping metric for one system against one reference, on ref's charts."""
    if ref.empty:                                    # no judge run: nothing to score against
        return dict.fromkeys(METRIC_LABELS, np.nan)
    p, level = p.reindex(ref.index), level.reindex(ref.index)
    ok = (p == ref)                                  # no status is wrong, as in the README
    s4 = ref == STAGE4
    return {"exact_status": ok.mean(), **rr.yes_no(ref, p, score),
            "stage4_caught": ok[s4].mean() if s4.any() else np.nan,
            "unsafe_rate": unsafe_rates(ref, p)["unsafe_rate"],
            **{f"exact_{lv}": ok[level == lv].mean() if (level == lv).any() else np.nan for lv in LEVELS}}


def _judge_status(judgments: pd.DataFrame) -> pd.Series:
    st = judgments[(judgments["kind"] == "status") & judgments["gate_ok"].astype(bool)]
    return st.set_index("visit_id")["judge_status"].dropna()


def judge_metrics(inp: dict, answers: pd.DataFrame, judgments: pd.DataFrame, n_boot: int = 1000,
                  seed: int = 0) -> pd.DataFrame:
    """One row per (system, metric): vs_truth (the README number, all 240 charts), vs_truth_judged and
    vs_judge (the charts the judge gave a status for), difference = vs_judge - vs_truth_judged, and
    n_judged. exact_status rows also carry judge-corrected accuracy among answered charts
    (Rogan-Gladen from verdicts, judge calibrated on the same charts' truth) with a 95% range."""
    truth, pred, level = rr.phenotype_predictions(inp)
    js_ = _judge_status(judgments) if len(judgments) else pd.Series(dtype=object)
    judged = truth.index.intersection(js_.index)
    score = rr._shared_scorer()
    vd = judgments[judgments["kind"] == "verdict"].copy()
    vd["verdict"] = vd["verdict"].astype(object)
    vd["truly_correct"] = (vd["answer"].to_numpy() == truth.reindex(vd["visit_id"]).to_numpy())
    vd["gate_ok"] = vd["gate_ok"].astype(bool)
    by_pair = vd.set_index(["visit_id", "answer"])
    rows = []
    for s, p in pred.items():
        t_all = _point(truth, p, level, score)
        t_j = _point(truth.loc[judged], p, level, score)
        j = _point(js_.loc[judged], p, level, score)
        a = answers[(answers["system"] == s)].dropna(subset=["answer"])
        sample = by_pair.reindex(pd.MultiIndex.from_frame(a[["visit_id", "answer"]]))[["verdict", "gate_ok"]]
        ca = (corrected_accuracy(sample.reset_index(drop=True), vd.reset_index(drop=True), n_boot=n_boot, seed=seed)
              if len(sample) and len(vd) else {"accuracy_est": np.nan, "ci_low": np.nan, "ci_high": np.nan})
        for k in t_all:
            rows.append({"system": s, "metric": k, "vs_truth": t_all[k], "vs_truth_judged": t_j[k],
                         "vs_judge": j[k], "difference": j[k] - t_j[k], "n_judged": len(judged),
                         **({"corrected_accuracy": ca["accuracy_est"], "ci_low": ca["ci_low"], "ci_high": ca["ci_high"]}
                            if k == "exact_status" else {})})
    out = pd.DataFrame(rows, columns=["system", "metric", "vs_truth", "vs_truth_judged", "vs_judge", "difference",
                                      "n_judged", "corrected_accuracy", "ci_low", "ci_high"])
    out.insert(1, "group", out["system"].map(rr.phenotype_group))
    out.insert(3, "metric_label", out["metric"].map(METRIC_LABELS))
    return out


def judge_agreement(inp: dict, judgments: pd.DataFrame, n_boot: int = 1000, seed: int = 0) -> pd.DataFrame:
    """The judge's own status against the truth, overall and per truth status and note difficulty: n
    charts, coverage (share it gave a status for), agreement where it did (95% bootstrap range), kappa."""
    truth, _, level = rr.phenotype_predictions(inp)
    js_ = (_judge_status(judgments) if len(judgments) else pd.Series(dtype=object)).reindex(truth.index)
    rng = np.random.default_rng(seed)
    groups = [("all", "all", truth.index == truth.index)]
    groups += [("truth_status", v, (truth == v).to_numpy()) for v in sorted(truth.unique())]
    groups += [("difficulty", v, (level == v).to_numpy()) for v in LEVELS]
    rows = []
    for g, v, mask in groups:
        t, j = truth[mask], js_[mask]
        has = j.notna()
        ok = (j[has] == t[has]).to_numpy()
        boot = [ok[rng.integers(0, len(ok), len(ok))].mean() for _ in range(n_boot)] if len(ok) else []
        lo, hi = np.percentile(boot, [2.5, 97.5]) if boot else (np.nan, np.nan)
        label = ("All charts" if g == "all" else STATUS_NAMES.get(v, v) if g == "truth_status"
                 else f"{LEVEL_NAMES[v].capitalize()} note")
        rows.append({"group": g, "value": v, "label": label, "n": int(mask.sum()), "coverage": float(has.mean()),
                     "agreement": float(ok.mean()) if len(ok) else np.nan, "ci_low": float(lo), "ci_high": float(hi),
                     "kappa": cohen_kappa(t[has], j[has]) if len(ok) else np.nan})
    return pd.DataFrame(rows)
