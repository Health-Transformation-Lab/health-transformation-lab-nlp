---
pr: 186
branch: feat/185-004-medgemma-v1-kaggle
title: "Run MedGemma 4B v1 on Kaggle next to MedGemma 1.5"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator review after merge (issue #196)
verdict: approve
---

# PR Review: Run MedGemma 4B v1 on Kaggle next to MedGemma 1.5

## Summary
This PR lets the Kaggle MedGemma notebook run MedGemma 4B v1 (`medgemma-4b-it`), the like-for-like comparison with
1.5 that #93 asked for. Three changes do it:
- `models.yaml` gives v1 its Kaggle Models handle.
- Google's `config.json` and `generation_config.json` at the pinned revision ship next to 1.5's.
- `keras_to_hf.compatible_preset` reads v1's older Keras preset. That preset names a tokenizer setting
  `is_vision_model`, which keras-hub 0.32 calls `has_vision_tokens`.

It took three 10-note Kaggle tests. The first two failed at conversion: first the old setting name, then keras-hub
refusing a `Path`. Each failure was fixed with a test. The third test read 10 of 10 notes and passed the gate on all
10. This review was written after the merge (the PR merged without one; #196). Approve.

## Scope of Change
- Files changed: 5 (+175 / -4)
- Areas touched: kaggle, python tests, models.yaml
- Commits:
  - 4f195a5 Run MedGemma 4B v1 on Kaggle next to MedGemma 1.5
  - 1c65e9c Read MedGemma 4B v1's older Keras preset
  - ec589d1 Pass keras-hub the preset folder as a string
- Range reviewed: `6b744b3..ec589d1`

## CI Status
| Check | Status |
|---|---|
| python, pr-conventions | green on ec589d1 (merged 2026-10-28 21:07 UTC) |
| r-parity | not needed: no label, scoring or reliability change |

## Kaggle tests (*MedGemma on Kaggle*, rung `medgemma-4b-it`, `limit` 10, `open_pr` off)
| Run | Commit | Ended | Cause |
|---|---|---|---|
| [11](https://github.com/healthtransformationlab/health-transformation-lab-nlp/actions/runs/40764582259) | 4f195a5 | failure | keras-hub 0.32 refused v1's tokenizer config (`is_vision_model`) |
| [12](https://github.com/healthtransformationlab/health-transformation-lab-nlp/actions/runs/40765747758) | 1c65e9c | failure | `from_preset` refused the `Path` that `compatible_preset` returns ("A preset identifier must be a string") |
| [13](https://github.com/healthtransformationlab/health-transformation-lab-nlp/actions/runs/40767325789) | ec589d1 | success | 10 of 10 notes read, 100% gate pass (as reported by the run; its artifact could not be re-downloaded from this review's container) |

These are 10-note smoke tests, not results. The 240-note run
([14](https://github.com/healthtransformationlab/health-transformation-lab-nlp/actions/runs/40769250182), from `main`)
opens its own results PR.

## Secrets, PHI and Claims Scan
Clean.
- No credentials: v1 is read from Kaggle Models, so no Hugging Face token is needed.
- No notes or patient data.
- The two config files are Google's public model metadata, byte for byte at the pinned revision `290cda5…`. Their
  licence (HAI-DEF terms) is already recorded in `models.yaml`.

## Strengths
- `compatible_preset` never changes the attached input. It writes renamed JSON configs to a work folder and links
  the 17 GB of weights instead of copying them. A current preset (1.5) is returned unchanged, and a test covers it.
- The renaming is one table (`RENAMED`), so a later keras-hub rename is a one-line change.
- The "refused" test still covers a rung without a Kaggle handle, now the 27B text model.
- Google's config is shipped, not the exporter's: transformers 4.x then reads v1's linear rope scaling (×8), as
  it does for 1.5.

## Findings
### 🔴 Blocking (Critical)
None.

### 🟡 Should fix (Important, non-blocking)
None.

### 🔵 Nits / suggestions (Minor)
- `compatible_preset` looks for the old names by substring over each top-level JSON file. A value containing
  `is_vision_model` would also trigger the copy. The copy is harmless (only keys are renamed), so it stays as it is.
- Only top-level `*.json` files are rewritten. That is all v1's preset has, and the test mirrors its layout.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets / PHI / org claims | ✅ | |
| Test first | ✅ | each failure has a test: v1 handle and configs, older preset renamed, current preset unchanged |
| Python and R in parity | n/a | no scoring change |
| Simulated is labelled simulated | ✅ | no numbers presented; the 10-note tests are smoke tests |
| Configuration | ✅ | no settings or environments change |
| Secrets register | ✅ | no credential; removes the need for one |
| Commits | ✅ | imperative subjects, bodies say why, co-author trailers |
| Other rows | n/a | |

## Test Coverage
`cd python && pytest -q tests`: 763 passed, 15 skipped on the branch (from the PR). On today's `main`, 835 passed
and 15 were skipped. The conversion itself (`convert`) needs the weights and is exercised only on Kaggle (run 13).

## Verdict
approve. Already merged; nothing to follow up beyond the 240-note run's results PR.
