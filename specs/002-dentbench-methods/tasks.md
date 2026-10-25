# Tasks: Reuse GlobalDentBench evaluation methods

## Phase 1: Setup

- [x] T001 Read GlobalDentBench methods (arXiv 2605.24636); map to this study (spec Context table)
- [x] T002 Draft severity matrix and difficulty definitions in `docs/dentbench_methods.md`

## Phase 2: Tests first

- [x] T003 [P] [US1] `test_dentbench_methods.py`: severity acceptance scenarios
- [x] T004 [P] [US2] difficulty assignment tests (L1/L2/L3 cases)
- [x] T005 [P] [US3] bake-off picks the best-calibrated judge; kappa CI present

## Phase 3: US1 + US2 (P1)

- [x] T006 [US1] `harm.py`; unsafe_rate, s2_rate in `reliability_report`
- [x] T007 [US2] `difficulty` in study build and answer key; by-level agreement table
- [x] T008 [US1][US2] R twins in `04_reliability.R`; parity test extended

## Phase 4: US3 (P2)

- [x] T009 [US3] Judge candidates + bake-off in `15_judge.py`; kappa + bootstrap CI; same-family flag
- [x] T010 [US3] `16_cost_effectiveness.py` uses the selected judge

## Phase 5: Later

- [ ] T011 Component verdicts (status, grade, extent judged separately), after the grade/extent readers are validated
- [ ] T012 Periodontist sign-off on the severity matrix (owner: dental reviewer)
- [ ] T013 Dentist acceptance check on a sample of judge verdicts (GlobalDentBench-style), alongside kappa

## Phase 6: Polish

- [x] T014 `docs/references.md`; README links; rebuild; dry run; parity
