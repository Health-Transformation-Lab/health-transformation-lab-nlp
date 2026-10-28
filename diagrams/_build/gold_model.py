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
    area: str                # results · judge · deid · file
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
PROV = [C("sha256", "string", "SHA-256 of the source file: its version (in result_files for repo · kaggle rows only)", "FK"),
        C("source", "string", "repo · kaggle · databricks"),
        C("run_id", "string", "Databricks job run id (databricks rows)"),
        C("run_ts", "timestamp", "when the reader job ran (databricks rows); llm_reader_runs: also the load time of Load results rows"),
        C("git_commit", "string", "commit the job was deployed from"),
        C("loaded_at", "timestamp", "when Load results wrote it (Load results rows)")]

TABLES = {
    "review_key": Table(
        "file", "One per synthetic review chart (answer_key/review_key.csv, not a table)", "10_build_study.py (seeded)", [
            C("visit_id", "bigint", "review chart (240)", "PK"),
            C("truth_status", "string", "the generator's truth"),
            C("difficulty", "string", "L1 · L2 · L3"),
            C("note_text", "string", "de-identified note, through the leak gate"),
        ]),
    "result_files": Table(
        "results", "One per committed result file version", "Load results: delete-then-append by sha256, written last", [
            C("file", "string", "e.g. ai_predictions_bert-base.csv"),
            C("kind", "string", "predictions · llm_details"),
            C("method", "string", "method (rung) from the file name"),
            C("sha256", "string", "SHA-256 of the file: its version", "PK"),
            C("rows", "bigint", "rows in the file"),
            C("source", "string", "repo · kaggle (results_manifest.csv)"),
            C("run_url", "string", "Kaggle workflow run; empty for repo"),
            C("git_commit", "string", "commit the bundle was deployed from"),
            C("loaded_at", "timestamp", "when Load results wrote it"),
        ]),
    "ai_predictions": Table(
        "results", "One per method and chart, per file version (key sha256 + visit_id) or reader run (key source + run_id + method + visit_id)",
        "Load results: delete-then-append by sha256 · MedGemma reader: replace (source, run_id, method)", [
            C("method", "string", "method (rung), e.g. modernbert-base+cw"),
            C("visit_id", "bigint", "review chart", "PK,FK"),
            C("pred", "string", "predicted status, one of six"),
            *[(C(c.name, c.type, c.description, "PK,FK") if c.name == "sha256" else c) for c in PROV],
        ]),
    "llm_reader_runs": Table(
        "results", "One per LLM reader call on a chart", "as ai_predictions", [
            C("visit_id", "bigint", "review chart", "PK,FK"),
            C("model", "string", "model id"),
            C("backend", "string", "hf (local weights) · openai (OpenAI-compatible endpoint)"),
            C("prompt_version", "string", "e.g. reader-v2"),
            C("shots", "bigint", "few-shot examples in the prompt"),
            C("input_tokens", "bigint", "prompt tokens"),
            C("output_tokens", "bigint", "completion tokens"),
            C("latency_s", "double", "seconds for the call"),
            C("raw", "string", "the model's full reply"),
            C("status", "string", "status the model answered"),
            C("grade", "string", "grade the model answered"),
            C("extent", "string", "extent the model answered"),
            C("quote", "string", "passage quoted from the note"),
            C("gate_ok", "boolean", "quote gate passed: the quote is verbatim in the note"),
            C("error", "string", "call or parse error"),
            C("fallback", "boolean", "gate failed, so the rules answered"),
            C("pred", "string", "final status (= ai_predictions.pred)"),
            C("method", "string", "method (rung), with shot and adapter tags"),
            *[(C(c.name, c.type, c.description, "PK,FK") if c.name == "sha256" else c) for c in PROV],
            C("truth", "string", "answer key truth (databricks rows)"),
            C("difficulty", "string", "L1 · L2 · L3 (databricks rows)"),
        ]),
    "chart_answers": Table(
        "judge", "One per system and review chart (README leaderboard systems)", "Judge scorecard: overwrite", [
            C("visit_id", "bigint", "review chart", "PK,FK"),
            C("system", "string", "AI method, +rules4 variant, rule phenotype or one evidence type", "PK"),
            C("answer", "string", "the system's status; null = no answer", "FK"),
            C("difficulty", "string", "L1 · L2 · L3"),
            C("truth", "string", "the generator's truth"),
        ]),
    "judgments": Table(
        "judge", "One per judge call: a chart's status, or a verdict on one answer",
        "Judge scorecard: overwrite, earlier calls kept and resumed", [
            C("visit_id", "bigint", "review chart", "PK"),
            C("kind", "string", "status (no answer shown) · verdict", "PK,FK"),
            C("answer", "string", "answer judged (verdict rows)", "PK"),
            C("verdict", "string", "correct · incorrect · not_determinable"),
            C("judge_status", "string", "the judge's own status (status rows)"),
            C("quote", "string", "verbatim from the note"),
            C("gate_ok", "boolean", "quote gate and schema check passed"),
            C("gate_reason", "string", "why the gate failed"),
            C("endpoint", "string", "serving endpoint"),
            C("prompt_version", "string", "judge-status-v1 · judge-v2"),
            C("prompt_tokens", "bigint", "prompt tokens"),
            C("completion_tokens", "bigint", "completion tokens"),
            C("latency_s", "double", "seconds for the call"),
            C("simulated", "boolean", "true for the simulated judge"),
            C("api_error", "boolean", "endpoint failed after retries; asked again next run"),
        ]),
    "judge_metrics": Table(
        "judge", "One per system and README metric", "Judge scorecard: overwrite", [
            C("system", "string", "as in chart_answers", "PK"),
            C("group", "string", "README group, e.g. Trained AI on the note"),
            C("metric", "string", "correct · unsafe_rate · sensitivity · …", "PK"),
            C("metric_label", "string", "the metric's README name"),
            C("vs_truth", "double", "against the generator's truth (as in the README)"),
            C("vs_truth_judged", "double", "against truth, on charts the judge answered"),
            C("vs_judge", "double", "with the judge's status as reference"),
            C("difference", "double", "vs_judge − vs_truth"),
            C("n_judged", "bigint", "charts with a judge answer"),
            C("corrected_accuracy", "double", "Rogan-Gladen corrected accuracy from verdicts"),
            C("ci_low", "double", "95% interval, low"),
            C("ci_high", "double", "95% interval, high"),
            C("judged_correct", "double", "share the judge called correct"),
            C("verdict_sensitivity", "double", "verdicts vs truth: sensitivity"),
            C("verdict_specificity", "double", "verdicts vs truth: specificity"),
        ]),
    "judge_agreement": Table(
        "judge", "One per slice: the judge's status against the truth", "Judge scorecard: overwrite", [
            C("group", "string", "all · truth_status · difficulty", "PK"),
            C("value", "string", "e.g. L3", "PK"),
            C("label", "string", "display name"),
            C("n", "bigint", "charts in the slice"),
            C("coverage", "double", "share the judge answered"),
            C("agreement", "double", "agreement with truth"),
            C("ci_low", "double", "95% interval, low"),
            C("ci_high", "double", "95% interval, high"),
            C("kappa", "double", "Cohen's kappa"),
        ]),
    "judge_run": Table(
        "judge", "One per call type: status · verdict · all", "Judge scorecard: overwrite", [
            C("kind", "string", "status · verdict · all", "PK"),
            C("calls", "bigint", "calls made"),
            C("charts", "bigint", "charts covered"),
            C("endpoint_errors", "bigint", "calls the endpoint failed"),
            C("gate_failures", "bigint", "answers that failed the quote gate"),
            C("prompt_tokens", "double", "prompt tokens"),
            C("completion_tokens", "double", "completion tokens"),
            C("usd", "double", "US$ at the endpoint's list price"),
            C("usd_per_chart", "double", "US$ per chart"),
            C("latency_mean_s", "double", "mean seconds per answered call"),
            C("latency_p50_s", "double", "median seconds"),
            C("latency_p95_s", "double", "95th percentile seconds"),
        ]),
    "deid_scores": Table(
        "deid", "One per de-identification engine and test tier", "Judge scorecard: overwrite, from data/deid/scores.csv", [
            C("method", "string", "de-identification engine", "PK"),
            C("tier", "string", "easy · hard · unseen · external · jsl48 · all", "PK"),
            C("n_notes", "bigint", "notes in the tier"),
            C("n_phi", "bigint", "PHI spans"),
            C("entity_recall", "double", "PHI entities caught"),
            C("char_recall", "double", "PHI characters caught"),
            C("char_precision", "double", "removed characters that were PHI"),
            C("decoy_damage", "double", "clinical decoys wrongly removed"),
            C("n_hard_negatives", "bigint", "hard negatives in the tier"),
            C("hard_negative_damage", "double", "hard negatives wrongly removed"),
            C("token_precision", "double", "token-level precision"),
            C("token_recall", "double", "token-level recall"),
            C("token_f1", "double", "token-level F1"),
            C("leaked_per_1k_notes", "double", "PHI left per thousand notes"),
            C("avg_chars", "double", "mean note length"),
            C("group", "string", "engine family (readme_results.deid_group)"),
        ]),
}

