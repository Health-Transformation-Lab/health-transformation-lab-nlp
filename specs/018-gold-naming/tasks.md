# Tasks: gold naming (spec 018)

- [x] T001 [US1] SQL and data names section in AGENTS.md
- [x] T002 [US1] Test: gold model tables and columns follow the conventions (`test_sql_conventions.py`)
- [x] T003 [US2] Test: `gold_names.to_gold` turns each CSV twin and loader frame into the declared gold columns; unknown columns fail; `from_gold` reverses (`test_gold_names.py`)
- [x] T004 [US2] `gold_names.py`; `gold_model.py` with the new names
- [x] T005 [US2] Notebooks 03, 07, 10 write through `to_gold`; 02 writes `fact_corpus_judge_call`
- [x] T006 [US2] Migration notebook 11 as the first `load_results` task; bundle test
- [x] T007 [US2] Dashboard queries on the new tables; bundle test
- [x] T008 Docs and diagrams regenerated
