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

import pandas as pd

from . import readme_results as rr

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
