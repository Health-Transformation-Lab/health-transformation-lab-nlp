# Tasks: spec 018

## US1 - DQ results in gold (#102)
- [x] T001 Failing tests: `grader_tables.dq_tables()` gives every table in the spec with its columns, `sha256` on every row, no note text
- [x] T002 `grader_tables.dq_tables()`; Load results overwrites each `dq_*` table

## US2 - EHR DQ grader dashboard (#103)
- [x] T003 Failing tests: the built dashboard matches the committed JSON; every dataset's SQL runs in DuckDB on the US1 tables; the banner says synthetic; reliability shows as not assessed
- [x] T004 `dashboards.py` builder and `dq_grader()`; `42_build_dashboards.py`; `databricks/resources/dashboards.yml` entry

## US5 (DQ part) - Genie space (#106)
- [x] T005 Failing tests: the space lists only `dq_*` tables, its instructions define each tile's measure and say synthetic
- [x] T006 `databricks/genie/dq_grader.geniespace.json`, `databricks/resources/genie.yml`; CI CLI pin

## US3 - Lab grader tables (#104)
- [ ] T007 Failing tests: the seeded sample is reproducible, every row simulated, `sim:` models, harm in S0–S2, score = covered / key points
- [ ] T008 `43_simulated_grader.py`; `grader_tables.lab_tables()`; Load results writes `grader_*`

## US4 - Lab grader dashboard (#105)
- [ ] T009 Failing tests: SQL runs in DuckDB; no overall rank across categories; access to care first; SIMULATED banner
- [ ] T010 `lab_grader()` in `dashboards.py`; dashboards.yml entry

## US5 (lab part)
- [ ] T011 `databricks/genie/lab_grader.geniespace.json`, tests as T005

## Polish
- [ ] T012 `docs/graders.md` (what each grader shows, how to open the Genie spaces; DQ part done); README link; run the full suite
