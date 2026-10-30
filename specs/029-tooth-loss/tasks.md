# Tasks: tooth lost to periodontitis (spec 029)

Implementation starts after this spec, plan and tasks are reviewed.

## US1 #369: synthetic extract in Open Dental's table format, own bronze schema

- [x] T001 [US1] Check each table and column in plan.md against Open Dental's source schema ([research.md](research.md));
  `TABLES` is written from it in T003
- [ ] T002 [US1] Failing tests: `test_open_dental.py` (seed, unchanged datasets, sources, no truth in the
  extract, rates recovered)
- [ ] T003 [US1] `open_dental.py` generator, own random stream; writes the extract and `tooth_loss_truth.csv`
- [x] T004 [US1] `<layer>_opendental_perio` schemas and the landing volume in `schemas.py` and
  `unity_catalog.yml`; failing schema and bundle tests first (`fact_tooth_loss_prediction` goes in `gold_model.py`
  with the model, T010)

## US2 #370: one silver row per patient and tooth

- [ ] T005 [US2] Failing tests: statuses on hand-built extracts, nothing dated after the loss
- [ ] T006 [US2] `tooth_loss.tooth_table`; base-R twin and parity inputs
- [ ] T006a [US2] Failing tests, then the bronze-to-silver data-quality checks after Kookal et al. 2024
  (completeness, accuracy, consistency; FR-009), with planted faults the generator records
- [ ] T007 [US2] Load job: bronze as is, silver tooth table, idempotent, batch keys

## US3 #371: the model, checked against the hidden truth

- [ ] T008 [US3] Failing tests: feature sets, grouped stratified split, metrics, expected-count stage rule
- [ ] T009 [US3] Logistic regression and XGBoost; scores, calibration and stage recount; R twins for metrics and
  the stage rule
- [ ] T010 [US3] `docs/tooth_loss.md`, results labelled synthetic; gold `fact_tooth_loss_prediction`
- [ ] T011 Full test suite, `ruff`, R parity; review file for each implementation PR
