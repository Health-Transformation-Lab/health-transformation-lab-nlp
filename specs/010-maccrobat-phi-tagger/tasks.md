# Tasks: MACCROBAT PHI tagger

- [x] T001 [US1] tests then `phi_tagger.words`, `bio_docs`, `split_docs`, `write_conll`
- [x] T002 [US3] tests then `phi_tagger.entities`, `score` (per type and weighted), `error_kinds`
- [x] T003 [US4] tests then `phi_tagger.regex_dates` and the named pattern sets
- [x] T004 [US2] tests then chunking and first-sub-token label alignment; `scripts/33_maccrobat_phi_tagger.py`
- [x] T005 Task A: baseline run, then a small settings sweep on CPU; record every run
- [x] T006 Task B: score each regex set on the chosen model's test predictions
- [x] T007 Task C: final system, weighted F1, error analysis; docs/deidentification.md section
- [ ] T008 Score MACCROBAT `Time` with Date (or map it); trailing-only trim rule from the training annotations; year pattern; check on a new split
- [ ] T009 Cross-validation over the 160 training notes instead of one 20-note validation set; batch size, 512+ word chunks, other seeds (needs a GPU)
