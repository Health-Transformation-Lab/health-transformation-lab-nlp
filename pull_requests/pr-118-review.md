---
pr: 118
branch: ci/116-agent-branch-convention
title: "Agent sessions move their work off claude/* branches; CI rejects them"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator review (4 files, a rule and its check)
verdict: approve
---

# PR Review: Agent sessions move their work off claude/* branches

## Summary
- **The rule:** AGENTS.md rule 4 now tells agent sessions to push to `<type>/<issue>-<slug>`, never to their
  assigned `claude/*` branch. Its wording is the owner's standing permission to push elsewhere, which a cloud
  session otherwise lacks.
- **The check:** the CI script rejects `claude/*` with a message that says what to do, and `/create-pr` says the
  same.
- Approve.

## Scope of Change
- Files: `AGENTS.md`, `.claude/commands/create-pr.md`, `.github/scripts/pr_conventions.py`,
  `python/tests/test_pr_conventions.py`
- Commit: e681890

## Secrets, PHI and Claims Scan
Clean.

## Findings
### 🔴 Blocking (Critical)
None.

### 🟡 Should fix (Important, non-blocking)
- **Open PRs from `claude/*` branches** (e.g. #98) fail the check on their next push. This is intended, and the
  PR body says so. Merge them first or move them to a conventional branch.

### 🔵 Nits / suggestions (Minor)
None.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| Test first | ✅ | the rejection test failed before the change |
| Commits | ✅ | imperative subject, body says why, co-author trailer |

## Test Coverage
`test_pr_conventions.py`: 30 passed. Full suite: 648 passed, 14 skipped. The script was also run by hand on both
kinds of branch.

## Verdict
Approve.
