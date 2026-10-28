---
pr: 115
branch: claude/festive-darwin-er45u9
title: "Classify status from the chart with XGBoost and explain it with SHAP"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: superpowers requesting-code-review subagent + coordinator verification
verdict: approve-with-nits
---

# PR Review: Classify status from the chart with XGBoost and explain it with SHAP

## Summary
Spec 013 G10: `classify_status.py` trains gradient-boosted trees (XGBoost) to predict periodontal status from
the recorded chart. It covers 5-level and 3-level schemes, splits people 80/20, picks hyperparameters by grouped
5-fold cross-validation, and reports one-vs-rest metrics. The model is explained with exact TreeSHAP from
XGBoost itself, and each feature is tagged with its role in the 2017 AAP/EFP rules. The reviewer found no
critical defects. It found one latent crash (a class missing from the training people) and four minor points:
two doc numbers, clashing reference numbers, an out-of-date source line in the spec, and test-first not being
visible in history. The crash and the first three minor points were fixed on the branch with tests. The `check`
job (PR conventions) failed because the description had no issue link; issue #117 was opened and linked.
Verdict: approve-with-nits.

## Scope of Change
- Files changed: 15 code, docs and spec files (+~480 / -2), plus 20 generated files in `data/datasets/classify_status/`
  (CSVs and 4 figures, ~1.2 MB, mostly the per-visit SHAP values)
- Areas touched: python, ci, docs, specs, data
- Commits:
  - `3879ad5` Classify status from the chart with XGBoost and explain it with SHAP
  - (this commit) Guard against a class missing from training; fix doc numbers and reference numbering; review
- Range reviewed: `origin/main (0ec3284)..HEAD`

## CI Status
| Check | Status |
|---|---|
| python | success on `3879ad5` |
| postgres | success on `3879ad5` |
| r-parity | success on `3879ad5` |
| bundle | success on `3879ad5` |
| azure-infra | success on `3879ad5` |
| check (PR conventions) | failure on `3879ad5`: no `Closes #` link; fixed by linking #117 |

## Secrets, PHI and Claims Scan
- Secrets: clean. A pattern scan of the diff found no key, token or credentialed URL.
- PHI / real data: clean. The committed CSVs hold visit ids, class labels and numbers from the synthetic generator.
- Organization claims: clean. The one paper is cited with a DOI, and the docs say that its use of SHAP was
  not checked rather than claiming it.

## Strengths
- SHAP is validated cheaply: a test checks that each visit's SHAP values add up to the model's margin.
- Every feature carries its AAP/EFP role, so the ranking can be checked against the rules. A test asserts it:
  attachment-loss features on top, smoking and diabetes below 10% of the top feature.
- No leakage: people are split before tuning, and GroupKFold runs on training people only.
- No `shap` dependency: XGBoost's built-in TreeSHAP gives the same values.
- The docs are candid about what synthetic data can and can't show, and they report the one unexplained
  pattern (age and stage IV) instead of hiding it.

## Findings
### 🔴 Blocking (Critical)
None.

### 🟡 Should fix (Important, non-blocking)
- **A class missing from training crashed later and unclearly.** `classify_status.py`, `tune` and `train_eval`.
  - XGBoost takes the class count from the labels, not from `num_class`.
  - A missing top class gave 4 probability columns and an IndexError at the metrics loop. A missing middle
    class raised "Invalid classes inferred".
  - Verified by fitting with stage 4, then stage 2, removed. Today's data never triggers it: the smallest
    training fold still has 26 stage-4 visits.
  - **Fixed:** `train_eval` now raises a ValueError naming the missing class. `tune` skips folds whose training
    part lacks a class and reports `cv_folds_used`. Two tests cover these, written first.

### 🔵 Nits / suggestions (Minor)
- **Two doc numbers didn't match the outputs.** `docs/code_walkthrough.md`:
  - Bone loss on `truth_status` is 0.08 at 5 levels and exactly 0 at 3 levels, not "zero".
  - Age's pull away from stage IV is 0.135 for stage IV; 0.05 is the average over all classes.
  - Checked against the committed `*_shap_importance.csv`. **Fixed.**
- **Clashing reference numbers.** `docs/references.md` gave the new references 26 and 27, which already
  belonged to other entries. Renumbered to 51 and 52, after the highest number in use (50). **Fixed.**
- **Spec line out of date.** `spec.md` G10 still said "Patel et al. 2022 (XGBoost + SHAP)". It now names the
  paper and says its use of SHAP was not checked. **Fixed.**
- **Test-first isn't visible in history.** The first commit holds both tests and code. The tests did fail
  first in the session, before the module existed, but git can't show it. Kept as is; the follow-up fix is in
  a separate test-first commit.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets | ✅ | scan clean |
| Synthetic only, no PHI | ✅ | generated outputs only |
| No organization claims; vendors cited | ✅ | Patel 2022 (DOI), Lundberg 2020, Tonetti 2018 |
| Test first | ✅ | 9 tests; history shows one commit for the first round (nit above) |
| Python and R in parity | ✅ n/a | FR-007: model outputs outside label/scoring parity; `r-parity` green |
| Simulated is labelled simulated | ✅ | "SYNTHETIC" in stdout, figure, summary CSV; MLflow `simulated=True`; docs say "not a result" |
| Seeds fixed | ✅ | seeded split, `random_state`, deterministic GroupKFold; same-seed test |
| Paths | ✅ | `DATASETS_DIR` |
| Spec for big changes | ✅ | spec 013 plan.md and tasks.md for G10 |
| Prices | n/a | |
| Commits | ✅ | imperative subjects, bodies say why, co-author trailer |
| Docs | ✅ | process table, walkthrough, references; README unchanged |
| Telemetry `@traced` | ✅ | every public function; the telemetry test passes |
| PR conventions (issue link) | ✅ after fix | `Closes #117` added to the description |

## Test Coverage
`tests/test_classify_status.py` has 9 tests:
- every status maps to a class in both schemes;
- only charted visits with a known status are used, and every feature has a role;
- people are never in both splits;
- metrics and SHAP output shapes;
- SHAP values add up to the margin;
- attachment loss outranks the grade modifiers;
- the same seed gives the same result;
- a missing class raises a clear error;
- tuning skips folds that lack a class.

Run locally:
- `pytest -q tests`: 655 passed, 14 skipped before the fix round;
- `test_classify_status.py`: 9 passed after it;
- `ruff check` on the new files: clean.

The tests skip without xgboost (`importorskip`), but CI's python job installs the `ml` extra, so they run there.

## Verdict
**approve-with-nits.** The important finding and three of the four nits are fixed on the branch. The remaining
nit (test-first visibility in the first commit) doesn't need a change. Merge once CI, including `check`, is
green on the head commit.
