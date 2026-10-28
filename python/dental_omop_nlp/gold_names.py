"""Gold table and column names (spec 018; AGENTS.md "SQL and data names").

pandas frames and the committed CSVs keep their analysis names; a job renames them with to_gold just
before writing dental_omop.gold_dental_omop_perio. One entry per gold table: the analysis column names it
is written from, and the gold name of each.

    to_gold    rename for gold; an unknown column fails, naming it; _count columns become integers
    from_gold  the reverse, for a job that reads gold back into the analysis code (the judge resume)
    RENAMED    old table name -> new (same name: columns renamed in place)
    migration_plan  what databricks/notebooks/11_migrate_gold_names.py does with each old table
"""

from __future__ import annotations

import pandas as pd

from .telemetry import traced

_PROVENANCE = {"sha256": "file_sha256", "source": "source_code", "run_id": "run_id", "run_ts": "run_ts",
               "git_commit": "git_commit_sha", "loaded_at": "loaded_ts"}

TABLES: dict[str, dict[str, str]] = {
    "dim_result_file": {"file": "file_name", "kind": "file_kind_code", "method": "method_name",
                        "sha256": "file_sha256", "rows": "row_count", "source": "source_code", "run_url": "run_url",
                        "git_commit": "git_commit_sha", "loaded_at": "loaded_ts"},
    "fact_prediction": {"method": "method_name", "visit_id": "visit_id", "pred": "predicted_status_code",
                        **_PROVENANCE},
    "fact_llm_call": {"visit_id": "visit_id", "model": "model_name", "backend": "backend_code",
                      "prompt_version": "prompt_version_code", "shots": "shot_count",
                      "input_tokens": "input_token_count", "output_tokens": "output_token_count",
                      "latency_s": "latency_seconds", "raw": "raw_response_text", "status": "answered_status_code",
                      "grade": "answered_grade_code", "extent": "answered_extent_code", "quote": "quote_text",
                      "gate_ok": "is_gate_ok", "error": "error_text", "fallback": "is_fallback",
                      "pred": "predicted_status_code", "method": "method_name", **_PROVENANCE,
                      "truth": "truth_status_code", "difficulty": "difficulty_code"},
    "fact_chart_answer": {"visit_id": "visit_id", "system": "system_name", "answer": "answer_status_code",
                          "difficulty": "difficulty_code", "truth": "truth_status_code"},
    "fact_judge_call": {"visit_id": "visit_id", "kind": "call_kind_code", "answer": "answer_status_code",
                        "verdict": "verdict_code", "judge_status": "judge_status_code", "quote": "quote_text",
                        "gate_ok": "is_gate_ok", "gate_reason": "gate_reason_text", "endpoint": "endpoint_name",
                        "prompt_version": "prompt_version_code", "prompt_tokens": "prompt_token_count",
                        "completion_tokens": "completion_token_count", "latency_s": "latency_seconds",
                        "simulated": "is_simulated", "api_error": "is_api_error"},
    "judge_metric": {"system": "system_name", "group": "group_name", "metric": "metric_code",
                     "metric_label": "metric_name", "vs_truth": "vs_truth_ratio",
                     "vs_truth_judged": "vs_truth_judged_ratio", "vs_judge": "vs_judge_ratio",
                     "difference": "difference_ratio", "n_judged": "judged_count",
                     "corrected_accuracy": "corrected_accuracy_ratio", "ci_low": "ci_low_ratio",
                     "ci_high": "ci_high_ratio", "judged_correct": "judged_correct_ratio",
                     "verdict_sensitivity": "verdict_sensitivity_ratio",
                     "verdict_specificity": "verdict_specificity_ratio"},
    "judge_agreement": {"group": "slice_group_code", "value": "slice_value_code", "label": "slice_name",
                        "n": "chart_count", "coverage": "coverage_ratio", "agreement": "agreement_ratio",
                        "ci_low": "ci_low_ratio", "ci_high": "ci_high_ratio", "kappa": "kappa_coef"},
    "judge_cost": {"kind": "call_kind_code", "calls": "call_count", "charts": "chart_count",
                   "endpoint_errors": "endpoint_error_count", "gate_failures": "gate_failure_count",
                   "prompt_tokens": "prompt_token_count", "completion_tokens": "completion_token_count",
                   "usd": "cost_usd", "usd_per_chart": "cost_per_chart_usd",
                   "latency_mean_s": "avg_latency_seconds", "latency_p50_s": "p50_latency_seconds",
                   "latency_p95_s": "p95_latency_seconds"},
    "deid_score": {"method": "engine_name", "tier": "tier_code", "n_notes": "note_count", "n_phi": "phi_count",
                   "entity_recall": "entity_recall_ratio", "char_recall": "char_recall_ratio",
                   "char_precision": "char_precision_ratio", "decoy_damage": "decoy_damage_ratio",
                   "n_hard_negatives": "hard_negative_count", "hard_negative_damage": "hard_negative_damage_ratio",
                   "token_precision": "token_precision_ratio", "token_recall": "token_recall_ratio",
                   "token_f1": "token_f1_ratio", "leaked_per_1k_notes": "leaked_phi_per_1k_note_rate",
                   "avg_chars": "avg_note_char_count", "group": "group_name"},
    # written in SQL by 02_llm_judge.sql under the gold names; the analysis names are its CSV export's
    # (data/corpus/judgments_corpus.csv, read by scripts/16_cost_effectiveness.py)
    "judge_queue": {"method": "method_name", "visit_id": "visit_id", "note_text": "note_text",
                    "pred": "predicted_status_code"},
    "fact_corpus_judge_call": {"method": "method_name", "visit_id": "visit_id", "pred": "predicted_status_code",
                               "verdict": "verdict_code", "supported_status": "supported_status_code",
                               "quote": "quote_text", "rationale": "rationale_text", "gate_ok": "is_gate_ok",
                               "error": "error_text", "prompt_version": "prompt_version_code",
                               "judge_model": "judge_model_name"},
}

