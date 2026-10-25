# Diagrams

draw.io sources with rendered PNGs, and Mermaid process flows. How they're built: [`_build/render.md`](_build/render.md).

| Diagram | What it shows |
|---|---|
| [d1 study process](d1_study_process.png) ([.drawio](d1_study_process.drawio)) | Chart notes, exam forms, procedure codes and diagnoses (completed and planned) and the probing chart → comparison, qualitative review, rule-based phenotype, AI, reviewers, acceptance test |
| [d2 platform architecture](d2_platform_architecture.png) ([.drawio](d2_platform_architecture.drawio)) | GitHub CI/CD → one bundle, three environments: jobs, Delta, Lakebase, MLflow, UC model, serving, Label Studio |
| [d3 ERD](d3_erd_omop_dental.png) ([.drawio](d3_erd_omop_dental.drawio)) | OMOP CDM 5.4 tables used, dental extension (SITE, SITE_EVENT), local concepts, perio_chart view |
| [d4 site storage designs](d4_site_storage_designs.png) ([.drawio](d4_site_storage_designs.drawio)) | Post-coordinated vs pre-coordinated vs site columns, with measured joins, time and storage |
| [d5 MLOps lifecycle](d5_mlops_lifecycle.png) ([.drawio](d5_mlops_lifecycle.drawio)) | Train → log → register (challenger) → acceptance test → champion; judge; monitoring |
| [flow 01: run order](flows/01_run_order.png) | Scripts 10–24 and what feeds what |
| [flow 02: review and acceptance](flows/02_review_and_acceptance.png) | Reviewers → human bar vs each method → verdict |
| [flow 03: judge and cost](flows/03_judge_and_cost.png) | Judge bake-off, calibration, corrected accuracy, cost frontier |
