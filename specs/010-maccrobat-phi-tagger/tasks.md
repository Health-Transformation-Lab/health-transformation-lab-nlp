# Tasks: MACCROBAT PHI tagger

- [ ] T001 [US1] tests then `phi_tagger.words`, `bio_docs`, `split_docs`, `write_conll`
- [ ] T002 [US3] tests then `phi_tagger.entities`, `score` (per type and weighted), `error_kinds`
- [ ] T003 [US4] tests then `phi_tagger.regex_dates` and the named pattern sets
- [ ] T004 [US2] tests then chunking and first-sub-token label alignment; `scripts/33_maccrobat_phi_tagger.py`
- [ ] T005 Task A: baseline run, then a small settings sweep on CPU; record every run
- [ ] T006 Task B: score each regex set on the chosen model's test predictions
- [ ] T007 Task C: final system, weighted F1, error analysis; docs/deidentification.md section
