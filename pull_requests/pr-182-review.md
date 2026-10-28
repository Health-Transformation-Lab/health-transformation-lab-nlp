---
pr: 182
branch: feat/122-020-kaggle-model
title: "Publish the class-weighted ModernBERT-base classifier as a Kaggle model"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: superpowers requesting-code-review subagent + coordinator verification
verdict: approve-with-nits
---

# PR Review: Publish the class-weighted ModernBERT-base classifier as a Kaggle model

## Summary
Spec 020 US3 (#122). The encoder notebook can now keep one rung's fine-tuned weights (`SAVE_MODEL`, through
`11_ai_predict.py --save-model`). `kaggle/publish_model.py` builds a public, Apache 2.0, transformers Kaggle model
from them. The card is scored by `ladder_eval` from the same run's review-set predictions, and the encoder workflow
publishes after a full run. The first review asked for changes on two points: later versions kept the first run's
card, and the card named the workflow run's commit rather than the one the notebook trained. Both are fixed in
99741e8, along with the minor findings, so the verdict is approve-with-nits. A real training run and upload on
Kaggle is left for the owner (spec task T007).

## Scope of Change
- Files changed: 11 (4 new: `kaggle/publish_model.py`, `kaggle/cards/model.md`, `python/tests/test_kaggle_model.py`,
  this review)
- Areas touched: python, kaggle, workflow, docs, specs
- Commits:
  - 2d0f9f9 Publish the class-weighted ModernBERT-base classifier as a Kaggle model
  - 99741e8 Refresh the model card on each version and name the trained commit
- Range reviewed: `origin/main...99741e8`

## CI Status
| Check | Status |
|---|---|
| python | pending on 99741e8 at the time of writing |
| postgres | pending |
| r-parity | pending (no labels, scoring, reliability or cost-effectiveness change) |
| bundle | pending |

## Secrets, PHI and Claims Scan
- Secrets: clean. The Kaggle token is read from the environment only, and the workflow keeps the existing `dev` secrets.
- PHI / real data: clean. The card says synthetic, not clinical performance, not for clinical use. Simulated predictions are refused.
- Organization claims: clean. The card says "not affiliated with any employer"; the base model and its licence are linked.

## Strengths
- The card uses the leaderboard's own scoring. Verified: the committed `ai_predictions_modernbert-base+cw.csv` gives
  83.8 (79.6–88.3), 14.6 unsafe errors, 21% stage IV and 89 / 68 / 81 by difficulty, matching `docs/results.md`.
- Refusals are layered: a partial or `simulated_` prediction file, `sim:`/`calib:` rows, the wrong labels or no weights, and a
  test run's `saved_model.json` in the workflow.
- The Kaggle calls match the installed `kaggle==2.2.5` signatures. Its enum lookup and slug checks accept the metadata.

## Findings
### 🔴 Blocking (Critical)
None.

### 🟡 Should fix (Important, non-blocking)
- **Fixed in 99741e8.** `kaggle/publish_model.py`, `upload`:
  - `model_instance_version_create` sends files and version notes only, so a second publish would have served new weights under the first run's scores.
  - It now calls `model_update` and `model_instance_update` before versioning. `test_upload_creates_the_model_and_instance_then_versions` covers it.
- **Fixed in 99741e8.** `.github/workflows/kaggle-encoders.yml`:
  - `--commit "${{ github.sha }}"` named the collecting run's commit, which is wrong for `collect_only` or another `branch`.
  - The notebook now writes `git rev-parse HEAD` into `saved_model.json`, and the workflow passes that value instead (tested).

### 🔵 Nits / suggestions (Minor)
- **Fixed.** The card's "top fine-tuned encoder" claim rested on overlapping CIs; it was removed.
- **Fixed.** "240" was hard-coded in the card; it now uses `len(key)`.
- **Fixed.** The wait loop (330 min) left little of the 350-minute job for publishing. It is now 315 of 360.
- **Fixed.** The README now says how to collect a long run later (`collect_only` with the same `save_model`, `limit` 0).
- **Fixed.** `saved_model.json["full_run"]` is now checked by the workflow, which refuses a test run's weights.
- **Kept.** `${{ inputs.save_model }}` is interpolated into the prepare step as the other inputs already are. Only someone who can start the workflow can set it.
- **Kept.** The ruff I001 under `python/`'s config matches the existing `kaggle/record_results.py`; the root config passes.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets | ✅ | scan clean |
| Synthetic only, no PHI | ✅ | card labelled; simulated refused |
| No organization claims; vendors cited | ✅ | |
| Test first | ✅ | `test_kaggle_model.py` written before the code |
| Python and R in parity | n/a | no scoring change |
| Simulated is labelled simulated | ✅ | `simulated_`, `sim:` and `calib:` refused |
| Seeds fixed | n/a | |
| Paths | ✅ | `DATASETS_DIR` |
| Spec for big changes | ✅ | spec 020 US3; T006 done, T007 (the run) added |
| Prices | n/a | |
| Commits | ✅ | |
| Docs | ✅ | `kaggle/README.md` |
| Configuration | ✅ | `save_model` is one workflow input, default empty; no environment changes |
| Secrets register | ✅ | reuses the existing Kaggle token |
| Idempotent writes | ✅ | the build is rmtree-then-write; upload is create, or update then version |
| Alerts | n/a | |
| Telemetry | ✅ | `HFEncoder.save` is `@traced` |

## Test Coverage
`tests/test_kaggle_model.py` covers:
- `HFEncoder.save`;
- the script flag, the notebook setting and the `+cw` handling, and the prepared kernel;
- the built folder and metadata;
- the card's scores, synthetic label and commit;
- the refusals;
- create, update and version on upload;
- the workflow step's guards and the artifact exclusion.

Run locally: `pytest -q tests` gave 775 passed, 15 skipped. A real save and reload with transformers on CPU (tiny BERT)
fed `publish_model.py`, and the workflow's shell guard was run on sample `saved_model.json` files. Not run: training
and uploading on Kaggle (no credentials here; T007).

## Verdict
approve-with-nits. Both Important findings are fixed on the branch. Merge once CI is green on 99741e8, then run T007.
