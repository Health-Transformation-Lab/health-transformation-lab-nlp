# Feature Specification: every model result reaches Databricks, wherever it ran

**Feature Branch**: `016-results-to-databricks`

**Created**: 2026-10-28

**Status**: implemented

**Input**: "How are all these results getting stored, do they all make it to Databricks?" They don't:
jobs that run on Databricks write Delta tables, but MedGemma now runs on Kaggle (Databricks Free
Edition often has no GPU) and its results stay a Kaggle download or a GitHub artifact, which
GitHub deletes after 90 days. Committed CSVs reach the dev workspace on every deploy, but nothing
loads them into tables.

> Personal learning project; synthetic data only. The rows loaded are model answers on the 240
> synthetic review notes: no note text goes into the predictions table, and `llm_details` keeps only
> what the committed CSV already holds.

## User stories

### US1 - A Kaggle run's results are committed, not lost (P1)
When the `kaggle-medgemma` workflow collects outputs, it opens a pull request that adds the
`ai_predictions_<rung>.csv` and `llm_details_<rung>.csv` files to `data/datasets/` and records
where they came from in `data/datasets/results_manifest.csv` (file, source `kaggle`, the workflow
run URL, the time). The results are then reviewed and versioned like any other change.

- A run with fewer rows than the committed file (a 10-note test) never replaces it: the step says
  so and opens no PR.
- `simulated_*` files are never recorded.
- Pull requests opened with the workflow's token don't start CI; the PR body says to push or
  re-run checks before merging. If the repo setting "Allow GitHub Actions to create pull requests"
  is off, the branch is still pushed and the log gives the link to open the PR by hand.

### US2 - Every committed result is in the gold tables (P1)
A Databricks job, **Load results**, runs after every deploy (so after every merge, in dev and uat).
It reads every non-simulated `ai_predictions_*.csv` and `llm_details_*.csv` deployed with the
bundle and appends the ones it hasn't loaded yet to:

| Table (`dental_omop.gold_dental_omop_perio`) | One row per | Columns |
|---|---|---|
| `result_files` | loaded file version | `file`, `kind` (predictions / llm_details), `method`, `sha256`, `rows`, `source`, `run_url`, `git_commit`, `loaded_at` |
| `ai_predictions` | (file version, chart) | `method`, `visit_id`, `pred`, `sha256`, `source`, `git_commit`, `loaded_at` |
| `llm_reader_runs` (existing) | (file version, chart) | the `llm_details` columns, `run_ts`, plus `source`, `sha256`, `git_commit` |

- A file version is its SHA-256: reloading the same file adds nothing; a changed file is a new
  version, and the old rows stay (time-stamped history, like the existing append tables).
- `source` comes from `results_manifest.csv`; a file not listed there is `repo` (made locally and
  committed). Rows the MedGemma reader job writes itself carry `source = databricks`.
- Probability columns are not loaded (they differ per method); the CSV stays the full record.

### US3 - Each loaded LLM run is an MLflow run (P2)
For each newly loaded `llm_details` file, the job logs an MLflow run (when tracking is on) with
the method, source, prompt version, shots and run URL as params, and rows, gate-failure and
fallback rates and the share of charts whose status matches the answer key as metrics. A
loader never fails on tracking: no MLflow means no run, as elsewhere (`tracking.track`).

## Out of scope
- Loading the other result folders (`data/corpus`, `data/review`, ladder tables): the same loader
  can take them later.
- Deleting old versions; changing any metric, label rule or score (so no R change).

## Success criteria
- After a Kaggle full run and its PR are merged, `select source, count(*) from ai_predictions group by 1`
  in dev shows `kaggle` rows for the MedGemma rung.
- Running Load results twice adds no rows the second time.
