---
pr: 95
branch: feat/94-016-reader-delta-mlflow
title: "Write the MedGemma reader's run to Unity Catalog and fix its MLflow setup"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: superpowers requesting-code-review subagent + coordinator verification
verdict: approve-with-nits
---

# PR Review: Write the MedGemma reader's run to Unity Catalog and fix its MLflow setup

## Summary
The Databricks MedGemma reader job now writes its predictions to `ai_predictions` and its run details to
`llm_reader_runs`. It deletes and re-appends by the key (source, job run id, method), so a retry replaces
the run's rows. Its MLflow setup now works: the bundle's experiment is passed in, the tracking URI is set,
and a logging failure warns instead of failing the step.

The review found one real defect, now fixed in `ebb1ea8`. The reader's rows now carry `sha256`, and Load
results deleted by `sha256` with no source filter. The reader's CSVs sit in the folder Load results reads,
so the next Load results run would have deleted the reader's rows and loaded them again as `repo` rows
without their run id. What remains is minor, so the verdict is approve-with-nits.

## Scope of Change
- Files changed: 12 (+329 / -18)
- Areas touched: python, databricks, docs, specs
- Commits:
  - a1a07a8 Write the MedGemma reader's run to Unity Catalog and fix its MLflow setup
  - ebb1ea8 Keep Load results from deleting or reloading the reader job's rows
- Range reviewed: `5bee736..ebb1ea8`

## CI Status
| Check | Status |
|---|---|
| python | pending at review time; 615 passed, 14 skipped locally |
| postgres | pending |
| r-parity | pending; no R changes (no labels, scoring, reliability or cost-effectiveness touched) |
| bundle | pending; `jobs.yml` gains two parameters |

## Secrets, PHI and Claims Scan
All three are clean. No tokens, keys or credentialed URLs; no notes, names or real data; no organization
claims.

## Strengths
- One small helper (`delta.replace_batch`) does the idempotent write, and every row carries its batch key
  (`source`, `run_id`, `run_ts`, `git_commit`).
- Key values are validated against a strict pattern before they go into the `DELETE`, and a test covers a
  quote injection.
- Empty columns take the table's existing type, matching how Load results handles them.
- A test reads `jobs.yml` and the notebook to check the new parameters are wired through.
- The docs and spec 016 are updated in the same change.

## Findings
### 🔴 Blocking (Critical)
None remaining.

### 🟡 Should fix (Important, non-blocking)
- **Fixed in ebb1ea8: Load results deleted the reader job's rows.**
  - Where: `databricks/notebooks/10_load_results.py` (`append`) together with `results_store.run_rows`.
  - Verified: `result_files` lists every `ai_predictions_*.csv` in `data/datasets`, which is the folder
    the reader writes to. Load results then ran `DELETE ... WHERE sha256 IN (...)` with no `source`
    filter, and its comment said reader rows had no `sha256`, which is no longer true.
  - The fix: file versions the reader has already written (`source = 'databricks'`) count as loaded, and
    the delete adds `AND source <> 'databricks'`. A regression test covers it.

### 🔵 Nits / suggestions (Minor)
- **`databricks/notebooks/03_medgemma_reader.py` with `jobs.yml` (`max_concurrent_runs: 2`).** Two
  concurrent runs of the same rung write the same CSV paths, so one run can store the other's predictions
  under its own `run_id`. This race already existed for the CSVs; it now reaches the table. Per-run output
  paths would close it. Not fixed here.
- **`tracking.py` `_setup`.** A non-absolute experiment raises inside `track()`, which warns and carries
  on untracked. That fits AGENTS.md, since tracking is optional, but "checked" only means the path is
  absolute: `set_experiment` creates a missing experiment.
- **`delta.py`.** Only all-null columns are cast to the table's type. A real type difference against an
  older `llm_reader_runs` fails the write loudly. That is deliberate and matches Load results, but watch
  the first run against the existing table.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets | ✅ | scan clean |
| Synthetic only, no PHI | ✅ | scan clean |
| No organization claims | ✅ | scan clean |
| Test first | ⚠️ | tests cover every behaviour; the first commit adds code and tests together, so history can't show they failed first. The fix in ebb1ea8 was test-first |
| Python and R in parity | n/a | nothing parity-relevant changed |
| Simulated labelled | ✅ | no new numbers |
| Seeds fixed | n/a | |
| Paths | ✅ | notebooks use the bundle-relative path, as Load results does |
| Spec for big changes | ✅ | spec 016 updated |
| Configuration | ✅ | experiment comes from the existing bundle variable; no per-environment values |
| Secrets register | n/a | no new credential |
| Idempotent writes | ✅ | delete-then-append by batch key; Load results now leaves the reader's rows alone |
| Alerts | n/a | |

## Test Coverage
Covered:
- `test_delta.py`: the batch-key delete, key validation and injection, first write to a missing table,
  and empty-column casting.
- `test_results_store.py`: `run_rows` labelling, and that Load results leaves the reader's rows alone.
- `test_tracking.py`: the experiment check and warn-instead-of-fail logging.

Run locally: `cd python && pytest -q tests` (615 passed, 14 skipped), and `ruff check` on the changed
`python/` files (clean). The notebooks keep the same import-order warnings they have on `main`.

Not run: a live Databricks job. The first dev deploy after merge exercises it.

## Verdict
Approve with nits. The one real defect is fixed and tested. The concurrent-run race is worth its own
small fix later.
