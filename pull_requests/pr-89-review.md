---
pr: 89
branch: claude/great-cerf-qwbqck
title: "Databricks AI features in the AI-use review and the evaluation (spec 017)"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator verification
verdict: approve
---

# PR Review: Databricks AI features in the AI-use review and the evaluation (spec 017)

## Summary
This PR restores the model inventory that missed PR #72's merge and adds a Databricks AI section to it.
It also adds two Databricks-hosted methods to the evaluation, `ai_classify` and the Llama 3.3 70B reader.
Both enter through the existing `ai_predictions_*` path, so scoring code is unchanged and needs no R
change. Neither has run: they bill the workspace and wait for the owner's approval.

## Findings
None blocking. Checked:
- **No note text in SQL.** Every note is a named statement parameter. The only literal is the module's
  own label JSON, with quotes escaped; a test uses a note containing an apostrophe.
- **No answer stays no answer.** NULL, an error or an unknown label becomes a missing prediction, which
  existing scoring counts as no answer. A failed batch is retried once.
- **Llama reader.** It uses the MedGemma reader's prompt, quote gate and fallback, so the two compare
  like for like. Llama is the judge's model family, so its judge scores carry self-preference risk. The
  `models.yaml` comment and the inventory both say so.
- **Unconfirmed until the first live run:**
  - whether a parameter marker or a string literal is needed for `ai_classify`'s labels: the code uses a
    literal, as the docs describe;
  - the exact shape of the v2 response: both v1 and v2 forms are parsed.
- **Simulated results stay separate.** `--simulate` writes only `simulated_*` files, and the results code
  ignores them.

## Checks
- `pytest -q tests`: 609 passed, 12 skipped.
- `ruff check` on the new files: clean.
- Scans: no secrets, no PHI, no organization claims beyond Databricks' own documentation, which is cited.

## Compliance
| Rule | Result |
|---|---|
| Spec for big changes | Pass: `specs/017-databricks-ai-functions/` (spec, plan, tasks); one issue per user story (#86–#88) |
| Test first | Pass |
| Configuration | Pass: settings checked and named before any call |
| Idempotent writes | Pass: a rerun overwrites the method's files |
| Simulated labelled | Pass |
| Python/R parity | n/a: no scoring change |
| Branches and issues | Pass: `claude/*` branch, closes #85–#88 |
