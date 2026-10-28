---
pr: 223
branch: feat/217-025-hf-publish
title: "Spec 025: publish the PerioBench datasets and a quickstart on Hugging Face and Kaggle"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator
verdict: approve
---

# PR Review: Spec 025, publishing on Hugging Face and Kaggle

## Summary
This PR adds Hugging Face publishing that reuses spec 020's file lists and checks, a quickstart notebook for both
platforms, one workflow with a platform choice and an early token check, and the organisation card. Verdict:
approve. The uploads themselves wait on the owner's token (T006) and a workflow run (T007).

## Scope of Change
- Commits: spec 025, then fe764f6 the implementation
- Range reviewed: `origin/main..fe764f6`

## Rubric
- **Synthetic only, nothing external, simulated or partial:** the Hugging Face build calls `kaggle/publish.py`'s
  `check()` and lists, and a test proves `raw/` is exactly that list.
- **Labels:** every card and the notebook say synthetic, not affiliated, not for clinical use; the results card
  calls cost columns illustrative.
- **Configuration (AGENTS.md):**
  - the token is declared once (`HF_PUBLISH_TOKEN`, environment `dev`);
  - it is checked for shape, then with one authenticated call, before any work;
  - it is in the register with scope and owner;
  - its expiry is unknown until it is made.
- **Failures:**
  - Hugging Face API errors raise and fail the step.
  - The quickstart Kaggle run is polled to `complete` or fails the job.
- **Idempotent:** each run is one commit per dataset; files no longer listed are deleted (`.gitattributes` is
  kept).
- **Tests first:** `test_hf_publish.py` and `test_quickstart.py`.
- **Telemetry:** no package function added (the scripts are outside `health_transformation_lab_nlp`).
- **Python/R parity:** not affected.

## Risks
- The token check reads `roleInOrg` and the fine-grained scope from `whoami`. If Hugging Face names these
  differently, the check fails closed with a clear message, and only the check needs changing.
- The notes test split is derived from `review_key.csv` by renaming `truth_*`. A test proves the labels match.

## CI Status
| Check | Status |
|---|---|
| python | 856 passed, 15 skipped locally |
