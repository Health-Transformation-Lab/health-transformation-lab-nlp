---
pr: 256
branch: fix/254-025-hf-token-diagnosis
title: "Say why the Hugging Face token is rejected, without printing it"
author: jcbowyer
reviewed_at: 2026-10-29
reviewer: coordinator (one function, workflow env, three tests)
verdict: approve
---

# PR Review: Hugging Face token diagnosis

## Summary
The token check names the secret it used, trims copy-and-paste wrapping, and says why a value is rejected
without printing it. Verdict: approve.

## Scope of Change
- Commits: 5ac0c6e
- Range reviewed: `origin/main..5ac0c6e`

## Rubric
- **Secrets never printed:** a test passes a recognisable fake value and checks the message holds none of it.
  The source name comes from a workflow expression, not the value.
- **Fails fast, naming the setting:** each message names the secret actually used.
- **Tests first:** the three new tests failed before the change.

## CI Status
| Check | Status |
|---|---|
| python | 1050 passed, 15 skipped locally |
