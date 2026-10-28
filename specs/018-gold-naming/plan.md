# Plan: gold naming (spec 018)

## Approach

- **Conventions** in AGENTS.md, "SQL and data names" (CLAUDE.md imports it). Adapted from
  jcbowyer/DE_Assessment `docs/shared/conventions.md`; `_usd` and `_seconds` replace its `_amount`, because
  per-chart costs are fractions of a cent, and the durations are seconds from a timer.
- **One mapping**, `python/dental_omop_nlp/gold_names.py`: `TABLES` maps each gold table to the pandas or
  SQL name it was written under and a column rename. `to_gold(df, table)` renames (unknown column: `ValueError`)
  and makes `_count` columns integers; `from_gold` reverses it for the judge resume. Notebooks call it just
  before writing; nothing upstream changes.
- **Declaration** `diagrams/_build/gold_model.py` lists the gold names; tests tie it to `gold_names` and the
  CSV twins, so the ERDs, `data_model.md` and the tables agree.
- **Migration** `databricks/notebooks/11_migrate_gold_names.py`, first task of the `load_results` job (deploy.yml
  starts it after every deploy): for each old table that exists and whose new table doesn't, copy with columns
  renamed and `_count` columns cast to `bigint`; unknown columns fail it. Idempotent: skips once the new table
  exists. Prints `DROP TABLE` statements, runs none.
- **Dashboard** queries read the new tables and alias back to the field names the widgets show.

## Touches

`AGENTS.md`; `python/dental_omop_nlp/gold_names.py`; notebooks 02, 03, 07, 10, new 11;
`databricks/resources/jobs.yml` (load_results tasks); `databricks/dashboards/scorecard.lvdash.json`;
tests `test_gold_names.py`, `test_sql_conventions.py`, `test_gold_model.py`, `test_bundle.py`,
`test_results_store.py`; `diagrams/_build/gold_model.py` and the regenerated diagrams; docs that name the tables.

## Environments

dev changes on merge (CI deploys and starts Load results, which migrates). uat and prod migrate on their next
deploy. No setting or credential changes.
