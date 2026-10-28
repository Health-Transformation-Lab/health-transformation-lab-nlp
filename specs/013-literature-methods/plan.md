# Plan: spec 013, G10 (status classifier with SHAP explanations)

Covers FR-007 for G10 only. The other gaps keep their own plans when they are built.

## Source, checked

Patel JS et al., *Developing and testing a prediction model for periodontal disease using machine learning
and big electronic dental record data*, Frontiers in Artificial Intelligence 2022, doi 10.3389/frai.2022.979525:
XGBoost on EDR features, healthy / mild / severe, 80/20 split, 5-fold cross-validation for the
hyperparameters, one-vs-all metrics. Whether it reported SHAP could not be checked from here (the full text
was out of reach), so the docs present SHAP as this repo's choice, not the paper's.

## Design

- **Unit:** charted visits (`visits_structured.csv`, `charted == True`): 3,437 visits of 1,145 people. Without a
  chart the stage features are all missing and the model would only learn "uncharted".
- **Outcome:** `algorithm_design` by default (what a study would have), `truth_status` as the alternative,
  as in `21_predict_progression.py`. Two schemes (spec G10): 5-level (healthy+gingivitis, stage 1-4) and
  3-level (healthy+gingivitis, stage 1-2, stage 3-4).
- **Features:** the recorded chart (max PD, BOP %, max CAL, RBL %, teeth lost to periodontitis, % teeth
  involved), age, smoking (1-9, 10+ a day), diabetes, HbA1c (missing left missing: XGBoost routes it),
  treated before.
- **Split:** people 80/20 by seed (no person in both), as `prediction.py` does 70/30.
- **Tuning:** 5-fold `GroupKFold` by person on the training people over max depth, learning rate, lambda,
  min child weight and class weight (none / balanced); score macro F1. A small grid (fixed, in code).
- **Metrics on the held-out people:** accuracy, macro F1, and per class one-vs-rest AUROC, sensitivity,
  specificity.
- **SHAP:** exact TreeSHAP from XGBoost itself (`pred_contribs=True`, the algorithm of Lundberg et al. 2020
  that the `shap` package uses for trees), on the held-out visits. Outputs mean |SHAP| per feature, overall
  and per class, and the per-visit values. Each feature carries its role in the 2017 AAP/EFP classification
  (Tonetti, Greenwell & Kornman 2018): stage criterion, gingivitis vs healthy (BOP), extent, grade modifier, or
  none. The check on synthetic data: stage criteria should rank first; grade modifiers and "none" low.
- **Dependency:** optional extra `ml = ["xgboost>=2.0"]`; CI's python job installs it. No `shap` package.
- **R:** out of scope (FR-007: model outputs are not part of label/scoring parity).
- **Output:** `data/datasets/classify_status/` (summary, metrics per class, SHAP importance, per-visit SHAP for
  the test set), labelled synthetic. Script `scripts/40_classify_status.py`.

## Files

| File | Change |
|---|---|
| `python/dental_omop_nlp/classify_status.py` | new: features, schemes, train/tune/evaluate, SHAP |
| `python/scripts/40_classify_status.py` | new: run it, write outputs, MLflow `track` |
| `python/tests/test_classify_status.py` | new, written first |
| `python/pyproject.toml`, `.github/workflows/ci.yml` | `ml` extra; CI installs it |
| `docs/references.md`, `docs/process.md`, `docs/code_walkthrough.md` | the paper, where the model sits, how to read SHAP |
