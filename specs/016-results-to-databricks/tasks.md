# Tasks: every model result reaches Databricks

**Tests**: required (test-first): each implementation task follows its failing test.

## US1 - A Kaggle run's results are committed
- [x] T001 Failing tests in `python/tests/test_results_store.py`: `record_results.py` copies the two CSVs, adds a `kaggle` manifest row with the run URL, skips `simulated_*`, and refuses (non-zero exit, nothing changed) a file with fewer rows than the committed one
- [x] T002 Implement `kaggle/record_results.py` and `results_store.read_manifest` / `record`
- [x] T003 Failing test: the Kaggle workflow has an `open_pr` input, `contents`/`pull-requests` write permissions, runs `record_results.py` and `gh pr create`
- [x] T004 Implement the PR step in `.github/workflows/kaggle-medgemma.yml`

## US2 - Every committed result is in the gold tables
- [x] T005 Failing tests: `result_files()` lists non-simulated predictions and details files with kind, method, sha256, rows and source from the manifest (`repo` when absent); `prediction_rows()` / `detail_rows()` carry method, sha256 and source; `new_files()` drops hashes already loaded
- [x] T006 Implement them in `python/dental_omop_nlp/results_store.py` (`@traced`)
- [x] T007 Failing bundle tests: job `load_results` runs `10_load_results.py` with catalog, schema and git_commit; `deploy.yml` runs it after deploying without waiting; the notebook appends to the three tables and the reader notebook tags `source`
- [x] T008 Implement the notebook, the job, the deploy step, and the reader-notebook tag

## US3 - MLflow run per loaded LLM file
- [x] T009 Failing test: `llm_run_metrics()` gives rows, gate-failure rate, fallback rate and agreement with the answer key
- [x] T010 Implement it; the notebook logs one `tracking.track` run per new `llm_details` file

## Polish
- [x] T011 Update `docs/results_storage.md`; run the full Python suite
