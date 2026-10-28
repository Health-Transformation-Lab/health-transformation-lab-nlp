---
pr: 139
branch: claude/great-cerf-qwbqck
title: "Rename the project to Health Transformation Lab (spec 019)"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator verification
verdict: approve once the owner has done steps 1-4 (repo rename, catalog, secret scope, Azure)
---

# PR Review: Rename the project to Health Transformation Lab (spec 019)

## Summary
This is a mechanical rename, closing #127. Every one of the 219 changed files was checked to differ from `main`
only by the name substitution. The new files are spec 019 and `test_rename.py`. Data is unchanged.

## Findings
- **Fixed in the branch (dcc13b9): data overwritten by the parity setup.** `make_parity_inputs.sh` rewrote
  committed results while R parity was being checked, and those files were committed. All of `data/` is
  restored to `main`. The script writing committed files when the documented command is run is a hazard
  worth its own issue.
- **Order of operations (not blocking, but required).** Merging before the owner steps would break things:
  - the Kaggle notebook clones the new repo URL;
  - the deploy expects the `health_transformation_lab` catalog to exist;
  - jobs read the new secret scope.

  The PR body lists the steps in order.
- **Old deployment.** The new bundle name means the old deployment's jobs and the `dental_omop` catalog stay
  until they're removed by hand. That's intended: a rebuild, with `prevent_destroy` protecting both catalogs.

## Checks
- `pytest -q tests`: 688 passed, 13 skipped. R parity: OK in every section. `ruff check`: clean.
- Scans: no secrets, no PHI.

## Compliance
| Rule | Result |
|---|---|
| Spec for big changes | Pass (spec 019; 018 was taken) |
| Test first | Pass (`test_rename.py`) |
| Python/R parity | Pass |
| Configuration | Pass: names are one declaration each (`catalog`, `domain`, `hf_secret_scope` variables) |
| Secrets register | Pass: scope and Azure names updated; no values |
| Branches and issues | Pass (`claude/*`, `Closes #127`) |
