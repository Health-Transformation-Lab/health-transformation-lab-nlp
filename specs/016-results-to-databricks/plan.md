# Implementation Plan: every model result reaches Databricks

**Branch**: `016-results-to-databricks` (work lands on `claude/great-cerf-qwbqck`) | **Date**: 2026-10-28 |
**Spec**: [spec.md](spec.md)

## Summary
A small pure-pandas module finds the result files, fingerprints them and turns them into table
rows; a script records a collected Kaggle run in the manifest (refusing a smaller run); the Kaggle
workflow calls it and opens a PR; a new notebook and job load whatever is new into Delta, and the
deploy workflow starts that job after each deploy.

## Technical context
- Python 3.12, pandas; Spark only in the notebook. No new dependencies.
- Storage: Delta tables in `dental_omop.gold_dental_omop_perio`; manifest CSV in git.
- Tests: pytest (module, script, workflow and bundle structure); no Spark in tests.

## Design
| Piece | File |
|---|---|
| Find, fingerprint, shape rows; manifest; MLflow metrics per LLM file | `python/dental_omop_nlp/results_store.py` |
| Record a collected run (copy + manifest; refuse fewer rows; skip simulated) | `kaggle/record_results.py` |
| PR step | `.github/workflows/kaggle-medgemma.yml` (`open_pr` input, default on) |
| Load new file versions to Delta, MLflow run per LLM file | `databricks/notebooks/10_load_results.py` |
| Job `load_results` (serverless CPU) | `databricks/resources/jobs.yml` |
| Run it after each deploy, without waiting | `.github/workflows/deploy.yml` |
| MedGemma reader job rows tagged `source = databricks` | `databricks/notebooks/03_medgemma_reader.py` |
| Docs | `docs/results_storage.md` |

Dedup: the notebook reads `sha256` from `result_files` (if the table exists) and loads only files
whose hash is new. `llm_reader_runs` gets new columns, so appends use `mergeSchema`.

## Constitution check
Synthetic data only; no metric or label change (no R parity change); test-first; `@traced` on
every public function; nothing simulated presented as a result (simulated files are skipped).
