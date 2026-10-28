---
pr: 165
branch: fix/164-genie-moved-spaces
title: "Approve the main bundle's Genie space deletions after the move"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator (two files, workflow plus tests)
verdict: approve
---

# PR Review: Approve the main bundle's Genie space deletions after the move

## Summary
The dev deploy stopped because the main bundle planned to delete the two Genie spaces that #157 moved to their
own bundle. The Deploy step now approves a destructive plan only when every action in it is a Genie space. The
Genie step recreates the spaces in the same run, and anything else still fails. #156's retry path can no longer
fire, so it is removed. Verdict: approve.

## Scope of Change
- Files changed: 2 (`.github/workflows/deploy.yml`, `python/tests/test_results_store.py`)
- Commits:
  - 74b7941 Approve the main bundle's Genie space deletions after the move
- Range reviewed: `origin/main..74b7941`

## Rubric
- Failures fail at once, with the reason: yes. Any other destructive plan exits 1 without approving.
- Idempotent: after the one-time removal, the main bundle plans no deletes, so the branch doesn't fire again.
- Tests first: the Genie-only case failed before the change; the tests run the real step script.
- Secrets: none touched.
- Python/R parity: not affected.

## Risks
- `--auto-approve` covers the whole second deploy. It runs from the same checkout as the plan just checked, so
  the plan can't change between the two calls.
- The spaces get new IDs, and their conversations are lost (created today).

## CI Status
| Check | Status |
|---|---|
| python | 750 passed, 15 skipped locally |
| deploy | runs after merge |
