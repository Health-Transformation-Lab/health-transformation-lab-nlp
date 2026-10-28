# Running the pipelines: configuration, secrets, alerts and failures

> Personal learning project; synthetic data. Databricks behaviour below is from Databricks' public documentation
> as of October 2026 (links inline); check the page before relying on a detail, because these features change.
> Rules for agents are in [`AGENTS.md`](../AGENTS.md); this page explains them.

Most production failures aren't code bugs. They're a variable set wrong in one environment, a secret that
expired on a Saturday, or a schema that changed upstream, and the alert about it was one of forty in a chat
channel nobody reads. This page covers how this repo heads those off.

## 1. Configuration

**One declaration per setting.** Every setting a job reads is declared once, with a description and a
default:

- Databricks jobs: a variable in [`databricks.yml`](../databricks.yml) (`variables:`), passed to the
  notebook as a job parameter. The same names are used in every target; only values differ, and an
  environment's values live under its target (or as `BUNDLE_VAR_<name>` in that GitHub environment).
- Scripts and libraries: an environment variable, listed in the doc of the feature that reads it (for
  example `DENTAL_TELEMETRY*` in [telemetry.md](telemetry.md)). There are no defaults hidden in code that
  differ by environment.

**Checked at the start.** A job checks its settings before it does any work, and fails with the variable's
name and what was expected, not with a stack trace an hour in. The repo already does this in three places:

- `telemetry.config_from_env` checks the shape of the connection string.
- The Kaggle workflow makes a cheap authenticated call (`kaggle kernels list --mine`) before pushing.
- `deploy.yml` stops early, with a message, when an environment has no sign-in.

The pattern for a new setting:

| Kind | If it's missing or malformed |
|---|---|
| Required (a catalog, an endpoint the job exists to call) | fail before any work, naming it |
| Optional (telemetry, tracking) | warn once and run without it; never fail the pipeline |
| A credential | check its shape, then make one cheap authenticated call, before the expensive work |

**Changed by pull request.** A setting changes in a PR like code. The PR says which environments it
affects. `bundle validate` runs in CI. A job records the commit it was deployed from (`git_commit` on every
job and run), so "what was this set to on Tuesday?" is answered from git.

## 2. Secrets: a register, and warnings before they expire

[`ops/secrets_register.yaml`](../ops/secrets_register.yaml) lists every credential the pipelines use. For
each one it records what it's for, where it was made, its scope, where it's stored, what uses it, its
lifetime, its **expiry date**, its owner, and what breaks when it expires. It never holds a value, and a
test checks that.

- When you make or rotate a credential, write its expiry date in the register in the same PR. `unknown`
  is allowed only until someone looks it up; it counts as an open finding.
- Give each credential the shortest lifetime that works, and the narrowest scope (`AGENTS.md`, secrets
  table).
- **Renew 14 days before expiry.** Warnings start at 30 days (SEV3, daily digest) and escalate at 7 days
  (SEV2, to the owner directly). An expired credential that stops a production job is SEV1.
