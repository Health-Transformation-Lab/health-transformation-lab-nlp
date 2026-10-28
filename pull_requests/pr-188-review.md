---
pr: 188
branch: fix/187-parity-needed-package-name
title: "Follow the renamed package in the parity check"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator review (two-file rename and one test; no subagent)
verdict: approve
---

# PR Review: Follow the renamed package in the parity check

## Summary
#153 was tested on a base from before the package rename, then merged after it. `main` lost its `python` check,
because the test imports `dental_omop_nlp`. Worse, `parity_needed.py` followed a package path that no longer
exists, so no module counted as a parity dependency. This PR renames both to `health_transformation_lab_nlp` and adds
a test that the package exists and is reached. Approve.

## Scope of Change
- Files changed: 2 (`.github/scripts/parity_needed.py`, `python/tests/test_parity_needed.py`), plus this review
- Commits: 12bed9c Follow the renamed package in the parity check
- Range reviewed: `origin/main..12bed9c`

## CI Status
| Check | Status |
|---|---|
| python, postgres, r-parity, bundle | pending on 12bed9c at the time of writing; r-parity runs in full (the PR changes parity_needed.py) |

## Secrets, PHI and Claims Scan
Clean: a rename and a test, with no data or credentials.

## Findings
None. A search found no other `dental_omop_nlp` in `.github/` or the test.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets / PHI / org claims | ✅ | |
| Test first | ✅ | the new test fails on the old name, since the path doesn't exist |
| Python and R in parity | n/a | CI only |
| Commits | ✅ | |
| Other rows | n/a | |

## Test Coverage
`pytest -q tests`: 796 passed, 15 skipped. `parity_needed.py` runs on the branch and prints `needed=false` for an empty diff.

## Verdict
approve. Merge once CI is green.
