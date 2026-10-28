---
pr: 92
branch: claude/gifted-ride-47y939
title: "Write the MedGemma reader's run to Unity Catalog and fix its MLflow setup"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: superpowers requesting-code-review subagent + coordinator verification
verdict: approve-with-nits
---

# PR Review: Write the MedGemma reader's run to Unity Catalog and fix its MLflow setup

## Summary
The Databricks MedGemma reader job now writes its predictions to `gold_dental_omop_perio.ai_predictions` and its
per-note details to `llm_reader_runs`. Before, its predictions only reached a CSV in the Git folder. Both writes
are delete-then-append by (source, job run id, method), so a task retry replaces the run's rows instead of
duplicating them. The job also passes the bundle's MLflow experiment to its scripts, and `tracking` checks that
setting before a run starts and no longer lets a failing logging call end the step. Review found one real
defect: Load results could delete the reader job's prediction rows. It was fixed on the branch in `245d451`, with
a test. What remains are minor notes, so the verdict is approve-with-nits.

## Scope of Change
- Files changed: 12 (+330 / -18 approx.), no generated data
- Areas touched: python, databricks, docs, specs
- Commits (net of main):
  - `4530b13`/cherry-picked: Write the MedGemma reader's run to Unity Catalog and fix its MLflow setup (via merge `76060b9`)
  - `76060b9` Merge main, keeping only the Unity Catalog and MLflow changes (drops this branch's earlier KerasHub
    backend, superseded by #83's conversion on main)
  - `245d451` Keep Load results from deleting the reader job's rows
- Range reviewed: `origin/main (5bee736)..245d451`

## CI Status
| Check | Status |
|---|---|
| python | success on `76060b9`; re-running on `245d451` |
| postgres | success on `76060b9` |
| r-parity | success on `76060b9` |
| bundle | success on `76060b9` |
| check (PR conventions) | success |
| azure-infra | success |

## Secrets, PHI and Claims Scan
- Secrets: clean (no tokens, keys or credentialed URLs in the diff).
- PHI / real data: clean (no data files; tests use synthetic visit ids).
- Organization claims: clean.

## Strengths
- The write is properly idempotent. A partial failure (predictions written, details not) recovers on retry, and
  every row carries its batch key (`source`, `run_id`, `method`, `sha256`, `git_commit`, `run_ts`).
- Batch-key values are checked against a strict pattern before they go into the `DELETE`, with a negative test.
- The setting is checked before work starts and tracking fails soft (AGENTS.md "Configuration and secrets").
- `docs/operations.md` no longer allows a plain append for `llm_reader_runs`.

## Findings
### 🔴 Blocking (Critical)
None.

### 🟡 Should fix (Important, non-blocking)
- **Fixed in `245d451`.** `databricks/notebooks/10_load_results.py:83`: Load results deleted `WHERE sha256 IN (...)`
  without a `source` filter. The reader job's rows now carry their CSV's sha256, and a predictions file is
  `visit_id,pred` only, so a deterministic run repeats its bytes. A later committed file with the same bytes would
  have deleted that run's `ai_predictions` rows but not its `llm_reader_runs` rows. Verified by reading both
  writers. Fix: `AND source <> 'databricks'`. Tested by `test_load_results_never_deletes_the_reader_jobs_rows`.

### 🔵 Nits / suggestions (Minor)
- **Fixed in `245d451`.** `03_medgemma_reader.py`: truth and difficulty were attached by position. They are now
  merged on `visit_id` (`validate="one_to_one"`), and a test checks it.
- **Fixed in `245d451`.** Spec 016's `tasks.md` didn't list the change; T013 now does.
- **Note.** `delta.py`: the reader's unpartitioned `DELETE` can race with Load results on the same table and raise
  a Delta concurrency exception. Not verified on a workspace. The task retry covers it because the write is
  idempotent; low impact.
- **Note.** `tests/test_delta.py` uses a fake Spark, so real Delta behaviour isn't covered:
  - mergeSchema adding `run_id`/`run_ts` to the existing `ai_predictions`
  - tz-aware `run_ts` in `createDataFrame`, which the old code already did

  The first dev run after merge is the check. Old rows have NULL `run_id`, so they never match the delete.
- **Note.** `tracking.track`: an error in `end_run` (leaving the run context) still propagates. This is outside
  the stated scope.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets | ✅ | scan clean |
| Synthetic only, no PHI | ✅ | |
| No organization claims; vendors cited | ✅ | |
| Test first | ✅ | `test_delta.py`, `run_rows`, tracking (fake mlflow), job wiring, and the review fixes each had failing tests first |
| Python and R in parity | ✅ | no labels, scoring, reliability or cost-effectiveness change; r-parity green |
| Simulated is labelled simulated | ✅ | no numbers presented |
| Seeds fixed | n/a | |
| Paths | ✅ | notebooks use the same `../../data/datasets` path as before |
| Spec for big changes | ✅ | spec 016 requirement and task T013 |
| Prices | n/a | |
| Commits | ✅ | imperative subjects, bodies say why, co-author trailer |
| Docs | ✅ | `operations.md`, `results_storage.md` |
| Configuration | ✅ | two job parameters, declared once in `jobs.yml`, the same in every target; the PR says they take effect on the next deploy |
| Secrets register | n/a | no credential added or changed |
| Idempotent writes | ✅ | delete-then-append by batch key; Load results no longer deletes the other writer's rows |
| Alerts | n/a | |

## Test Coverage
- New tests:
  - `test_delta.py`: new table, rerun deletes its own batch first, table without key columns, rejected key values.
  - `test_results_store.py`: `run_rows`, the Load results delete filter, the reader's `visit_id` join.
  - `test_tracking.py`: relative experiment on Databricks, bundle experiment, logging error, job wiring.
- Run locally on `245d451`: `cd python && pytest -q tests` gives 616 passed, 14 skipped. `ruff check` is clean on
  the changed package and test files. The notebooks' lint warnings are the same 8 as on main.
- Not run: the Databricks job itself (no valid workspace token in the session); the first dev run after merge
  shows the tables and the MLflow run.

## Verdict
**approve-with-nits.** The one Important finding is fixed with a test. The remaining notes are about Delta
behaviour that only a workspace run can show; check `select source, run_id, method, count(*) from
dental_omop.gold_dental_omop_perio.ai_predictions group by all` and the MLflow experiment after the first dev run.
