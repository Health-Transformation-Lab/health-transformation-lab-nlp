# Diagrams

draw.io sources with rendered PNGs, and Mermaid process flows. Gold table reference (every column): [`docs/gold_tables.md`](../docs/gold_tables.md). How they're built: [`_build/render.md`](_build/render.md).

| Diagram | What it shows |
|---|---|
| [**d0 medallion architecture**](d0_medallion_architecture.png) ([.drawio](d0_medallion_architecture.drawio)) | Source → ingest → bronze (PHI zone) → silver (de-identified) → gold (OMOP + dental) → query and process → serve → consumers, on Databricks; same style as the Milliman diagrams |
| [d1 study process](d1_study_process.png) ([.drawio](d1_study_process.drawio)) | Chart notes, exam forms, procedure codes and diagnoses (completed and planned) and the probing chart → comparison, qualitative review, rule-based phenotype, AI, reviewers, acceptance test |
| [d2 platform architecture](d2_platform_architecture.png) ([.drawio](d2_platform_architecture.drawio)) | GitHub CI/CD → one bundle, three environments: jobs, Delta, Lakebase, MLflow, UC model, serving, Label Studio |
| [d3 ERD](d3_erd_omop_dental.png) ([.drawio](d3_erd_omop_dental.drawio)) | OMOP CDM 5.4 tables used, dental extension (SITE, SITE_EVENT), local concepts, perio_chart view |
| [d4 site storage designs](d4_site_storage_designs.png) ([.drawio](d4_site_storage_designs.drawio)) | Post-coordinated vs pre-coordinated vs site columns, with measured joins, time and storage |
| [d5 MLOps lifecycle](d5_mlops_lifecycle.png) ([.drawio](d5_mlops_lifecycle.drawio)) | Train → log → register (challenger) → acceptance test → champion; judge; monitoring |
| [**d6 gold overview**](d6_gold_overview.png) ([.drawio](d6_gold_overview.drawio)) | `gold_dental_omop_perio`: where results come from, the job that writes each of the 9 tables, grain, key, readers |
| [d7 ERD: gold results](d7_erd_gold_results.png) ([.drawio](d7_erd_gold_results.drawio)) | `result_files`, `ai_predictions`, `llm_reader_runs`, every column and type, keys and idempotency (spec 016) |
| [d8 ERD: gold judge scorecard](d8_erd_gold_judge.png) ([.drawio](d8_erd_gold_judge.drawio)) | `chart_answers`, `judgments`, `judge_metrics`, `judge_agreement`, `judge_run`, `deid_scores` (spec 012) |
| [flow 01: run order](flows/01_run_order.png) | Scripts 10–24 and what feeds what |
| [flow 02: review and acceptance](flows/02_review_and_acceptance.png) | Reviewers → human bar vs each method → verdict |
| [flow 03: judge and cost](flows/03_judge_and_cost.png) | Judge bake-off, calibration, corrected accuracy, cost frontier |
