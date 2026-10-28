"""The gold schema dental_omop.gold_dental_omop_perio, declared once: tables, columns, keys, relationships.

The jobs write these tables from pandas (no DDL to read), so this file is the declaration the ERDs
and diagrams/gold/data_model.md are drawn from. python/tests/test_gold_model.py checks its columns
against the CSV twins and results_store, so a column added there fails until it is added here.
Logical keys: Delta enforces none. Synthetic data only.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Column:
    name: str
    type: str
    description: str
    key: str = ""            # "PK", "FK" or "PK,FK": the logical key


@dataclass(frozen=True)
class Table:
    area: str                # results · judge · deid · corpus · file
    description: str         # the grain: one row per ...
    writer: str              # the job and how it writes
    columns: list = field(default_factory=list)


@dataclass(frozen=True)
class Relationship:
    parent: str
    child: str
    parent_cols: tuple
    child_cols: tuple
    label: str
    cardinality: str = "||--o{"   # Mermaid ER: parent side, line, child side
    derived: bool = False         # dashed: summarised from or matched on, not a key


C = Column
PROV = [C("file_sha256", "string", "SHA-256 of the source file: its version", "FK"),
        C("source_code", "string", "repo · kaggle · databricks"),
        C("run_id", "string", "Databricks job run id (databricks rows)"),
        C("run_ts", "timestamp", "when the reader job ran (databricks rows)"),
        C("git_commit_sha", "string", "commit the job was deployed from"),
        C("loaded_ts", "timestamp", "when Load results wrote it (Load results rows)")]

TABLES = {
    "review_key": Table(
        "file", "One per synthetic review chart (answer_key/review_key.csv, not a table)", "10_build_study.py (seeded)", [
            C("visit_id", "bigint", "review chart (240)", "PK"),
            C("truth_status", "string", "the generator's truth"),
            C("difficulty", "string", "L1 · L2 · L3"),
            C("note_text", "string", "de-identified note, through the leak gate"),
        ]),
    "dim_result_file": Table(
        "results", "One per committed result file version", "Load results: append new versions, last", [
            C("file_name", "string", "e.g. ai_predictions_bert-base.csv"),
            C("file_kind_code", "string", "predictions · llm_details"),
            C("method_name", "string", "method (rung) from the file name"),
            C("file_sha256", "string", "SHA-256 of the file: its version", "PK"),
            C("row_count", "bigint", "rows in the file"),
            C("source_code", "string", "repo · kaggle (results_manifest.csv)"),
            C("run_url", "string", "Kaggle workflow run; empty for repo"),
            C("git_commit_sha", "string", "commit the bundle was deployed from"),
            C("loaded_ts", "timestamp", "when Load results wrote it"),
        ]),
    "fact_prediction": Table(
        "results", "One per method and chart, per file version or reader run",
        "Load results: delete-then-append by file_sha256 · MedGemma reader: replace (source_code, run_id, method_name)", [
            C("method_name", "string", "method (rung), e.g. modernbert-base+cw"),
            C("visit_id", "bigint", "review chart", "PK,FK"),
            C("predicted_status_code", "string", "predicted status, one of six"),
            *[(C(c.name, c.type, c.description, "PK,FK") if c.name == "file_sha256" else c) for c in PROV],
        ]),
    "fact_llm_call": Table(
        "results", "One per LLM reader call on a chart", "as fact_prediction", [
            C("visit_id", "bigint", "review chart", "PK,FK"),
            C("model_name", "string", "model id"),
            C("backend_code", "string", "hf (local weights) · openai (OpenAI-compatible endpoint)"),
            C("prompt_version_code", "string", "e.g. reader-v2"),
            C("shot_count", "bigint", "few-shot examples in the prompt"),
            C("input_token_count", "bigint", "prompt tokens"),
            C("output_token_count", "bigint", "completion tokens"),
            C("latency_seconds", "double", "seconds for the call"),
            C("raw_response_text", "string", "the model's full reply"),
            C("answered_status_code", "string", "status the model answered"),
            C("answered_grade_code", "string", "grade the model answered"),
            C("answered_extent_code", "string", "extent the model answered"),
            C("quote_text", "string", "passage quoted from the note"),
            C("is_gate_ok", "boolean", "quote gate passed: the quote is verbatim in the note"),
            C("error_text", "string", "call or parse error"),
            C("is_fallback", "boolean", "gate failed, so the rules answered"),
            C("predicted_status_code", "string", "final status (= fact_prediction.predicted_status_code)"),
            C("method_name", "string", "method (rung), with shot and adapter tags"),
            *[(C(c.name, c.type, c.description, "PK,FK") if c.name == "file_sha256" else c) for c in PROV],
            C("truth_status_code", "string", "answer key truth (databricks rows)"),
            C("difficulty_code", "string", "L1 · L2 · L3 (databricks rows)"),
        ]),
    "fact_chart_answer": Table(
        "judge", "One per system and review chart (README leaderboard systems)", "Judge scorecard: overwrite", [
            C("visit_id", "bigint", "review chart", "PK,FK"),
            C("system_name", "string", "AI method, +rules4 variant, rule phenotype or one evidence type", "PK"),
            C("answer_status_code", "string", "the system's status; null = no answer", "FK"),
            C("difficulty_code", "string", "L1 · L2 · L3"),
            C("truth_status_code", "string", "the generator's truth"),
        ]),
    "fact_judge_call": Table(
        "judge", "One per judge call: a chart's status, or a verdict on one answer",
        "Judge scorecard: overwrite, earlier calls kept and resumed", [
            C("visit_id", "bigint", "review chart", "PK"),
            C("call_kind_code", "string", "status (no answer shown) · verdict", "PK,FK"),
            C("answer_status_code", "string", "answer judged (verdict rows)", "PK"),
            C("verdict_code", "string", "correct · incorrect · not_determinable"),
            C("judge_status_code", "string", "the judge's own status (status rows)"),
            C("quote_text", "string", "verbatim from the note"),
            C("is_gate_ok", "boolean", "quote gate and schema check passed"),
            C("gate_reason_text", "string", "why the gate failed"),
            C("endpoint_name", "string", "serving endpoint"),
            C("prompt_version_code", "string", "judge-status-v1 · judge-v2"),
            C("prompt_token_count", "bigint", "prompt tokens"),
            C("completion_token_count", "bigint", "completion tokens"),
            C("latency_seconds", "double", "seconds for the call"),
            C("is_simulated", "boolean", "true for the simulated judge"),
            C("is_api_error", "boolean", "endpoint failed after retries; asked again next run"),
        ]),
    "judge_metric": Table(
        "judge", "One per system and README metric", "Judge scorecard: overwrite", [
            C("system_name", "string", "as in fact_chart_answer", "PK"),
            C("group_name", "string", "README group, e.g. Trained AI on the note"),
            C("metric_code", "string", "correct · unsafe_rate · sensitivity · …", "PK"),
            C("metric_name", "string", "the metric's README name"),
            C("vs_truth_ratio", "double", "against the generator's truth (as in the README)"),
            C("vs_truth_judged_ratio", "double", "against truth, on charts the judge answered"),
            C("vs_judge_ratio", "double", "with the judge's status as reference"),
            C("difference_ratio", "double", "vs_judge − vs_truth"),
            C("judged_count", "bigint", "charts with a judge answer"),
            C("corrected_accuracy_ratio", "double", "Rogan-Gladen corrected accuracy from verdicts"),
            C("ci_low_ratio", "double", "95% interval, low"),
            C("ci_high_ratio", "double", "95% interval, high"),
            C("judged_correct_ratio", "double", "share the judge called correct"),
            C("verdict_sensitivity_ratio", "double", "verdicts vs truth: sensitivity"),
            C("verdict_specificity_ratio", "double", "verdicts vs truth: specificity"),
        ]),
    "judge_agreement": Table(
        "judge", "One per slice: the judge's status against the truth", "Judge scorecard: overwrite", [
            C("slice_group_code", "string", "all · truth_status · difficulty", "PK"),
            C("slice_value_code", "string", "e.g. L3", "PK"),
            C("slice_name", "string", "display name"),
            C("chart_count", "bigint", "charts in the slice"),
            C("coverage_ratio", "double", "share the judge answered"),
            C("agreement_ratio", "double", "agreement with truth"),
            C("ci_low_ratio", "double", "95% interval, low"),
            C("ci_high_ratio", "double", "95% interval, high"),
            C("kappa_coef", "double", "Cohen's kappa"),
        ]),
    "judge_cost": Table(
        "judge", "One per call type: status · verdict · all", "Judge scorecard: overwrite", [
            C("call_kind_code", "string", "status · verdict · all", "PK"),
            C("call_count", "bigint", "calls made"),
            C("chart_count", "bigint", "charts covered"),
            C("endpoint_error_count", "bigint", "calls the endpoint failed"),
            C("gate_failure_count", "bigint", "answers that failed the quote gate"),
            C("prompt_token_count", "bigint", "prompt tokens"),
            C("completion_token_count", "bigint", "completion tokens"),
            C("cost_usd", "double", "US$ at the endpoint's list price"),
            C("cost_per_chart_usd", "double", "US$ per chart"),
            C("avg_latency_seconds", "double", "mean seconds per answered call"),
            C("p50_latency_seconds", "double", "median seconds"),
            C("p95_latency_seconds", "double", "95th percentile seconds"),
        ]),
    "deid_score": Table(
        "deid", "One per de-identification engine and test tier", "Judge scorecard: overwrite, from data/deid/scores.csv", [
            C("engine_name", "string", "de-identification engine", "PK"),
            C("tier_code", "string", "easy · hard · unseen · external · jsl48 · all", "PK"),
            C("note_count", "bigint", "notes in the tier"),
            C("phi_count", "bigint", "PHI spans"),
            C("entity_recall_ratio", "double", "PHI entities caught"),
            C("char_recall_ratio", "double", "PHI characters caught"),
            C("char_precision_ratio", "double", "removed characters that were PHI"),
            C("decoy_damage_ratio", "double", "clinical decoys wrongly removed"),
            C("hard_negative_count", "bigint", "hard negatives in the tier"),
            C("hard_negative_damage_ratio", "double", "hard negatives wrongly removed"),
            C("token_precision_ratio", "double", "token-level precision"),
            C("token_recall_ratio", "double", "token-level recall"),
            C("token_f1_ratio", "double", "token-level F1"),
            C("leaked_phi_per_1k_note_rate", "double", "PHI left per thousand notes"),
            C("avg_note_char_count", "double", "mean note length"),
            C("group_name", "string", "engine family (readme_results.deid_group)"),
        ]),
    "judge_queue": Table(
        "corpus", "One per prediction sampled for the corpus judge (stratified by method)", "built by hand; read by the LLM judge job", [
            C("method_name", "string", "method (rung)", "PK,FK"),
            C("visit_id", "bigint", "chart or note", "PK,FK"),
            C("note_text", "string", "de-identified note, through the leak gate"),
            C("predicted_status_code", "string", "the method's status, to judge"),
        ]),
    "fact_corpus_judge_call": Table(
        "corpus", "One per corpus judge call (ai_query)", "LLM judge (02_llm_judge.sql): create or replace", [
            C("method_name", "string", "method (rung)", "PK,FK"),
            C("visit_id", "bigint", "chart or note", "PK,FK"),
            C("predicted_status_code", "string", "the status judged"),
            C("verdict_code", "string", "correct · incorrect · not_determinable"),
            C("supported_status_code", "string", "the status the judge says the note supports"),
            C("quote_text", "string", "verbatim from the note"),
            C("rationale_text", "string", "the judge's reason"),
            C("is_gate_ok", "boolean", "quote gate and schema check passed"),
            C("error_text", "string", "ai_query error"),
            C("prompt_version_code", "string", "judge-v2"),
            C("judge_model_name", "string", "serving endpoint"),
        ]),
}

R = Relationship
RELATIONSHIPS = [
    R("dim_result_file", "fact_prediction", ("file_sha256",), ("file_sha256",), "file_sha256"),
    R("dim_result_file", "fact_llm_call", ("file_sha256",), ("file_sha256",), "file_sha256"),
    R("fact_prediction", "fact_llm_call", ("method_name", "visit_id", "source_code"),
      ("method_name", "visit_id", "source_code"), "method_name, visit_id, source_code", "||..o|", derived=True),
    R("review_key", "fact_prediction", ("visit_id",), ("visit_id",), "visit_id"),
    R("review_key", "fact_llm_call", ("visit_id",), ("visit_id",), "visit_id"),
    R("review_key", "fact_chart_answer", ("visit_id",), ("visit_id",), "visit_id"),
    R("fact_judge_call", "fact_chart_answer", ("visit_id", "answer_status_code"), ("visit_id", "answer_status_code"),
      "visit_id, answer_status_code", "|o--o{"),
    R("judge_cost", "fact_judge_call", ("call_kind_code",), ("call_kind_code",), "call_kind_code", "||..o{", derived=True),
    R("fact_judge_call", "judge_agreement", (), (), "status calls summarised", "}o..o{", derived=True),
    R("fact_chart_answer", "judge_metric", ("system_name",), ("system_name",), "system_name", "}o..o{", derived=True),
    R("fact_prediction", "fact_chart_answer", ("method_name",), ("system_name",), "method_name = system_name",
      "}o..o{", derived=True),
    R("fact_prediction", "judge_queue", ("method_name", "visit_id"), ("method_name", "visit_id"),
      "sampled from", "||..o|", derived=True),
    R("judge_queue", "fact_corpus_judge_call", ("method_name", "visit_id"), ("method_name", "visit_id"),
      "method_name, visit_id", "||--o|"),
]

AREAS = {   # fill, legend label
    "results": ("#FFF4C2", "gold · results from anywhere (spec 016)"),
    "judge": ("#EFE9FB", "gold · judge scorecard (spec 012)"),
    "deid": ("#E3F1E4", "gold · de-identification benchmark"),
    "corpus": ("#FDE7F1", "gold · corpus judge (ai_query, notebook 02)"),
    "file": ("#E4E7EA", "file in git, not a table"),
}
