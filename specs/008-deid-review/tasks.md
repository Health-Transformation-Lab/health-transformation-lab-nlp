# Tasks: Label Studio review flows for de-identification

## Phase 1: Setup
- [x] T001 Spec with the user's clarifications (both flows; engine pre-annotation)

## Phase 2: Tests first
- [x] T002 [P] [US1] gold tasks: predictions in Label Studio format, type mapping, seeded unaided share
- [x] T003 [P] [US1] gold export parsing; agreement F1 (exact span, typed and untyped); consensus spans
- [x] T004 [P] [US2] QA sample (flagged first, seeded); redaction offset map; answer key of true leaks
- [x] T005 [P] [US2] QA export parsing; Wilson CI; reviewer sensitivity/specificity
- [x] T006 [P] [US3] simulated exports are seeded and parse back

## Phase 3: Implementation
- [x] T007 `dental_omop_nlp/deid_review.py`
- [x] T008 `labelstudio/deid_gold.xml`, `labelstudio/deid_qa.xml`; field names match the parser
- [x] T009 `scripts/30_deid_review_tasks.py`, `scripts/31_deid_review_import.py` (`--simulate`)
- [x] T010 R twin (agreement F1, Wilson CI) in `08_deid.R`; parity block; `make_parity_inputs.sh`
- [x] T011 `labelstudio/README.md`, `docs/deid_review_protocol.md`, `docs/deidentification.md`

- [x] T011b Review fixes: consensus counts annotators, not spans; true leaks are surviving runs (no tags,
  no bare titles); `deid.redact` shares `redact_map` (a span nested in another no longer re-emits text);
  seeded gold/QA split with no overlap; real-run outputs gitignored; R twin covers consensus, annotator
  recall, sensitivity, specificity and leak-span recall

## Phase 4: Later
- [ ] T012 First real annotation round on the synthetic challenge set (2+ annotators, 50 notes)
- [ ] T013 Inside the secure environment: QA sample of the chosen engine's output on real notes
