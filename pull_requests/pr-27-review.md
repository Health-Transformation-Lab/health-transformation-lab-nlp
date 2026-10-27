---
pr: 27
branch: claude/awesome-cannon-7xnqm6
title: "Speed up the r-parity rebuild: 3 minutes to 1, identical outputs"
author: jcbowyer
reviewed_at: 2026-10-27
reviewer: superpowers requesting-code-review subagent + coordinator verification
verdict: approve
---

# PR Review: Speed up the r-parity rebuild: 3 minutes to 1, identical outputs

## Summary
Performance-only change to four pipeline steps (site generation, record plausibility, reviewer
agreement bootstrap, judge-calibration bootstrap). The reviewer ran `origin/main` and the branch
side by side: `22_build_sites` and `20_data_quality` outputs are byte-identical (parquets included),
and fuzzing the old vs new reliability and cost-effectiveness functions (None/NaN/pd.NA/numpy str_
labels, empty inputs, NaN gate flags) gave identical results. Three minor findings, all fixed on the
branch. Verdict: approve.

## Scope of Change
- Files changed: 9 code/test files + spec 012 docs (`specs/012-judge-scorecard/`)
- Areas touched: python, specs
- Range reviewed: `origin/main...HEAD`

## CI Status
| Check | Status |
|---|---|
| python, r-parity, postgres, bundle | see PR checks on the pushed head |

## Secrets, PHI and Claims Scan
Secrets: clean. PHI / real data: no data files changed. Organization claims: clean.

## Findings
### 🔴 Blocking (Critical)
None.
### 🟡 Should fix (Important, non-blocking)
None.
### 🔵 Nits / suggestions (Minor)
- `plausibility.check_history` kept visits with NaN `person_id` (the groupby it replaced dropped
  them). Real data has none. Fixed: `dropna(subset=["person_id"])`.
- `22_build_sites` would merge duplicate `visit_id`s in `derive_all`. Unique today. Fixed: assert.
- No equivalence test for `check_history`. Fixed: reference-implementation test on unsorted input
  with NaN persons, exact frame equality.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets / synthetic only / no org claims | ✅ | |
| Test first | ✅ | each fast path guarded by an exact-equality test against the old code |
| Python and R in parity | ✅ | no R change; parity inputs byte-identical |
| Seeds fixed | ✅ | RNG streams unchanged (hash-pinned for draw_mouth) |
| Spec for big changes | n/a | no dataset, metric or label change (spec 012 docs ride along) |
| Commits | ✅ | |

## Test Coverage
`pytest -q tests`: all pass; targeted equivalence tests in test_sites, test_vs_humans,
test_cost_effectiveness, test_longitudinal.

## Verdict
Approve. Merge when CI is green.
