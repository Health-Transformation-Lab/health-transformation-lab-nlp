# Plan: two graders on Databricks (spec 019)

## Approach
- **Tables (US1, US3):** `dental_omop_nlp/grader_tables.py` turns the committed CSVs into one DataFrame per gold
  table, each with the source files' `sha256`. The Load results notebook (`10_load_results.py`) overwrites each
  table from it on every run. That is idempotent by construction, and the history lives in git.
- **Dashboards (US2, US4):** `dental_omop_nlp/dashboards.py` builds each `.lvdash.json` from Python (datasets,
  counters, bars, tables, a filter, text), so widget wiring isn't hand-edited JSON.
  `python/scripts/42_build_dashboards.py` writes `databricks/dashboards/{dq_grader,lab_grader}.lvdash.json`, with
  `--check` for CI. Datasets read `dental_omop.gold_dental_omop_perio.*`, the same names in every target.
- **SQL tested locally:** tests load the tables from `grader_tables` into DuckDB under the same three-part names
  (an attached `dental_omop` database with a `gold_dental_omop_perio` schema) and run every dataset query. So the
  SQL keeps to what DuckDB and Databricks SQL share: no `QUALIFY`, no Databricks-only functions.
- **Genie (US5):** `databricks/genie/<space>.geniespace.json` (tables, text instructions, sample questions),
  declared in `databricks/resources/genie.yml` with `file_path`. This needs a Databricks CLI with the
  `genie_spaces` resource and the direct engine, which the bundle already uses. Tests check that each space lists
  only tables `grader_tables` writes, and that its instructions name every measure its dashboard shows.
- **Simulated sample (US3):** `43_simulated_grader.py` is seeded. Its rows say `simulated = true` and its models
  are `sim:` names. The dashboard banner and Genie instructions depend on that flag.

## Environments
No new settings. Deploying adds two dashboards, two Genie spaces and the new tables in dev, uat and prod, all
under the existing catalog and schema. CI's Databricks CLI pin moves up for the Genie resource.

## Risks
- The `genie_spaces` resource is new. If validate rejects it on the pinned CLI, the spaces stay as files with a
  documented import step until the pin can move.
- A widget spec the AI/BI editor rewrites on first open: the builder keeps to the widget versions the existing
  scorecard dashboard uses.
