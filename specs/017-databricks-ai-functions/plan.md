# Implementation Plan: Databricks AI features in the review and the evaluation

**Spec**: [spec.md](spec.md) | **Date**: 2026-10-28

## Design
| Piece | File |
|---|---|
| Label descriptions, SQL statements, response parsing, batch runner with an injectable executor | `python/dental_omop_nlp/databricks_ai.py` |
| CLI: check settings, print the cost estimate, run or simulate, write the CSVs | `python/scripts/41_databricks_ai_methods.py` |
| Plain names and the LLM group for `dbai-*` methods | `python/dental_omop_nlp/readme_results.py` |
| Inventory section and its test | `docs/model_inventory.md`, `python/tests/test_model_inventory.py` |
| Tests (no network) | `python/tests/test_databricks_ai.py` |

The SQL goes through the Statement Execution API with named parameters (note text is never pasted into
SQL), 10 notes per statement: `SELECT id, ai_classify(t, :labels) FROM VALUES (:id0, :t0), ...`. The
`ai_query` reader reuses `llm_reader.PROMPTS["reader-v2"]` and `llm_reader.parse_answer`, so its quote
gate and output columns match the MedGemma reader's.

## Constitution check
- Synthetic data only.
- Scoring code is unchanged, so no R change is needed. New methods enter through the existing
  `ai_predictions_*` path.
- Simulated output is labelled, tests come first, and every public function carries `@traced`.
