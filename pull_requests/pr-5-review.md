---
pr: 5
branch: ccr-5ad3b6f0-n31g16
title: "BERT ladder results, JSL and Microsoft pricing, /create-pr and /pr-review"
author: jcbowyer
reviewed_at: 2026-10-26
reviewer: read-only reviewer subagent (Superpowers not installed in this session) + coordinator verification
verdict: approve (after d4b660d)
---

# PR Review: BERT ladder results, JSL and Microsoft pricing, /create-pr and /pr-review

## Summary
Adds six CPU-trained encoder results, checkpoint/resume for fine-tuning, a licensed cost kind
(John Snow Labs from the vendor's own example), a Microsoft PHI-options price/quality table, and
the /create-pr and /pr-review commands. One critical defect was found and verified (a finished
run's checkpoint was resumed by the next fit); fixed in d4b660d with tests, along with two minor
items. Approve once CI is green on d4b660d.

## Scope of Change
- Files changed: 26 at review (+1,518 / −11, mostly prediction CSVs and docs)
- Areas touched: python (rungs, deid_eval, benchmark script, tests), r (08_deid.R, test_parity.R),
  costs.yaml, docs, specs/007, .claude (commands, rubric), data (predictions, simulated reliability)
- Range reviewed: `origin/main..HEAD` at 2026-10-26 12:17

## CI Status
| Check | Status |
|---|---|
| python, postgres, r-parity, bundle | pending on d4b660d |

## Secrets, PHI and Claims Scan
Clean: no credentials, no `data/raw` files or real notes; vendor figures cite their sources.

## Strengths
- Cost model reproduces the vendor's own $2,418 example; prices cite vendor sources.
- Simulated-reviewer agreement is labelled as a dry run throughout.

## Findings
### 🔴 Blocking (Critical)
- **rungs.py: a finished run's checkpoint was resumed.** Verified: transformers 5.20
  `DefaultFlowCallback.on_step_end` saves at `global_step >= max_steps` with `save_strategy=steps`,
  and `output_dir` depends only on the model id, so the next `fit` (03_run_ladder after
  11_ai_predict, another label or seed) trained zero steps and predicted with old weights.
  **Fixed (d4b660d):** `_clear_checkpoints` after `train()`; test added.

### 🟡 Should fix (Important, non-blocking)
- None.

### 🔵 Nits / suggestions (Minor)
- `_last_checkpoint` could pick a half-written checkpoint. **Fixed:** requires `trainer_state.json`.
- NaN `prorate_license`: Python prorated, R errored. **Fixed:** both treat missing as whole months.
- R licensed branch never exercised by parity. **Fixed:** test_parity.R 9b checks it against
  Python's values.
- The committed `cost_inputs.csv` predates the licence columns; harmless (R falls back, CI regenerates).

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets | ✅ | scan clean |
| Synthetic only, no PHI | ✅ | data/raw untouched; JSL notes stay out of the repo |
| No organization claims; vendors cited | ✅ | JSL example labelled the vendor's own |
| Test first | ✅ | failing tests written before each fix |
| Python and R in parity | ✅ | R twin updated; 9b adds a direct check (CI r-parity) |
| Simulated labelled simulated | ✅ | dry-run agreement labelled |
| Seeds, paths | ✅ | no new generators; paths unchanged |
| Spec for big changes | ✅ | specs/007 T019 added |
| Prices | ✅ | sources and dates in costs.yaml |
| Commits | ✅ | imperative, why, co-author |

## Test Coverage
`pytest -q tests`: 216 passed, 12 skipped. R not installed locally; CI r-parity runs 9b.

## Verdict
Approve after d4b660d, once CI is green.
