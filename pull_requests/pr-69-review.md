---
pr: 69
branch: claude/great-cerf-qwbqck
title: "Name branches after the issue for each user story, and link PRs to it"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator (process rule and a small CI check)
verdict: approve
---

# PR Review: Name branches after the issue for each user story, and link PRs to it

## Summary
This PR adds a process rule and a check; no data, metric or label changes. The rule is in `AGENTS.md`, so every
agent reads it, and `CLAUDE.md`, `/create-pr` and the constitution (1.3.0) point to it. A PR check
enforces it. Closes #68.

## Findings
None blocking. Checked:
- **Injection.** The workflow passes the branch and PR body to the script as environment variables, never as
  `${{ }}` inside `run:`. A test enforces this.
- **Agent sessions.** Tool-named `claude/*` branches pass the name check but still need `Closes #<issue>`, so
  agent sessions, which can't rename their assigned branch, can comply.
- **Automated PRs.** `kaggle-results/*` (opened by the Kaggle workflow) and `dependabot/*` need no issue. The
  Kaggle results PR body links its run, not an issue.
- **Spec Kit.** Spec Kit's `NNN-name` branches now fail the name check. The rule says to rename them; the
  Spec Kit scripts are left unchanged so they can still be refreshed from upstream.
- **Old PRs.** PRs opened before this one aren't re-checked: the check runs on PR events only.

## Checks
- `pytest -q tests`: 578 passed, 12 skipped (30 new cases).
- `ruff check`: clean.
- The script was run on a passing and a failing example.
- Scans: no secrets, PHI or organization claims.

## Compliance
| Rule | Result |
|---|---|
| No secrets, synthetic only, no org claims | Pass |
| Test first | Pass |
| Python/R parity | n/a |
| Spec | n/a (process rule; constitution amended with a version bump as its governance section requires) |
| Commits | Pass (`Closes #68`) |
