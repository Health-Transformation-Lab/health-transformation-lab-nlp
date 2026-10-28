# Tasks: case profiles and record-mismatch flags (spec 026)

Tests come first in every story (constitution III). Each story is its own branch and PR off `main`:
`feat/234-026-case-profiles`, `feat/235-026-mismatch-rules`, `feat/236-026-recheck-page`. Every output is
synthetic and says so; all wording follows `AGENTS.md` "Words" (`test_wording.py` guards it).

## Phase 1: Setup

- [ ] T001 Create `python/health_transformation_lab_nlp/case_profile.py` with a module docstring (spec 026, synthetic only, KEEPER citation, the Words rule) and an empty `python/tests/test_case_profile.py`
- [ ] T002 Add `python/scripts/45_case_profiles.py` (telemetry setup, `data_label="synthetic"`, reads `DATASETS_DIR / "visits_structured.csv"` and `answer_key/visits_truth.csv`, makes `DATASETS_DIR / "case_profiles"`), and add it to `python/scripts/make_parity_inputs.sh` after `20_data_quality.py`

## Phase 2: Foundational

- [ ] T003 In `python/health_transformation_lab_nlp/case_profile.py`, define `STATUS_RANK` from `plausibility.LABELS` (healthy 0, gingivitis 1, stage I–IV 2–5) and a `_status(value)` helper that returns `None` for `"unknown"` or missing

## Phase 3: US1 #234, a standard case profile for every visit (P1, MVP)

**Goal**: one profile per visit, nine categories, structured values only. **Independent test**: build profiles for the study; every visit has all nine categories, missing values read "not recorded", no note text.

