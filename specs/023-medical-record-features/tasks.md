# Tasks: synthetic medical-record features for the status classifier (spec 023)

Implementation starts after this spec, plan and tasks are reviewed.

## US1 #198: the synthetic visits carry seeded medical-record features

- [ ] T001 [US1] Research: check each candidate source in plan.md against its paper; fill `CONDITIONS` with
  cited numbers only
- [ ] T002 [US1] Failing tests: `test_medical_record.py` (seed, byte-identical rebuild, sources, diabetes =
  HbA1c, odds ratios within tolerance, ranges, column names)
- [ ] T003 [US1] `medical_record.py`: `CONDITIONS`, `draw_medical_record`, own random stream; `@traced`
- [ ] T004 [US1] `study.py` writes the medical record next to the visits; the data card says synthetic

## US2 #199: dental-only, dental+medical and medical-only

- [ ] T005 [US2] Failing tests: `four` scheme, feature sets, stratified split grouped by person
- [ ] T006 [US2] `classify_status.py`: `FEATURE_SETS`, `four`, `split_stratified`, `compare_feature_sets`
- [ ] T007 [US2] `scripts/44_medical_features.py`, writes `synthetic_medical_feature_sets.csv`
- [ ] T008 [US2] Docs: results labelled synthetic, the paper's Table 2 averages cited beside them; PROBAST /
  TRIPOD-AI page

## US3 #200: per-class metrics, the same in R

- [ ] T009 [US3] Failing tests: `class_metrics` on hand-worked cases
- [ ] T010 [US3] `class_metrics` in Python; base-R twin in `r/R/13_spec023.R`; parity input and check
- [ ] T011 Full test suite, `ruff`, R parity; review file for the implementation PR
