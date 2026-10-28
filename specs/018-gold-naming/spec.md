# Feature Specification: gold table and column names follow one SQL convention

**Feature Branch**: `claude/focused-mccarthy-gy9rjp` (agent session branch)

**Created**: 2026-10-28

**Status**: implemented

**Input**: "ai_predictions and deid_scores are poor titles; it might be easier if table names had some sort of
prefix. Did we not have a SQL standard for all table names to be singular? If not, add to CLAUDE.md all
standard SQL conventions: snake_case, is_ for boolean, date and date time naming conventions etc."

> Personal learning project; synthetic data only. No metric, label rule or result changes: the same rows
> under new names.

The repo had no SQL standard. The singular-table rule came from another project (jcbowyer/DE_Assessment,
`docs/shared/conventions.md`), which this spec adapts. Gold tables were plural and unprefixed, and columns mixed
styles: `gate_ok` and `fallback` are booleans, `loaded_at` and `run_ts` are both timestamps, `latency_s` is a
duration, `n_judged` is a count.

## User stories

### US1 - SQL naming conventions are written down and checked (P1) #113

AGENTS.md (which CLAUDE.md imports) has a "SQL and data names" section: snake_case, singular table names,
`dim_` / `fact_` prefixes in gold, and a column suffix for each kind of value, with the type each suffix implies.
`python/tests/test_sql_conventions.py` checks every gold table declared in `diagrams/_build/gold_model.py` against it.

- A gold table whose name is plural or unprefixed, or a column without a known suffix, or with a type that
  contradicts its suffix (`_ts` not a timestamp, `is_` not a boolean, `_count` not an integer), fails the test.
- OMOP CDM tables and columns keep their official names: the conventions don't apply to them.

### US2 - Gold tables and columns follow the conventions, existing tables migrated (P1) #114

| Was | Now | Kind |
|---|---|---|
| `result_files` | `dim_result_file` | dimension: one row per result file version |
| `ai_predictions` | `fact_prediction` | fact: one method's status for one chart |
| `llm_reader_runs` | `fact_llm_call` | fact: one LLM reader call |
| `chart_answers` | `fact_chart_answer` | fact: one system's answer on one chart |
| `judgments` | `fact_judge_call` | fact: one judge call (judge scorecard) |
| `judge_metrics` | `judge_metric` | summary: one system × metric |
| `judge_agreement` | `judge_agreement` | summary: one slice of judge vs truth |
| `judge_run` | `judge_cost` | summary: cost and speed per call type |
| `deid_scores` | `deid_score` | summary: one de-id engine × test tier |
| `judgments` written by `02_llm_judge.sql` | `fact_corpus_judge_call` | fact: one corpus judge call |
| `judge_queue` (input of 02) | `judge_queue` | its columns renamed |

Columns are renamed by `python/dental_omop_nlp/gold_names.py`, one mapping per table, for example `gate_ok` →
`is_gate_ok`, `loaded_at` → `loaded_ts`, `latency_s` → `latency_seconds`, `n_judged` → `judged_count`,
`pred` → `predicted_status_code`, `sha256` → `file_sha256`. The full list is `diagrams/gold/data_model.md`.

- The rename happens when a job writes gold. pandas frames, the committed CSV twins (`data/datasets/judge/`,
  `llm_details_*.csv`) and the R parity keep their names: they are analysis files, not tables.
- A frame with a column the mapping doesn't know fails before writing, naming the column, so a new column is
  declared and named on purpose instead of arriving under its pandas name.
- **Migration:** the Load results job's first task copies each old table that exists to its new name, columns
  renamed, when the new table doesn't exist yet. The MedGemma reader's Databricks rows and the judge's earlier
  calls (which a rerun resumes from) are kept. Running it again does nothing. Old tables are not dropped: the
  task prints the `DROP TABLE` statements for the owner to run after checking.
- The Scorecard dashboard reads the new tables; its widgets show the same fields.
- Notebook 02's corpus judge writes `fact_corpus_judge_call`, not `judgments`, so the two judge jobs no longer
  overwrite each other's table.

## Out of scope

- Tables from jobs not yet run in a workspace (`study_benchmark`: `labeled_notes`, `benchmark_results`;
  `encoder_gpu`: `encoder_gpu_predictions`). They follow the conventions when they're next changed.
- OMOP CDM tables (`person`, `visit_occurrence`, `measurement`, `note`) keep their official names.

## Success criteria

- `pytest` passes, including the convention and mapping tests; the R parity test is unchanged.
- After a deploy, Load results leaves the 9 tables under their new names with the same row counts as the old.
