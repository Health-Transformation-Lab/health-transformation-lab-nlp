---
pr: 153
branch: ci/152-parity-only-when-needed
title: "Run R parity on a pull request only when a change can reach it"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator review (CI only: one script, one workflow change, one test file)
verdict: approve
---

# PR Review: Run R parity on a pull request only when a change can reach it

## Summary
A `changes` job decides from the import graph whether a pull request can affect R parity. `r-parity` is skipped
when it can't; pushes to `main`, manual runs and a weekly run still run it in full. Approve.

## Scope of Change
- Files: `.github/scripts/parity_needed.py` (new), `.github/workflows/ci.yml`, `python/tests/test_parity_needed.py`
  (new)
- Commit: 1db284a

## Secrets, PHI and Claims Scan
All three are clean.

## Findings
### 🔴 Blocking (Critical)
None.

### 🟡 Should fix (Important, non-blocking)
None.

### 🔵 Nits / suggestions (Minor)
- **Imports the scan can't see:** imports built at run time (`importlib`, `sys.path`) aren't followed. The only ones
  in the pipeline load `eval/`, which is always counted as a dependency. The full run on every push to `main` and
  every Monday is the backstop.
- **First run:** the skip is proven only by CI on the next pull request that changes no dependency.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| Test first | ✅ | the decision tests were written first. One wrong assumption was corrected: `readme_results.py` is imported by `36_judge_scorecard.py` |
| Python and R parity | ✅ | parity still runs on every change to its inputs and on `main` |
| Configuration | ✅ | CI only; no settings |

## Test Coverage
`test_parity_needed.py`: 17 passed. Full suite: 753 passed, 15 skipped.

## Verdict
Approve.
