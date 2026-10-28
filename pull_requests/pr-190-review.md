---
pr: 190
branch: feat/189-016-catch-up
title: "Catch Databricks up by itself after an outage"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: superpowers requesting-code-review subagent + coordinator verification
verdict: approve-with-nits
---

# PR Review: Catch Databricks up by itself after an outage

## Summary
A scheduled workflow (`catch-up.yml`) runs `catch_up.py` every 3 hours for each target. It waits out a Databricks
outage, escalates after 24 hours or on a refused credential or bad host, re-runs the target's failed deploy job once
Databricks answers, and runs Load results when the deployed commit has no successful load. The first review found
two Important problems: the shared concurrency group could cancel a queued deploy, and a long outage after a good
deploy never escalated. Both are fixed in bf58f47, with four of the minor findings. Approve with nits.

## Scope of Change
- Files: `.github/scripts/catch_up.py`, `.github/workflows/catch-up.yml`, `python/tests/test_catch_up.py` (new);
  `docs/operations.md`, `docs/results_storage.md`
- Commits:
  - 261348d Catch Databricks up by itself after an outage
  - f5814f4 Merge origin/main
  - bf58f47 Escalate a long outage, and never cancel a queued deploy
- Range reviewed: `origin/main..bf58f47`

## CI Status
| Check | Status |
|---|---|
| python, postgres, r-parity, bundle | pending on bf58f47 at the time of writing |

## Secrets, PHI and Claims Scan
Clean. No credentials in the diff: the client secret comes from the GitHub environment and is masked by the sign-in
action, and `GITHUB_TOKEN` is used only within the run. No data is touched.

## Strengths
- The decision is a pure function with a test for every branch. The CLIs are only read and parsed around it.
- Every alert has a severity, an owner (GitHub's failed-run email) and an action.
- Safe to repeat: Load results is keyed by SHA-256, and only the newest deploy run (by API ordering) is ever re-run.

## Findings
### 🔴 Blocking (Critical)
None.

### 🟡 Should fix (Important, non-blocking)
- **Fixed in bf58f47.** `catch-up.yml` concurrency: the group `deploy-<target>` would cancel a deploy waiting in it.
  It now uses `catch-up-<target>`, and `decide` does nothing while the target's deploy is queued or running.
- **Fixed in bf58f47.** `catch_up.py`, `decide`: unreachable after a good deploy stayed SEV3 forever. When
  Databricks last answered is kept in the Actions cache; 24 hours without an answer is SEV2 whatever the deploy did.
  `DATABRICKS_HOST` is checked before any work.

### 🔵 Nits / suggestions (Minor)
- **Fixed.** dev and uat could re-run the same run. Each now re-runs only its own job (`gh run rerun --job`), and a refused re-run waits for the next check.
- **Fixed.** A `gh` or CLI error ended in a traceback. It now ends with a SEV3 message and an action.
- **Fixed.** The "keeps failing" message now also allows for Databricks flapping. A Load results run SKIPPED because another is loading is not a failure.
- **Kept.** A persistent SEV2 fails every 3-hour run, so the owner gets repeated emails until it's fixed. That keeps it visible; per AGENTS.md, a SEV2 that repeats gets its cause fixed.
- **Kept.** Each scheduled run adds entries to the GitHub environments' deployment history. It's cosmetic, and needed for the environment secrets.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets / PHI / org claims | ✅ | |
| Test first | ✅ | `test_catch_up.py` written with the code, 30 tests |
| Configuration | ✅ | no new settings; host and credential checked before work |
| Secrets register | ✅ | no new credential |
| Idempotent writes | ✅ | no table writes; Load results is SHA-keyed |
| Alerts | ✅ | severity, owner (failed-run email), action on every message |
| Commits / Docs | ✅ | |
| Other rows | n/a | |

## Test Coverage
`pytest -q tests`: 826 passed, 15 skipped. The fake-CLI end-to-end runs covered:
- down after a failed deploy (SEV3);
- 30 hours down after a failed or a good deploy (SEV2);
- a refused secret (SEV2);
- recovered, with a re-run by job id;
- never loaded, so Load results runs;
- already loaded;
- a malformed host.

Not run: against real Databricks and GitHub. The first scheduled run on `main` will exercise the CLI shapes, and a
mismatch ends with a SEV3 "could not check".

## Verdict
approve-with-nits. Merge once CI is green.
