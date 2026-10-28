---
pr: 158
branch: fix/154-019-genie-before-tables
title: "Load results before the Genie spaces when their tables don't exist yet"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator (3 files; no subagent needed)
verdict: approve
---

# PR Review: Load results before the Genie spaces when their tables don't exist yet

## Summary
Every dev deploy since #107/#108 failed because the Genie spaces need gold tables that only Load results
writes, and Load results ran after a successful deploy. A new deploy script retries once, after a waited
Load results run, when the Genie spaces are the only failure. Behaviour is tested against a fake CLI.
Verdict: approve.

## Scope of Change
- Files: `.github/scripts/deploy_bundle.sh` (new), `.github/workflows/deploy.yml`, `python/tests/test_results_store.py`
- Range reviewed: `origin/main..HEAD`

## Secrets, PHI and Claims Scan
Clean. The script logs CLI output only; the CLI doesn't print the client secret.

## Repo Rules
| Rule | Status |
|---|---|
| Test first | ✅ the five new tests failed before the script existed |
| Retries explicit, only for failures that pass on their own | ✅ one retry, only for the Genie-tables error |
| Idempotent writes | ✅ Load results overwrites/merges as before; it runs once per deploy (`loaded` output) |

## Findings
🔵 The match is on the error text (`genie_spaces` + `does not exist`). If the CLI rewords it, the
deploy fails as before, so it fails closed.

## Checks run
- `cd python && pytest -q tests`: 750 passed, 15 skipped.
