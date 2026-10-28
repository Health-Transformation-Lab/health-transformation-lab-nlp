---
pr: 227
branch: docs/224-020-tasks-done
title: "Tick spec 020's Kaggle run tasks, T005 and T007"
author: Claude Code (agent session for jcbowyer)
reviewed_at: 2026-10-28
reviewer: coordinator verification (a two-line checklist change; no reviewer subagent run)
verdict: approve
---

# PR Review: Tick spec 020's Kaggle run tasks, T005 and T007

## Summary
The PR ticks the last two tasks in spec 020's `tasks.md` and names the GitHub Actions run behind each. Both claims
check out. Kaggle's public API shows `perio-bench-notes` and `perio-bench-results` as public under CC BY 4.0, and
`perio-bench-note-classifier` as public with one transformers instance, `modernbert-base-cw`, version 1, under
Apache 2.0. The logs of the two runs show the Kaggle job passing and the model upload ending in "created". The
change is docs only and touches no code, data or settings. Approve.

## Scope of Change
- Files changed: 1 (+2 / -2)
- Areas touched: specs
- Commits: 0861ed3 Tick spec 020's Kaggle run tasks, T005 and T007; bc91497 merge of `origin/main`
- Range reviewed: `ffa5f27..bc91497`

## CI Status
| Check | Status |
|---|---|
| check (PR conventions) | queued when this was written |
| python, postgres, r-parity, bundle | not expected: the change is a `.md` file |

## Secrets, PHI and Claims Scan
- Secrets: clean.
- PHI / real data: clean. No data files.
- Organization claims: clean. The change names only this repo's own Kaggle items and workflow runs.

## Strengths
- Each ticked task names its run ID and date, so anyone can trace the claim.

## Findings
### 🔴 Blocking (Critical)
None.
### 🟡 Should fix (Important, non-blocking)
None.
### 🔵 Nits / suggestions (Minor)
None.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets | Yes | |
| Synthetic only, no PHI | Yes | |
| No organization claims; vendors cited | Yes | |
| Test first | n/a | no behaviour change |
| Python and R in parity | n/a | |
| Simulated is labelled simulated | n/a | no numbers |
| Spec for big changes | n/a | updates an existing spec's tasks |
| Commits | Yes | imperative subject, body says why, co-author trailer |
| Branch and issue | Yes | `docs/224-020-tasks-done`, `Closes #224` |

## Test Coverage
`cd python && python -m pytest -q tests` on the merged branch: 859 passed, 15 skipped. The PR has no ruff or R
parity changes to check.

## Verdict
Approve. It can merge once the PR-conventions check is green.