RENAMED = {"result_files": "dim_result_file", "ai_predictions": "fact_prediction", "llm_reader_runs": "fact_llm_call",
           "chart_answers": "fact_chart_answer", "judgments": "fact_judge_call", "judge_metrics": "judge_metric",
           "judge_agreement": "judge_agreement", "judge_run": "judge_cost", "deid_scores": "deid_score"}
# judge_agreement keeps its name: the migration renames its columns in place

# An old judgments table was written by the scorecard or, if it ran last, by the corpus judge (02): its columns say which.
_TARGETS = {"judgments": ("fact_judge_call", "fact_corpus_judge_call")}

# When a job has already written the new table, the old rows whose batch key it lacks are added; the other
# new tables are rebuilt on every run, so an old copy is stale.
MERGE_KEYS = {"dim_result_file": ("file_sha256",),
              "fact_prediction": ("source_code", "run_id", "method_name", "file_sha256", "visit_id"),
              "fact_llm_call": ("source_code", "run_id", "method_name", "file_sha256", "visit_id"),
              "fact_judge_call": ("visit_id", "call_kind_code", "answer_status_code", "endpoint_name",
                                  "prompt_version_code")}


@traced
def to_gold(df: pd.DataFrame, table: str) -> pd.DataFrame:
    """df under table's gold column names. Columns already under their gold name pass; any other fails."""
    names = TABLES[table]
    gold = set(names.values())
    unknown = [c for c in df.columns if c not in names and c not in gold]
    if unknown:
        raise ValueError(f"{table}: no gold name for column(s) {unknown}; add them to dental_omop_nlp/gold_names.py")
    out = df.rename(columns=names)
    for c in out.columns:
        if c.endswith("_count") and not c.startswith("avg_") and pd.api.types.is_float_dtype(out[c]):
            out[c] = out[c].round().astype("Int64")       # a sum of counts read back as float
    return out


@traced
def from_gold(df: pd.DataFrame, table: str) -> pd.DataFrame:
    """The reverse of to_gold: gold names back to the analysis names."""
    return df.rename(columns={v: k for k, v in TABLES[table].items()})


def _unknown(columns, table: str) -> list[str]:
    names = TABLES[table]
    return [c for c in columns if c not in names and c not in names.values()]


@traced
def migration_plan(existing: dict[str, list[str]]) -> list[tuple[str, str, str]]:
    """(action, old, new) for each old-named table in existing (table name -> its columns):
    copy (no new table yet), merge (a job wrote the new table first: add the old rows whose MERGE_KEYS it lacks),
    stale (the new table is rebuilt every run), rewrite (same name, old columns) or fail (new is then the
    unknown columns, comma-separated). Tables already under their new names need nothing."""
    plan = []
    for old, new in RENAMED.items():
        if old not in existing:
            continue
        cols = existing[old]
        target = next((t for t in _TARGETS.get(old, (new,)) if not _unknown(cols, t)), None)
        if target is None:
            plan.append(("fail", old, ", ".join(_unknown(cols, new))))
        elif old == target:
            if not set(cols) <= set(TABLES[target].values()):
                plan.append(("rewrite", old, target))
        elif target not in existing:
            plan.append(("copy", old, target))
        else:
            plan.append(("merge" if target in MERGE_KEYS else "stale", old, target))
    return plan