- [ ] T004 [US1] Failing tests in `python/tests/test_case_profile.py`: hand-built visits give all nine categories in order; a visit with no chart shows measurements "not recorded" and the chart as not taken; `"unknown"` statuses read "not recorded"; a patient's last visit reads "no later visit"; the next visit's code and failed plausibility flags appear under "after the visit"; only the note reader's status column (`notes` in `visits_structured.csv`, a status, not text) is read, and no value is longer than a status or measurement (no note text can enter)
- [ ] T005 [US1] `PROFILE_ITEMS` in `python/health_transformation_lab_nlp/case_profile.py`: ordered (category, item, source column, unit) for Demographics (age, clinic), Presentation (`proc_dx_completed`, `proc_dx_planned`, `exam_form`), Visit context (`visit_seq`, `charted`, `treated_before`), Measurements (`rec_max_probing_depth_mm`, `rec_bop_pct`, `rec_max_cal_mm`, `rec_rbl_pct`, `rec_teeth_lost_perio`, `rec_pct_teeth_involved`), Diagnostic tests (`probing_chart`, `radiograph_ai`), Risk factors (`cigarettes_per_day`, `diabetes`, `hba1c`), Treatment (`proc_codes_completed`, `proc_codes_planned`), Other readings (`notes`, the note reader's status, `algorithm_v0`, `algorithm_design`), After the visit
- [ ] T006 [US1] `build_profiles(visits)` (`@traced`) in `python/health_transformation_lab_nlp/case_profile.py`: long frame `visit_id, category, category_order, item, item_order, value_text, value_num`; "After the visit" from the person's next visit by `visit_seq` and `plausibility.check_history` on `proc_dx_completed`
- [ ] T007 [US1] Write `data/datasets/case_profiles/case_profile_item.csv` from `python/scripts/45_case_profiles.py`; test on the built study: 4,343 visits × every category
- [ ] T008 [US1] `grader_tables.dq_tables` adds `fact_case_profile_item` in `python/health_transformation_lab_nlp/grader_tables.py`; gold columns in `python/health_transformation_lab_nlp/gold_names.py` (`category_name`, `category_order_num`, `item_name`, `item_order_num`, `item_value_text`, `item_value_num`); declare it in `diagrams/_build/gold_model.py` ("one per visit, category and item"); extend `python/tests/test_grader_tables.py`
- [ ] T009 [US1] Document the table in `docs/gold_tables.md`; note in `docs/rag_and_vocabulary.md` (R6) that the profile now exists

## Phase 4: US2 #235, record-mismatch flags scored against the truth (P1)

**Goal**: six named rules, each scored for precision, recall and injected errors caught. **Independent test**: one hand-built visit per rule fails exactly that rule; on the study every rule is scored; R gives the same flags and scores.

- [ ] T010 [US2] Failing tests in `python/tests/test_case_profile.py`: one visit per rule fails only it (stage III code with CAL 2 mm and bone loss 10%; gingivitis code with PD 6 mm and BOP 40%; stage II code with no periodontal procedure; healthy code with chart reading stage II; gingivitis code with radiograph stage III; stage III then stage I); no chart gives `not_checkable` for chart rules; no code gives `no_code`; stage-drop flags equal `plausibility.check_history` on the same history; `score_rules` on a hand-worked table gives the expected precision, recall and injected-error counts with not-checkable visits excluded
- [ ] T011 [US2] `RULES` and named thresholds in `python/health_transformation_lab_nlp/case_profile.py`: `HIGH_CODE_MAX_CAL_MM = 3`, `HIGH_CODE_RBL_PCT = 15`, `LOW_CODE_PD_MM = 5`, `LOW_CODE_BOP_PCT = 30`, `CHART_STEPS = 1`, each with its source comment (2017 classification; Patel 2022 Fig. 2 for BOP)
- [ ] T012 [US2] `check_rules(visits)` (`@traced`): one row per (visit, rule), `outcome` in `fail | pass | not_checkable | no_code`, `evidence_text` with the triggering values; the recorded code is `proc_dx_completed`; periodontal care is `proc_codes_completed` or `proc_codes_planned` reading periodontitis
- [ ] T013 [US2] `score_rules(checks, truth, by=None)` (`@traced`): per rule and `any_rule`, overall (`clinic = "All"`) and per clinic: checked, flagged, not checkable, wrong code (`proc_dx_completed != truth_status`), true flags, precision, recall, injected errors (`record_error` non-empty) and caught
- [ ] T014 [US2] Write `record_mismatch.csv` (failed rules only, with clinic and `is_injected_error`) and `mismatch_rule_score.csv` from `python/scripts/45_case_profiles.py`; print the score table headed SYNTHETIC
- [ ] T015 [P] [US2] R twin `r/R/15_spec026.R` (base R): `check_rules`, `score_rules`; source it in `r/tests/test_parity.R` and compare flags exactly and scores to 1e-9 against the CSVs, skipping with a message when they are missing
- [ ] T016 [US2] `grader_tables.dq_tables` adds `fact_record_mismatch` and `mismatch_rule_score`; gold columns (`rule_name`, `rule_label_name`, `mismatch_evidence_text`, `is_injected_error`, `checked_count`, `flagged_count`, `not_checkable_count`, `wrong_code_count`, `true_flag_count`, `precision_ratio`, `recall_ratio`, `injected_error_count`, `injected_caught_count`) in `python/health_transformation_lab_nlp/gold_names.py`; declare both in `diagrams/_build/gold_model.py`; extend `python/tests/test_grader_tables.py`
- [ ] T017 [US2] Results note in `docs/graders.md`: each rule, its threshold and source, and the measured scores labelled "synthetic records, against the generator's truth"

## Phase 5: US3 #236, "Records to recheck" in the DQ grader and its Genie space (P2)

**Goal**: the profile and flags where people already look. **Independent test**: dashboard and Genie files build from code, `--check` passes, the page reads only the three new gold tables.

- [ ] T018 [US3] Failing tests in `python/tests/test_dashboards.py`: the DQ grader has a "Records to recheck" page with a synthetic banner, the rule-score table, the flagged-visit table and a visit-filtered profile table; its datasets read only declared gold tables; the Genie space lists the three tables and its sample questions include a mismatch question
- [ ] T019 [US3] Add the page to `dq_grader()` in `python/health_transformation_lab_nlp/dashboards.py` (banner: "Synthetic records. A mismatch is a coding or charting gap, not a clinical error."; clinic, rule and visit filters)
- [ ] T020 [US3] Extend `DQ_TABLES`, `DQ_INSTRUCTIONS` (the Words rule, the synthetic label, "not checkable" meaning) and `DQ_QUESTIONS` ("Which visits have a stage III–IV code but max CAL under 3 mm?", "Show the profile of visit 1234.", "Which rule has the best precision?") in `python/health_transformation_lab_nlp/dashboards.py`
- [ ] T021 [US3] Rebuild `databricks/dashboards/dq_grader.lvdash.json` and `databricks/genie/dq_grader.geniespace.json` with `python/scripts/42_build_dashboards.py`; describe the page in `docs/graders.md`

## Phase 6: Polish

- [ ] T022 Full checks: `cd python && pytest -q tests`, `ruff check` on changed files, `python/scripts/make_parity_inputs.sh && Rscript r/tests/test_parity.R` where R is available, `python scripts/42_build_dashboards.py --check`
- [ ] T023 Each PR says no environment's settings change and the new gold tables reach dev, uat and prod with the next deploy and Load results; review written to `pull_requests/pr-<n>-review.md`

## Dependencies

- Setup (T001–T002) → Foundational (T003) → US1 (T004–T009).
- US2 needs T003 and the "after the visit" history from T006 only for its stage-drop test; it can start once T006 is merged.
- US3 needs the gold tables from US1 (T008) and US2 (T016).
- Polish runs per PR.

## Parallel opportunities

- T015 (R twin) runs beside T014 once T012–T013 are written.
- T009 and T017 (docs) run beside the code in their story.
- Within US3, T018's dashboard and Genie tests can be written together.

## Implementation strategy

MVP is US1: a profile per visit in gold, usable from Genie's table list before the page exists. Then US2 adds the
flags and scores; US3 puts both on the dashboard. Each story ships as its own PR closing its issue.
