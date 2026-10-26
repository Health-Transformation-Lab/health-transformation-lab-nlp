# Deploying to dev, UAT and prod (Databricks Asset Bundle)

`databricks.yml` at the repo root defines the bundle; jobs live in
`databricks/resources/jobs.yml`. One set of code, three targets, settings as
variables.

> Synthetic data only in every target until the real-data path is approved.
> Personal learning project; see [DISCLAIMER](../DISCLAIMER.md).

## Targets

| | dev | uat | prod |
|---|---|---|---|
| Purpose | your sandbox (e.g. Free Edition) | shared test | production |
| Bundle mode | `development` (resources prefixed `[dev <you>]`, schedules paused) | `production` | `production` |
| Deployed by | you, from your laptop | CI on push to `main`, or on demand | CI on demand, after approval |
| Runs as | you | service principal | service principal |
| Workspace path | your home folder | `/Workspace/Shared/.bundle/dental-omop-nlp/uat` | `.../prod` |
| Workspace | your dev workspace | the UAT workspace | the prod workspace |
| Catalog | `dental_omop` (schemas below) | same | same |
| `n_people` | 300 | 1,500 | 1,500 |
| MedGemma GPU job | no (run notebook 03 on serverless GPU) | yes, single-node GPU cluster | yes, all review notes |

Each target is its own workspace (its own `DATABRICKS_HOST`), so catalog and
schema names are the same everywhere. One catalog, one schema per layer:

| Schema in `dental_omop` | Holds |
|---|---|
| `landing_dental_omop_perio` | the `data` volume: files the pipeline writes (`DENTAL_DATA_ROOT`) |
| `bronze_dental_omop_perio` | raw tables (empty for now) |
| `silver_dental_omop_perio` | cleaned tables (empty for now) |
| `gold_dental_omop_perio` | OMOP and study tables, `benchmark_results`, `judgments`, `llm_reader_runs`, `perio_note_classifier` |

The bundle creates the catalog, all four schemas and the volume on deploy
(`databricks/resources/unity_catalog.yml`), each with `prevent_destroy` so
`bundle destroy` never drops them. Deploying needs Databricks CLI 0.288 or later
and `CREATE CATALOG` on the metastore. (The old `dental_uat` / `dental_prod`
catalogs were placeholders the bundle never created; you had to make them by hand.)

In dev (`mode: development`) Databricks prefixes Unity Catalog resources with
`dev_<user short name>_` instead of `[dev <you>]`: the catalog, schemas, volume
and registered model all get it, and the jobs follow because they reference the
resources rather than the `catalog`/`domain` variables. Deployed
from CI by the service principal, `<you>` is the principal's short name (e.g.
`dev_dental_omop_ci_perio_note_classifier`). uat and prod have no prefix.

## Variables

| Variable | Default | What it sets |
|---|---|---|
| `catalog`, `domain` | `dental_omop`, `dental_omop_perio` | the catalog, and the suffix of the `landing_`/`bronze_`/`silver_`/`gold_` schemas |
| `n_people` | `300` | synthetic people in the benchmark job |
| `judge_endpoint` | `none` | Model Serving endpoint for `ai_query` (notebook 02) |
| `warehouse_name` → `warehouse_id` | `Serverless Starter Warehouse` | SQL warehouse for notebook 02 (looked up by name) |
| `reader_rung`, `reader_limit` | `medgemma-1.5-4b-it`, `40` (prod `0` = all) | MedGemma job |
| `hf_secret_scope` | `dental` | secret scope with `hf_token` |
| `gpu_node_type`, `gpu_spark_version` | `g5.2xlarge`, `16.4.x-gpu-ml-scala2.12` | GPU job cluster (uat/prod; AWS node type, change on Azure/GCP) |
| `lakebase_instance`, `lakebase_database`, `lakebase_schema` | `dental-dev` / `-uat` / `-prod`, `databricks_postgres`, `cdm_dev` / `cdm` | where the OMOP CDM goes in Lakebase |
| `service_principal` | placeholder id | who runs uat/prod jobs |
| `users_group` | `users` | group given CAN_VIEW on uat/prod jobs |

Override any variable with `--var name=value`, or the environment variable
`BUNDLE_VAR_<name>` (that's how CI passes them).

## Jobs

| Job | Notebook | Compute |
|---|---|---|
| `study_benchmark` | `01_run_benchmark.py`: build synthetic study, baselines, Delta tables | serverless |
| `llm_judge` | `02_llm_judge.sql`: judge with `ai_query` | SQL warehouse |
| `load_lakebase` | `04_load_lakebase.py`: OMOP CDM 5.4 + dental extension into Lakebase (Postgres) | serverless |
| `medgemma_reader` (uat/prod) | `03_medgemma_reader.py`: MedGemma note reader, run log to Delta | single-node GPU |

## Deploy from your laptop (dev)

```bash
databricks auth login --host https://<your-workspace>      # once
databricks bundle validate -t dev
databricks bundle deploy   -t dev
databricks bundle run      -t dev study_benchmark
```

## Deploy with CI (uat, prod)

- `.github/workflows/ci.yml`: Python tests (including `tests/test_bundle.py`,
  which checks the three targets, variables, notebook paths and parameters),
  R parity, and `bundle validate` for all targets when dev credentials exist.
- `.github/workflows/deploy.yml`: push to `main` deploys **uat**; run it
  manually to choose dev, uat or prod. Prod waits for approval.

One-time setup in GitHub → Settings → Environments:

1. Create environments `dev`, `uat`, `prod`. Give `prod` required reviewers.
2. In each, add secrets `DATABRICKS_HOST`, `DATABRICKS_CLIENT_ID`,
   `DATABRICKS_CLIENT_SECRET` (a service principal's OAuth M2M credentials), and
   variables `SERVICE_PRINCIPAL`, `JUDGE_ENDPOINT`, `WAREHOUSE_NAME`,
   `GPU_NODE_TYPE`, `USERS_GROUP` as needed.
3. In each workspace: the service principal has `CREATE CATALOG` on the
   metastore (the bundle creates the catalogs) and can use the
   warehouse and the serving endpoint; create the `dental` secret scope with
   `hf_token` for the MedGemma job.

Until those secrets exist, the workflows skip the Databricks steps and still run the tests.

## Checked here, and not

- Both YAML files validate against the bundle schema from Databricks CLI
  v0.270.0, and the CLI loads all three targets.
- `bundle validate` and `deploy` against a real workspace haven't been run from
  this repo yet (they need workspace credentials). Run `validate -t dev` first.
