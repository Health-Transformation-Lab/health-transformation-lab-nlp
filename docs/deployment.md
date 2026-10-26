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
| DistilBERT in the benchmark job (`train_encoder`) | no (baselines only, ~3 min) | yes | yes |
| MedGemma GPU job | no (run notebook 03 on serverless GPU) | yes, single-node GPU cluster | yes, all review notes |

The catalog names for uat and prod are placeholders: set them to the
catalogs your workspaces actually have.

## Variables

| Variable | Default | What it sets |
|---|---|---|
| `catalog`, `schema` | per target (above) | where tables and the data volume go |
| `n_people` | `300` | synthetic people in the benchmark job |
| `train_encoder` | `false` (uat/prod `true`) | train the DistilBERT rung in the benchmark job; over 16 minutes on serverless CPU |
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

One-time setup, per target (the same steps worked on a Free Edition workspace, which
has no account console and no AWS account of your own to configure). uat and prod can
be the same workspace as dev: each target has its own catalog.

1. **Create the service principal, its group, catalog and schema.** Logged in as a
   workspace admin:

   ```bash
   databricks auth login --host https://<workspace>
   databricks/setup/create_service_principal.sh uat --print-config   # names it will use, no changes
   databricks/setup/create_service_principal.sh uat [--judge-endpoint <serving endpoint>]
   ```

   A bundle can't create a service principal, so this script does, with the CLI. It
   makes `dental_omop_nlp_uat_sp` and the group `dental_omop_nlp_uat_admin` (you and the
   principal), both at account level through the workspace's SCIM proxy, and assigns
   them to the workspace. It gives the principal `workspace-access` (every API call
   needs it) and `databricks-sql-access` (validate looks up the SQL warehouse), and
   `READ` on the `dental` secret scope (created if missing). It creates the target's
   catalog and schema if missing (`dental_uat.dental`; the deploy creates the
   registered model there, so they must exist first), gives the group `ALL PRIVILEGES`
   on the catalog and `CREATE CATALOG` on the metastore, and, with `--judge-endpoint`,
   `CAN_QUERY` on that endpoint. It prints the principal's `id` and `applicationId`.
   Run it once per target; a second run fails at the first step because the
   principal exists.
2. **Create its OAuth secret**, here for 90 days. The output shows it once: put it
   straight into GitHub in step 3, never in a file or a chat.
   ```bash
   databricks service-principal-secrets-proxy create <id> --lifetime 7776000s
   ```
3. **Create the GitHub environment, its variables and the secret.** Host and client
   ID are identifiers, so variables; only the client secret is a secret. `gh secret set`
   prompts for the value, so it stays out of your shell history.
   ```bash
   gh api -X PUT repos/<owner>/dental-omop-nlp/environments/uat
   gh variable set DATABRICKS_HOST      -R <owner>/dental-omop-nlp -e uat -b <workspace url>
   gh variable set DATABRICKS_CLIENT_ID -R <owner>/dental-omop-nlp -e uat -b <applicationId>
   gh variable set SERVICE_PRINCIPAL    -R <owner>/dental-omop-nlp -e uat -b <applicationId>
   gh secret set   DATABRICKS_CLIENT_SECRET -R <owner>/dental-omop-nlp -e uat
   ```
   Optional variables: `JUDGE_ENDPOINT`, `WAREHOUSE_NAME` (default
   `Serverless Starter Warehouse`), `GPU_NODE_TYPE`, `USERS_GROUP` (default `users`).
   Give `prod` required reviewers (Settings → Environments → prod).
4. **Check the sign-in:** Actions → `auth_check` → Run workflow, environment `uat`. It
   should print a `userName` equal to `DATABRICKS_CLIENT_ID`. Before the secret
   expires, repeat step 2 and `gh secret set`.
5. **Secrets the jobs read**, in the `dental` scope: `hf_token` (MedGemma job) and
   `lakebase_url` (Lakebase load), e.g. `databricks secrets put-secret dental hf_token`.
   The Lakebase load also needs the principal to be able to connect to the target's
   Lakebase instance; the script doesn't set that up.

Until those secrets exist, the workflows skip the Databricks steps and still run the tests.
Every workflow signs in through `.github/actions/databricks-signin`, which strips spaces and
Windows line endings from the three values first, so a pasted `\r\n` can't break sign-in.

## Checked here, and not

- Both YAML files validate against the bundle schema from Databricks CLI
  v0.270.0, and the CLI loads all three targets.
- `bundle validate` and `deploy` against a real workspace haven't been run from
  this repo yet (they need workspace credentials). Run `validate -t dev` first.
- `databricks/setup/create_service_principal.sh` hasn't been run from this repo; its
  calls are the ones that set up a Free Edition workspace for another bundle. The tests
  check its syntax, its names and catalog per target, and the workflows' sign-in.