- Some limits to know:
  - A Databricks service-principal OAuth secret lasts at most **730 days**, and a principal can hold
    up to five at once ([OAuth M2M](https://docs.databricks.com/aws/en/dev-tools/auth/oauth-m2m)). So
    rotation is make the new one, swap it in, then delete the old one, with no gap.
  - OAuth access tokens last one hour and are refreshed automatically; it's the secret behind them that
    expires.
  - The Application Insights connection string never expires, so it's rotated by recreating the
    resource.

The register is the input for an expiry check that will run on a schedule and feed the digest (below).
That check isn't built yet.

## 3. Alerts: severity levels and a digest people can work through

An alert is worth sending only if it names an action and an owner. Everything else is a dashboard.

| Level | Means | Examples here | Who hears, how | Act within |
|---|---|---|---|---|
| **SEV1** critical | Wrong or unsafe output is being published, data is exposed, or production is down with no workaround | de-identification leak gate fails; wrong numbers reach the README or dashboard; a secret is leaked; an expired credential stops a production job | the named owner directly (email and phone push), immediately | 1 hour |
| **SEV2** high | A production pipeline failed and won't recover by itself, or will fail soon | retries used up; results older than their freshness target; a credential expires within 7 days | the owner by email, as it happens, deduplicated | same working day |
| **SEV3** medium | Something failed or drifted but recovered, or will need work | a retry succeeded; a data-quality check below threshold; rows in the rescued-data column; a credential expires within 30 days | **daily digest** | next working day |
| **SEV4** low | Worth knowing; no deadline | deprecation warnings; cost drifting up; a credential expires within 90 days | **weekly digest** | this week |

**Why a digest, and how to make one usable:**

- **One email per owner per period, not one per event.** Group by severity, then by system. Show each
  problem once, with a count and first and last seen (for example "Load results: rescued rows, 14 times
  since Monday").
- **Every line has an action**: what failed, the impact, the owner, and a link to the run and to the
  fix. A line with no action is removed from alerting, not muted.
- **It's a work list.** An item stays in each digest until it's closed, so nothing disappears because it
  scrolled away. The weekly digest lists what was closed too.
- **Chat channels can mirror a digest; they don't replace it.** A busy Teams or Slack channel mixes
  people's messages with machine messages and has no "done" state. Email to a named owner, or a ticket,
  does.
- **Only SEV1 and SEV2 interrupt anyone.** If SEV2 fires more than a few times a week for the same cause,
  fix the cause or lower its level. Alert fatigue is what makes the real one get missed.

The telemetry already records what the digest needs: failures by step and error type, durations, and
data-quality pass rates ([telemetry.md](telemetry.md), KQL queries). The digest job, Azure Monitor alert
rules grouped by severity, and the expiry check are the next spec, the "pipeline doctor".

## 4. Failures, retries and reruns on Databricks

What the platform does, and what it leaves to you:

- **Task retries (Lakeflow Jobs).** You set a retry policy per task: how many times, and the interval.
  - For most configurations the default is **not to retry**.
  - Serverless jobs auto-optimise retries by default.
  - When both are set, the **timeout applies to each retry**.
  - Continuous jobs can't use retry policies; they retry the whole job with exponential backoff.
  - Source: [Configure tasks](https://docs.databricks.com/aws/en/jobs/configure-task),
    [Continuous jobs](https://docs.databricks.com/aws/en/jobs/continuous).
  - Here, the GPU jobs set `max_retries: 6`, 30 minutes apart (`databricks/resources/jobs.yml`), to wait
    out a GPU shortage.
- **Repair runs.** A repair re-runs only the unsuccessful tasks and the tasks that depend on them, and
  each re-run starts **from the beginning of the task**.
  - Databricks states that Lakeflow Jobs **doesn't make tasks idempotent**, so a task that wrote part
    of its output before failing can write it again.
  - Repair is only for jobs with two or more tasks.
  - Source: [Repair job failures](https://docs.databricks.com/aws/en/jobs/repair-job-failures).
- **Declarative Pipelines.** Flows retry transient failures.
  - The current properties reference gives per-flow and per-update retry limits, defaulting to 5 for
    triggered pipelines; older pages said fewer.
  - **No retries in development mode or for Validate updates**
    ([pipeline properties](https://docs.databricks.com/aws/en/ldp/properties)).
  - After a failure you can refresh only selected tables, full-refresh a selection, or reset streaming
    checkpoints for selected flows (`reset_checkpoint_selection`) without clearing written data.
  - A full refresh of a streaming table truncates it and re-reads the source, so records past the
    source's retention are lost. Set `pipelines.reset.allowed = false` on tables that must never be
    fully refreshed
    ([refresh semantics](https://docs.databricks.com/aws/en/ldp/concepts/refresh),
    [run an update](https://docs.databricks.com/aws/en/ldp/updates)).
- **Streaming.** `foreachBatch` gives a micro-batch id, and Delta gives commit versions. These are
  transaction ids, not business batch ids. If you need "which delivery did this row come from", write
  one yourself.

**So every write in this repo is idempotent.** A rerun of any task must leave the table as if it ran
once:

- Use overwrite, or `MERGE` on a key.
- Or **delete-then-append by batch key**. Load results (spec 016) does this: it deletes the rows of the
  same file versions (SHA-256), then appends, and records each loaded file in `dim_result_file` last.
- Every written row carries its batch key (file SHA, run id, `git_commit`, load time), so a bad batch can
  be found and removed.
- Plain `append` is allowed only for a log, where every row is a distinct event. The MedGemma reader job
  writes `fact_prediction` and `fact_llm_call` by batch key instead (`delta.replace_batch`, keyed by
  source, job run id and method), so one of its retries replaces the run's rows.

### When Databricks is down: catch up without anyone remembering (issue #189)

Results made elsewhere (Kaggle, a laptop) are committed to git first, so an outage loses nothing. What it can
leave behind is the load: a merge deploys and starts Load results (`deploy.yml`), and if Databricks is down the
deploy fails; if Load results fails, nobody sees it, because the deploy starts it without waiting.

`.github/workflows/catch-up.yml` (*Catch up Databricks after an outage*) runs `.github/scripts/catch_up.py` every
3 hours for dev and uat, in the deploy's concurrency group, and can be started by hand:

| What it finds | What it does |
|---|---|
| Databricks doesn't answer | warns (SEV3) and checks again in 3 hours; still behind 24 hours after a failed deploy, the run fails (SEV2, GitHub emails the owner) |
| Databricks refuses the sign-in | fails at once (SEV2): renew `DATABRICKS_CLIENT_SECRET` |
| it answers, and the last deploy of `main` failed | re-runs the deploy's failed jobs (up to 3 attempts; then it fails, SEV2: not an outage) |
| deployed, but Load results has no successful run for the deployed commit | runs Load results and waits; fails after 3 failures for one commit |
| otherwise | nothing |

Load results adds only file versions it hasn't loaded, so running it again is safe. Nobody needs to remember to
re-run anything after an outage.

## 5. Ingestion with Auto Loader, and schema drift

The repo doesn't ingest files with Auto Loader yet; these are the rules for when it does. Sources:
[Auto Loader options](https://docs.databricks.com/aws/en/ingestion/cloud-object-storage/auto-loader/options),
[schema inference and evolution](https://docs.databricks.com/aws/en/ingestion/cloud-object-storage/auto-loader/schema),
[cleaning up processed files](https://docs.databricks.com/aws/en/ingestion/cloud-object-storage/auto-loader/clean-source).

**Choose `cloudFiles.schemaEvolutionMode` on purpose, and write down why:**

| Mode | On a new column | Use when |
|---|---|---|
| `addNewColumns` (default without a schema) | stream **stops**; the column is added to the schema; the restart (job retry) picks it up | the source adds columns legitimately and you want them |
| `rescue` | schema never changes; unexpected data goes to the rescued-data column; stream keeps going | the feed must not stop, and drift is reviewed |
| `failOnNewColumns` | stream stops until someone updates the schema or removes the data | regulated or contract feeds: a change needs a decision |
| `none` (default when a schema is given) | new columns ignored, **silently**, unless `rescuedDataColumn` is set | rarely; always pair it with a rescued-data column |

- `addNewColumnsWithTypeWidening` (Public Preview, DBR 16.4+) also widens types. Unsupported changes
  (int to string, say) still go to the rescued-data column
  ([type widening](https://docs.databricks.com/aws/en/ingestion/cloud-object-storage/auto-loader/type-widening)).
- **Always set** `cloudFiles.schemaLocation` (where the inferred schema and its history live) and
  `rescuedDataColumn`.
- Use `cloudFiles.schemaHints` to pin the types you know. `addNewColumns` isn't allowed with a full
  schema, but it works with hints.
- **Capture drift as data:** count rows with a non-null rescued-data column per batch and send it as a
  data-quality metric. Any rescued rows is a SEV3 digest item, with the file names. Keep the schema
  location's history: it's the record of when each column appeared.

**`cloudFiles.cleanSource`** (DBR 16.4+) moves or deletes processed files:

- The default is `OFF`. It acts after `cloudFiles.cleanSource.retentionDuration`, which defaults to
  30 days; `DELETE` needs more than 7.
- A `MOVE` destination must be in the same external location (or volume) as the source and not inside
  it.
- It's **best effort**. The setting in force at cleanup time is the one that applies.
- With `DELETE`, turn on bucket versioning so a deletion can be undone.
- Use it only when one stream reads the directory. Together with the `cloud_files_state` function, it's
  the only record Auto Loader keeps of which files it took. Write your own file ledger (file, size,
  checksum, batch, rows) if you need to prove what was loaded, as `dim_result_file` does for results.

## 6. FHIR on Databricks: partners, not platform

Databricks has no native FHIR parser. The options are partner or Labs projects:

- **Health Samurai's Aidbox** runs on Lakebase, Databricks' managed Postgres. Health Samurai and Databricks
  announced the partnership in June 2026, and Aidbox's March 2026 release added Databricks identities for
  Lakebase connections. Health Samurai says the data is replicated into the lakehouse with no ETL step
  ([Databricks blog](https://www.databricks.com/blog/building-fhir-native-health-data-platform-databricks-lakebase),
  [Health Samurai](https://health-samurai.io/partners/databricks)).
- **`dbignite`** is a Databricks Labs project
  ([github.com/databrickslabs/dbignite](https://github.com/databrickslabs/dbignite)). Databricks Labs
  projects aren't covered by Databricks support.

Treat each as a vendor dependency, with its own version, owner and renewal date in the register if it
needs a credential.
