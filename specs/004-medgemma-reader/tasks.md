# Tasks: MedGemma reader

## Phase 1: Setup
- [x] T001 Public model facts (variants, terms, MedGemma 1.5 id); docs/medgemma.md
- [x] T002 Spec, plan, constitution check

## Phase 2: Tests first
- [x] T003 [P] [US1] parse / gate / fallback / PHI pre-check
- [x] T004 [P] [US1] few-shot selection seeded, k per status
- [x] T005 [P] [US2] OpenAI-compatible backend against a local fake server; simulated backend
- [x] T006 [P] [US3] families of evaluated LLM rungs
- [x] T007 [P] [US4] SFT records in the reader format
- [x] T008 judge prompt text unchanged after sharing criteria

## Phase 3: Implementation
- [x] T009 `llm_reader.py`, `judge.CRITERIA`
- [x] T010 `make_rung` + registry fields + MedGemma 1.5 entry
- [x] T011 `11_ai_predict.py` backends; simulated dry run
- [x] T012 costs.yaml entries; `14_benchmark_cost.py` simulated MedGemma
- [x] T013 `15_judge.py` automatic family exclusion
- [x] T014 `17_medgemma_lora.py`; Databricks notebook 03

## Phase 4: Later (needs GPU + HAI-DEF terms accepted)
- [ ] T015 Run 4B zero-shot on the review set (Free Edition serverless GPU); record gate-fail and fallback rates
- [ ] T016 Measure real throughput; replace assumed notes/sec in costs.yaml
- [ ] T017 Two prompt variants: report prompt sensitivity
- [ ] T018 LoRA fine-tune on train.csv; compare with BERT ladder and on the cost frontier
  - [x] T018a Comparison script `29_medgemma_vs_bert.py` (paired CI vs best encoder, by difficulty, fallback, cost), tagged output files per variant, R twin; notebook 03 runs LoRA + comparison. Dry run only so far.
- [ ] T019 27B text via a paid GPU endpoint, if 4B is promising
