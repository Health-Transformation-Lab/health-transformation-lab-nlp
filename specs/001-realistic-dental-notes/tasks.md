# Tasks: Realistic synthetic dental notes from published examples

**Input**: [spec.md](spec.md), [plan.md](plan.md)

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

- [x] T001 Spec Kit initialized; constitution v1.0.0 ratified
- [x] T002 Pull published diagnosis patterns and statistics (arXiv 2311.10809, 2407.21050) into `docs/note_realism.md`

## Phase 2: Tests first (Superpowers test-driven-development)

- [x] T003 [P] [US2] `test_note_realism.py`: table of catalogue-form sentences → expected status/grade/extent (fails before T006)
- [x] T004 [P] [US1] Catalogue coverage test: every pattern appears in 1,000 `ehr` notes (fails before T007)
- [x] T005 [P] [US3] Diagnosis-presence test: `ehr` notes without a diagnosis line between 0.5% and 3%

## Phase 3: User Story 1 + 2 (P1) 🎯 MVP

- [x] T006 [US2] `note_reader.read_grade`, `read_extent`; broaden `read_stated_dx` (health wording, Roman grades)
- [x] T007 [US1] `dx_patterns.py` catalogue with ids, weights, citations
- [x] T008 [US1] `clinical_notes.py`: `ehr` style using the catalogue; record `dx_pattern`
- [x] T009 [US1] Extent trap ("with generalized recession") in catalogue; reader test

## Phase 4: User Story 3 (P2)

- [x] T010 [US3] Diagnosis-absent share configurable, default 1.5% in `ehr` style

## Phase 5: User Story 4 (P3)

- [x] T011 [US4] `ehr` body: CC, med hx review, perio charting, radiographs, dx, tx, NV; common abbreviations
- [ ] T012 [US4] Clinician plausibility review of 20 notes (manual; owner: dental reviewer)

## Phase 6: Polish

- [x] T013 `study.py`: `ehr` as majority style; `dx_pattern` in answer key
- [x] T014 Rebuild datasets; rerun dry-run pipeline; `pytest`; R parity
- [x] T015 README + `docs/data_sources.md` links; `docs/note_realism.md`
- [ ] T016 Profile a real de-identified note sample (once approved) and retune weights

## Dependencies

T003–T005 before T006–T011. T013 after T008. T014 after all code tasks.
