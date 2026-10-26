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
- [ ] T009b Attach ASQ-PHI (Mendeley Data is blocked from the workspace), confirm its field names, score it
- [ ] T010 Pick the engine on the unseen tier; switch study.py's default; keep a human review sample on real notes
- [x] T011 AI engines: transformer NER (hf_stanford, hf_obi) and LLM (llm) with a verbatim-only rule; LLM token cost in Python and R; Databricks notebook 06_deid_benchmark.py
- [ ] T012 Run the AI engines on Databricks (Hugging Face and serving endpoints are blocked from this workspace) and add their rows to the results
- [x] T013 John Snow Labs engine (`jsl`, clinical_deidentification pipeline) tested with a fake pipeline; i2b2/n2c2 2014 loader (`--i2b2-2014`)
- [ ] T014 Get a John Snow Labs licence (academic or trial) and n2c2 2014 access; run every engine on both
