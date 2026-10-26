# Tasks: de-identification methods

- [x] T001 Spec; categories from HHS Safe Harbor and the 2014 i2b2/UTHealth guidelines
- [x] T002 [US1] tests then phi_challenge.py: easy / hard / unseen tiers, marked PHI and dental decoys
- [x] T003 [US2] regex_v2, dental guard, "+" ensembles; Azure de-identification and Azure AI Language engines tested with fake clients
- [x] T004 [US3] deid_eval.score_records: entity / char recall, precision, decoy damage, by category
- [x] T005 [US4] engine and review cost, frontier, ICER; R twin 08_deid.R; parity
- [x] T006 26_deid_benchmark.py; Presidio run (Python 3.12 + spaCy); docs/deidentification.md; action item H2
- [ ] T007 Run azure_deid and azure_language (+regex_v2+guard) on the challenge set (needs an Azure resource)
- [ ] T008 Fill real service prices in costs.yaml from the pricing pages
- [x] T009 Second test set: `load_external` + `26_deid_benchmark.py --external` (any labeled JSONL/JSON)
- [x] T009b ASQ-PHI downloaded from Mendeley Data; `load_external` reads its release format; every local engine scored on it, with over-redaction on its hard negatives
- [ ] T010 Pick the engine on the unseen tier; switch study.py's default; keep a human review sample on real notes
- [x] T011 AI engines: transformer NER (hf_stanford, hf_obi) and LLM (llm) with a verbatim-only rule; LLM token cost in Python and R; Databricks notebook 06_deid_benchmark.py
- [x] T012 Run the transformer engines (hf_stanford, hf_obi, alone and with regex_v2+guard) on CPU now that Hugging Face is reachable; rows merged into data/deid, docs updated
- [ ] T012b Run the llm engine (needs a serving endpoint) and score hf_stanford+presidio / hf_stanford+hf_obi ensembles
- [x] T013 John Snow Labs engine (`jsl`, clinical_deidentification pipeline) tested with a fake pipeline; i2b2/n2c2 2014 loader (`--i2b2-2014`)
- [ ] T014 Get a John Snow Labs licence (academic or trial) and n2c2 2014 access; run every engine on both
- [x] T015 Databricks `ai_mask` engine: spans recovered from the masked text, tested with a fake reply; notebook widget for a SQL warehouse; token cost ILLUSTRATIVE
- [ ] T016 Run `ai_mask` (+regex_v2+guard) on the challenge set and ASQ-PHI in a Databricks workspace; fill its token price
