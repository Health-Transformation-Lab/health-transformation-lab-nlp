# Tasks: de-identification methods

- [x] T001 Spec; categories from HHS Safe Harbor and the 2014 i2b2/UTHealth guidelines
- [x] T002 [US1] tests then phi_challenge.py: easy / hard / unseen tiers, marked PHI and dental decoys
- [x] T003 [US2] regex_v2, dental guard, "+" ensembles; Azure de-identification and Azure AI Language engines tested with fake clients
- [x] T004 [US3] deid_eval.score_records: entity / char recall, precision, decoy damage, by category
- [x] T005 [US4] engine and review cost, frontier, ICER; R twin 08_deid.R; parity
- [x] T006 26_deid_benchmark.py; Presidio run (Python 3.12 + spaCy); docs/deidentification.md; action item H2
- [ ] T007 Run azure_deid and azure_language (+regex_v2+guard) on the challenge set (needs an Azure resource)
- [ ] T008 Fill real service prices in costs.yaml from the pricing pages
- [ ] T009 Add ASQ-PHI (MIT) as a second test set
- [ ] T010 Pick the engine on the unseen tier; switch study.py's default; keep a human review sample on real notes