R = Relationship
RELATIONSHIPS = [
    # the reader job's own rows (source databricks) carry their scratch CSV's sha256 but have no result_files row
    R("result_files", "ai_predictions", ("sha256",), ("sha256",), "sha256 (repo · kaggle rows)", "|o--o{"),
    R("result_files", "llm_reader_runs", ("sha256",), ("sha256",), "sha256 (repo · kaggle rows)", "|o--o{"),
    R("ai_predictions", "llm_reader_runs", ("method", "visit_id", "source"), ("method", "visit_id", "source"),
      "method, visit_id, source (per version or run)", "}o..o{", derived=True),
    R("review_key", "ai_predictions", ("visit_id",), ("visit_id",), "visit_id"),
    R("review_key", "llm_reader_runs", ("visit_id",), ("visit_id",), "visit_id"),
    R("review_key", "chart_answers", ("visit_id",), ("visit_id",), "visit_id"),
    R("judgments", "chart_answers", ("visit_id", "answer"), ("visit_id", "answer"), "visit_id, answer", "|o--o{"),
    R("judge_run", "judgments", ("kind",), ("kind",), "kind", "||..o{", derived=True),
    R("judgments", "judge_agreement", (), (), "status rows summarised", "}o..o{", derived=True),
    R("chart_answers", "judge_metrics", ("system",), ("system",), "system", "}o..o{", derived=True),
    R("ai_predictions", "chart_answers", ("method",), ("system",), "method = system", "}o..o{", derived=True),
]

AREAS = {   # fill, legend label
    "results": ("#FFF4C2", "gold · results from anywhere (spec 016)"),
    "judge": ("#EFE9FB", "gold · judge scorecard (spec 012)"),
    "deid": ("#E3F1E4", "gold · de-identification benchmark"),
    "file": ("#E4E7EA", "file in git, not a table"),
}
