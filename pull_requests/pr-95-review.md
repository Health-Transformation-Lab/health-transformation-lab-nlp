---
pr: 95
branch: feat/94-016-reader-delta-mlflow
title: "Load results: don't load the reader job's own CSVs a second time"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: superpowers requesting-code-review subagent + coordinator verification
verdict: approve
---

# PR Review: Load results: don't load the reader job's own CSVs a second time

## Summary
This PR first carried the Unity Catalog and MLflow work for the MedGemma reader job. The same work arrived on
`main` first through PR #92 (issue #90), so it was narrowed to the one gap the review found that `main` still
has. The reader job writes `ai_predictions_<rung>.csv` and `llm_details_<rung>.csv` into `data/datasets`, which
is the folder Load results reads, and loads them itself with `source = databricks`. Load results only counted
versions listed in `result_files` as loaded, so its next run would add the same predictions again as
`source = repo` rows. It now also counts the sha256s the reader has already written as loaded. Verdict: approve.

## Scope of Change
- Files changed: 2 (+14 / -0), plus this review
- Areas touched: databricks, python tests
- Commits: the original commits, then a merge of `main` that takes `main`'s version of everything #92 already
  covers and keeps only the skip
- Range reviewed: `origin/main..HEAD`

## CI Status
| Check | Status |
|---|---|
| python, r-parity, bundle, postgres | green on the earlier head; to re-run on the merge. 617 passed, 14 skipped locally |

## Secrets, PHI and Claims Scan
All three are clean.

## Strengths
- Small change. It reads only `source` and `sha256`, and does nothing when the table or those columns don't exist.

## Findings
### 🔴 Blocking (Critical)
None.

### 🟡 Should fix (Important, non-blocking)
None.

### 🔵 Nits / suggestions (Minor)
- **Not fixed here:** two concurrent reader runs of the same rung (`max_concurrent_runs: 2`) write the same CSV
  paths, so one run can store the other's predictions under its own `run_id`. Per-run output paths would fix it.
- **Uncertain:** whether files the job writes into the bundle folder survive the next bundle deploy. If they
  don't, this skip rarely fires, but it costs nothing when it doesn't.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets, no PHI, no organization claims | ✅ | scans clean |
| Test first | ✅ | the new test fails on `main`'s notebook (`loaded \|=` is absent) |
| Idempotent writes | ✅ | prevents duplicate rows across the two writers |
| Python and R parity | n/a | |

## Test Coverage
A source-level test of the notebook, as the other notebook tests do. `cd python && pytest -q tests`: 617 passed,
14 skipped.

## Verdict
Approve.
