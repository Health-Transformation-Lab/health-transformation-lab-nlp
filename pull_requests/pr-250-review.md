---
pr: 250
branch: fix/248-018-migrate-missing-key
title: "Count a key column neither table has as null on both sides"
author: jcbowyer
reviewed_at: 2026-10-29
reviewer: coordinator verification (one-function fix, verified against dev's tables)
verdict: approve
---

# PR Review: Count a key column neither table has as null on both sides

## Summary
This fixes the `KEY_NOT_EXISTS: run_id` failure that stopped dev's first Load results after #232. The null stand-in
for a missing key column now covers both sides, typed from the other side or as string. Only the legacy table's
columns are written. A read-only run over dev's real legacy tables showed every table resolving, with exactly the
rows #228 predicted still to carry. Approve.

## Scope of Change
- Files changed: 2 (+~25 / -12), plus this review
- Areas touched: databricks, python tests
- Commits: bfbb525 Count a key column neither table has as null on both sides
- Range reviewed: `origin/main...bfbb525`

## CI Status
| Check | Status |
|---|---|
| Test every change (Python, R parity, bundle) | running |
| Check the branch name and issue link | running |

## Secrets, PHI and Claims Scan
Clean.

## Findings
### 🔴 Blocking (Critical)
None.
### 🟡 Should fix (Important, non-blocking)
None.
### 🔵 Nits / suggestions (Minor)
- The behaviour is Spark-only and covered by a string test. A Spark unit test would need pyspark, which the test
  environment doesn't install. The read-only dev run is the behavioural check.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets / PHI / org claims | ✅ | |
| Test first | ✅ | the regression test fails on main |
| Idempotent writes | ✅ | still an anti-join merge by batch key; a rerun adds nothing |
| Configuration | ✅ | no change |
| Commits | ✅ | |

## Test Coverage
- `cd python && pytest -q tests`: 998 passed, 15 skipped.
- A read-only serverless run of the fixed functions in dev, counts only:
  - old catalog `fact_prediction`: 240 rows not yet in gold;
  - old catalog `fact_llm_call`: 240;
  - `llm_reader_runs`: 250;
  - all others: 0, or stale.

## Verdict
approve. Merge when CI is green. Then read the next Load results' `migrate_gold_names` output.
