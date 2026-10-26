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
| Catalog.schema | `workspace.dental_dev` | `dental_uat.dental` | `dental_prod.dental` |
| `n_people` | 300 | 1,500 | 1,500 |
| MedGemma GPU job | no (run notebook 03 on serverless GPU) | yes, single-node GPU cluster | yes, all review notes |

The catalog names for uat and prod are placeholders: set them to the
catalogs your workspaces actually have.

## Variables

| Variable | Default | What it sets |
|---|---|---|
| `catalog`, `schema` | per target (above) | where tables and the data volume go |
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
2. Create the service principal and its grants, as a workspace admin. A bundle
   can't create a service principal, so a script does it with the Databricks SDK,
   reading the catalog, schema, warehouse and secret scope from the target:

   ```bash
   cd python && pip install -e ".[databricks]"
   databricks auth login --host https://<workspace>
   python scripts/32_service_principal.py --target uat                    # dry run: prints the plan
   python scripts/32_service_principal.py --target uat --apply --create-secret \
       [--judge-endpoint <endpoint>] [--warehouse-name "<name>"]
   ```

   It creates `dental-omop-nlp-uat` (entitlements `workspace-access`,
   `allow-cluster-create`), grants `USE_CATALOG`, `CREATE_SCHEMA` on the catalog,
   table/volume/model privileges on the schema, `CAN_USE` on the warehouse,
   `CAN_QUERY` on the judge endpoint and `READ` on the secret scope, then creates
   an OAuth secret (scope `all-apis`) and writes the three secrets below to
   `.databricks-sp-uat.env` (mode 0600, gitignored; it never prints the secret).
   Re-running reuses the principal and only adds grants. Anything not there yet
   (catalog schema, secret scope, endpoint) is reported as skipped: create it and
   re-run. The catalog itself must exist. Not yet run against a real workspace
   from this repo; tested against a fake client (`tests/test_service_principal.py`).
3. In each environment, add secrets `DATABRICKS_HOST`, `DATABRICKS_CLIENT_ID`,
   `DATABRICKS_CLIENT_SECRET` (a service principal's OAuth M2M credentials), and
   variables `SERVICE_PRINCIPAL`, `JUDGE_ENDPOINT`, `WAREHOUSE_NAME`,
   `GPU_NODE_TYPE`, `USERS_GROUP` as needed.
4. In each workspace: if you skipped the script, grant the service principal the
   catalog/schema, the warehouse and the serving endpoint by hand; create the `dental` secret scope with
   `hf_token` for the MedGemma job.

Until those secrets exist, the workflows skip the Databricks steps and still run the tests.

## Checked here, and not

- Both YAML files validate against the bundle schema from Databricks CLI
  v0.270.0, and the CLI loads all three targets.
- `bundle validate` and `deploy` against a real workspace haven't been run from
  this repo yet (they need workspace credentials). Run `validate -t dev` first.
