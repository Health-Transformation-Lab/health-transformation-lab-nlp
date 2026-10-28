# Tasks: Databricks AI features in the review and the evaluation

- [x] T001 [US1] Failing test: the inventory lists every AI Function the code calls, and the Databricks section names each feature in the spec
- [x] T002 [US1] Databricks section in `docs/model_inventory.md`
- [x] T003 [US2] Failing tests: label descriptions cover the six statuses; the classify statement uses parameters only; parsing handles v2 VARIANT, v1 string, NULL and errors; a failed batch gives no answer
- [x] T004 [US2] `databricks_ai.py` classify path
- [x] T005 [US3] Failing tests: the query statement uses the reader-v2 prompt; answers go through `parse_answer`; the details columns match the reader's
- [x] T006 [US3] `databricks_ai.py` query path
- [x] T007 Failing tests: the script checks settings, prints the estimate, writes `simulated_*` on `--simulate`, and its names are `dbai-classify` / `dbai-query-<endpoint>`
- [x] T008 `scripts/41_databricks_ai_methods.py`; plain names and group in `readme_results.py`
- [ ] T009 After approval: run both on the 240 review notes; commit the results; refresh the README results
