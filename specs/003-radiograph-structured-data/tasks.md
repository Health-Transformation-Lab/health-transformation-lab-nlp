# Tasks: Structured radiograph findings

## Phase 1: Setup
- [x] T001 Ground the error model: vendor bone-level output (CEJ–crest mm per site), CNN bitewing accuracy
- [x] T002 Spec, plan, constitution check

## Phase 2: Tests first
- [x] T003 [P] [US1] reader: RBL → stage I–III, never IV; no bone loss → unknown; no radiograph → unknown
- [x] T004 [P] [US1] simulator: features consistent with chart within noise; bitewing posterior-only; failures flagged
- [x] T005 [P] [US2] fusion rung trains/predicts with and without radiograph features

## Phase 3: US1 + US2 (P1)
- [x] T006 [US1] `radiograph.py`: simulate, features, read, summary
- [x] T007 [US1] study: radiograph per visit; source columns; agreement/coverage include it
- [x] T008 [US2] `fusion_tfidf_rad` rung; models.yaml
- [x] T009 [US1][US2] reliability (Python + R) includes radiograph_ai; dry run

## Phase 4: US3 (P2)
- [x] T010 Label Studio field + decided_by; algorithm v0 priority
- [x] T011 OMOP local concepts and mapping doc

## Phase 5: Later
- [ ] T012 Profile real vendor output (format, noise, failure rate) on approved images; retune simulator
- [ ] T013 BERT fusion (encoder embedding + radiograph features) once BERT rungs run
- [ ] T014 Vendor data agreement / BAA and de-identification of structured exports (no DICOM)
