---
pr: 21
branch: claude/awesome-cannon-7xnqm6
title: "Faster dev benchmark, trimmed CI credentials, Node 24 actions, no test warnings"
author: jcbowyer
reviewed_at: 2026-10-27
reviewer: superpowers requesting-code-review subagent + coordinator verification
verdict: approve
---

# PR Review: Faster dev benchmark, trimmed CI credentials, Node 24 actions, no test warnings

## Summary
Turns DistilBERT off in the dev benchmark job (`train_encoder`, on in uat/prod), routes every
workflow's Databricks sign-in through a local action that trims pasted whitespace and masks the
secret, moves checkout and setup-python to Node 24 releases, and removes both Python test
warnings (an XML truth test in the i2b2 loader; a singular fixture in the progression test). No
blocking findings. One verified minor finding (notebook widget default) is fixed on the branch.
Verdict: approve.

## Scope of Change
- Files changed: 14 (+~150 / -~40)
- Areas touched: .github, databricks, python, docs, pull_requests
- Commits:
  - 1bfff4d Skip the DistilBERT rung in the dev benchmark job
  - 5f4c5bf Trim pasted whitespace from Databricks credentials before sign-in; move to Node 24 actions
  - eb0928b Fix the two warnings in the Python test suite
  - 756d3a9 Merge remote-tracking branch 'origin/main'
  - 0087c3c Commit the PR #17 review
  - (next) Default train_encoder off when the notebook runs by hand; add this review
- Range reviewed: `origin/main...HEAD`

## CI Status
| Check | Status |
|---|---|
| python, r-parity, postgres, bundle | running on the pushed head at time of writing |

## Secrets, PHI and Claims Scan
Secrets: clean. PHI / real data: no data files in the branch's own changes. Organization claims: clean.

## Strengths
- One sign-in action replaces three copies of the credential env.
- Structural test: no job env holds raw `DATABRICKS_*`; sign-in precedes every CLI step.
- Behaviour test runs the action's script on `\r\n` values and checks output and mask.
- Fixture comment explains the singular fit; `filterwarnings("error")` keeps both warnings out.

## Findings
### 🔴 Blocking (Critical)
None.
### 🟡 Should fix (Important, non-blocking)
None.
### 🔵 Nits / suggestions (Minor)
- `01_run_benchmark.py:38` widget defaulted to `"true"`, so a hand run in dev trained DistilBERT. Fixed: default `"false"`; uat/prod jobs pass `"true"`.
- `databricks-signin/action.yml` doesn't mask trimmed host/client ID when stored as secrets. Left: neither is a credential.
- PR #17 review commit is unrelated. Left: it is its own commit, following the new reviews-in-git rule.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets | ✅ | |
| Synthetic only, no PHI | ✅ | |
| No organization claims; vendors cited | ✅ | |
| Test first | ✅ | 8 new tests, each failed before its change |
| Python and R in parity | ✅ | model and scoring unchanged; CI r-parity runs |
| Simulated is labelled simulated | n/a | |
| Seeds fixed | ✅ | fixture uses `default_rng(0)` |
| Paths | ✅ | |
| Spec for big changes | n/a | no dataset, metric or label change |
| Prices | n/a | |
| Commits | ✅ | |
| Docs | ✅ | deployment.md updated |

## Test Coverage
`cd python && pytest -q tests`: 298 passed, 12 skipped, 0 warnings. The sign-in action on
GitHub's runners is exercised by the `bundle` CI job.

## Verdict
Approve. Merge when CI is green.
