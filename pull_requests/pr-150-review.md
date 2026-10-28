---
pr: 150
branch: chore/127-021-rename
title: "021: rename the project to Health Transformation Lab (merge last)"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator verification
verdict: approve; merge last (after #101 and #108), once the owner has done steps 1-4
---

# PR Review: 021: rename the project to Health Transformation Lab

## Summary
This is a mechanical rename, closing #127. Every changed file was checked to differ from `main`
only by the name substitution. The new files are spec 021 and `test_rename.py`. Data is unchanged.

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
- `pytest -q tests`: 714 passed, 14 skipped. R parity: OK in every section. `ruff check`: clean.
- Scans: no secrets, no PHI.

## Compliance
| Rule | Result |
|---|---|
| Spec for big changes | Pass (spec 021, per the owner's decision on #127; schema names are spec 022's) |
| Test first | Pass (`test_rename.py`) |
| Python/R parity | Pass |
| Configuration | Pass: names are one declaration each (`catalog`, `domain`, `hf_secret_scope` variables) |
| Secrets register | Pass: scope and Azure names updated; no values |
| Branches and issues | Pass (`chore/127-021-rename`, `Closes #127`; replaces #139, opened from `claude/*`) |
