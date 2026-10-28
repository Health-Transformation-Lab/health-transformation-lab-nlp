# Tasks: spec 013

Only G10 is planned so far (plan.md). Test first for each.

## G10: status classifier with SHAP (FR-007)

- [x] T001 `ml` optional extra (xgboost) in `python/pyproject.toml`; CI python job installs it
- [x] T002 Tests: features from charted visits only, people never in both splits, 5- and 3-level schemes map
      every status, metrics and SHAP shapes, SHAP rows sum to the model's margin, stage criteria rank above
      grade modifiers on synthetic charts, seed gives the same result twice
- [x] T003 `classify_status.py`: `features`, `SCHEMES`, `split_people`, `tune`, `train_eval`, `shap_values`,
      `AAP_ROLE`; every public function `@traced`
- [x] T004 `scripts/42_classify_status.py --outcome --scheme --seed`: writes `data/datasets/classify_status/`,
      prints "SYNTHETIC", logs to MLflow
- [x] T005 Run it on both schemes and commit the outputs
- [x] T006 Docs: references (Patel 2022 Frontiers), process table, code walkthrough section on reading SHAP
