# AGENTS.md

Rules for every coding agent working in this repo (Claude Code, Codex, Cursor, Copilot and others).
Claude Code reads them through `CLAUDE.md`, which imports this file and adds its own workflow.

Folders with their own rules have their own `AGENTS.md` (read it before working there):

- `databricks/agents/chart_review/AGENTS.md`: the planned Databricks chart review agent.

## Ground rules

Read `DISCLAIMER.md` and `.specify/memory/constitution.md` first. The short version:

- **Personal learning project, not affiliated.** Don't describe anything here as
  an organization's plan, study, finding or partnership. Mention companies only
  as their public sources describe them, with a citation.
- **Synthetic only. No PHI, ever.** Don't add real notes, real names, or
  employer data anywhere, including tests and prompt examples. One exception:
  published, already de-identified datasets licensed for redistribution (MACCROBAT,
  CC BY 4.0) live in `data/external/<name>/` with a README giving source and licence,
  for evaluation and training only, never mixed into the synthetic sets.
  Data-use-agreement sets (i2b2/n2c2) never go in.
- **Python and R stay in parity.** If you change labels, scoring, reliability
  or cost-effectiveness on one side, change the other and run the parity test.
- **Test first.** Write the failing test, then the code.
- **Label simulated output as simulated.** Never present a dry-run number as a result.

## When a change needs a spec

Anything that changes a dataset, a metric, a label rule or the review workflow gets a spec first:
`specs/NNN-name/spec.md` (what and why), then `plan.md` and `tasks.md` in the same folder (how).
Small fixes (a typo, a one-line bug with a regression test) don't need one.
Every pull request gets a review written to `pull_requests/pr-<n>-review.md`, against
`.claude/review-rubric.md` and these rules.

## Branches and issues

Every user story is a GitHub issue, and every branch and pull request belongs to one.

1. **One issue per user story.** When a spec is written, open one issue per user story, titled
   `<spec number> US<n>: <story>` (e.g. `016 US2: every committed result is in the gold tables`), and write
   the issue number next to the story in `spec.md` (`### US2 - ... (P1) #71`). A fix or chore without a spec
   gets its own issue too, describing the problem.
2. **Branch: `<type>/<issue>-<slug>`**, e.g. `feat/71-016-results-loader` or `fix/72-volume-log-append`.
   - type: `feat`, `fix`, `docs`, `data`, `ci`, `chore`, `spec`
   - issue: the GitHub issue number (a Jira key like `DENT-123` also passes, if a Jira project is ever used)
   - slug: lowercase words joined by `-`, at most 40 characters; for spec work, start with the spec number
   - `/speckit-specify` creates `NNN-name`: rename it (`git branch -m spec/<issue>-NNN-name`)
3. **Pull request: one issue's work, and `Closes #<issue>` in the description**, so the merge closes it
   (use `Refs #<issue>` for one part of a larger story).
4. **Branches a tool names are kept as they are:** `claude/*` (an agent session's assigned branch: the PR
   still needs its `Closes #<issue>` line), `dependabot/*`, and `kaggle-results/*` (results PRs the Kaggle
   workflow opens; no issue needed).

CI checks 2–4 on every PR (`.github/workflows/pr-conventions.yml`, `.github/scripts/pr_conventions.py`).

## Configuration and secrets

Most production failures are configuration: a variable wrong in one environment, or a secret that expired.
Details and reasons: [`docs/operations.md`](docs/operations.md).

- **One declaration per setting**: a `databricks.yml` variable (description and default) for jobs, or an
  environment variable documented with its feature. Same names in every environment; no per-environment
  defaults hidden in code.
- **Check settings before doing work.** Required setting missing or malformed: fail at once, naming it.
  Optional (telemetry, tracking): warn and carry on. A credential: check its shape, then one cheap
  authenticated call, before the expensive work.
- **Settings change by pull request**, and the PR says which environments change.
- **Every credential is in [`ops/secrets_register.yaml`](ops/secrets_register.yaml)** with where it lives,
  scope, owner, what breaks without it and its **expiry date** (never its value). Making or rotating a
  credential updates the register in the same PR. Renew 14 days before expiry; rotate without a gap (make
  the new one, swap, then revoke the old).
- Never put a secret in a job parameter, a file, a log, a span, a PR or chat.

## Alerts and severity

Every alert names a severity, an owner and an action. Without an action it isn't an alert.

| Level | Means | Goes to |
|---|---|---|
| SEV1 | wrong or unsafe output published, data exposed, or production down | the owner directly, now (1 hour) |
| SEV2 | a production pipeline failed and won't recover, or a credential expires within 7 days | the owner by email, same day |
| SEV3 | failed then recovered, a data-quality check below threshold, rescued rows, credential within 30 days | the **daily digest** |
| SEV4 | warnings, deprecations, cost drift, credential within 90 days | the **weekly digest** |

Digests are one email per owner per period: grouped by severity then system, each problem once with a count,
each line with its fix and link, and kept until closed. A chat channel may mirror a digest, never replace it.
A SEV2 that fires every week for the same cause gets its cause fixed or its level lowered.

## Failures, retries and reruns

- **Every write is idempotent**: overwrite, `MERGE` on a key, or delete-then-append by batch key (as Load
  results does). Plain append only for event logs. Databricks repair re-runs a whole task from the start and
  does not make it idempotent for you.
- **Every written row carries its batch key** (run id or file SHA, `git_commit`, load time).
- **Retries are set explicitly** per task (count and interval), only for failures that can pass on their own
  (no GPU free, a network blip); a timeout applies to each retry. A bad setting or bad data fails at once.
- A failure says how it ended (exit code, signal, memory) and is logged where it survives the process
  (`runlog`), never into a file opened for append on a volume.

## Ingestion and schema drift

- Auto Loader streams set `cloudFiles.schemaLocation`, a rescued-data column, and a deliberately chosen
  `cloudFiles.schemaEvolutionMode`, with the reason in a comment. Default to `rescue` or `failOnNewColumns`
  for feeds that must not change silently; never `none` without a rescued-data column.
- Rows in the rescued-data column are counted per batch and reported (SEV3).
- `cleanSource` only for single-reader directories, `DELETE` only with bucket versioning on, and keep our
  own file ledger when we must prove what was loaded.

## Commands

```bash
cd python && pip install -e ".[dev]"
pytest -q tests                                   # Python tests
cd .. && python/scripts/make_parity_inputs.sh && Rscript r/tests/test_parity.R   # R vs Python parity
cd python && python scripts/10_build_study.py     # rebuild study datasets (seeded)
cd python && python scripts/35_readme_results.py  # refresh the README results leaderboards after new results
```

Full pipeline and dry runs: `README.md`. Study design: `docs/process.md`.

## Conventions

- Commits: imperative subject, body says why. Co-author trailer when an agent wrote it.
- Seeds: every generator and sampler takes one; defaults are fixed.
- Paths: use `dental_omop_nlp.paths`, never hard-code `data/`.
- Telemetry: every public function or method in `python/dental_omop_nlp/` gets `@traced` (from
  `.telemetry`); a test fails without it. Never put note text or row-level data in span attributes or logs.
- Names: simulated files `simulated_*`, simulated methods `sim:<name>`, calibration-only methods `calib:<name>`.
- R: base R only, matching Python to 1e-9 (`r/tests/test_parity.R`).
- Databricks names: identical in every target (catalog `dental_omop`, schemas
  `landing_`/`bronze_`/`silver_`/`gold_dental_omop_perio`). Never add `dev_`,
  `[dev <user>]` or per-environment prefixes or suffixes, and never use
  `mode: development` (it adds them): each environment is its own workspace.
  dev is deployed by CI on every merge to `main`; don't `bundle deploy` it from a laptop.
- Secrets and tokens: whenever you tell the user to create one, give the exact scope(s)
  to select, a short lifetime, and where it goes, and add it to `ops/secrets_register.yaml` with its expiry.
  Never ask for it in chat. For this repo:

  | Credential | Where it's made | Scope | Goes to |
  |---|---|---|---|
  | `dental-omop-ci` OAuth secret | Databricks → Settings → Identity and access → Service principals → Secrets | `all-apis` (bundle deploy touches jobs, workspace files, Unity Catalog, MLflow, SQL) | GitHub environment secret `DATABRICKS_CLIENT_SECRET` |
  | Workspace personal access token (admin setup; agent reads job runs) | Databricks → Settings → Developer → Access tokens | `all-apis`, 15 days at most; revoke when not needed | cloud environment variable `DATABRICKS_TOKEN` |
  | `gh` login for `gh secret set` / `gh variable set` | `gh auth login` | `repo` (classic), or fine-grained: this repo, Secrets, Variables and Environments read and write | your laptop only |
  | Hugging Face token for MedGemma | huggingface.co → Settings → Access tokens | Read | Databricks secret scope `dental`, key `hf_token` |
  | Application Insights connection string (telemetry, spec 014) | Azure portal → Application Insights `dental-omop-nlp-appi` → Overview, or `terraform -chdir=infra/azure output -raw connection_string` piped straight into the secret (docs/telemetry.md); also in the git-ignored Terraform state | ingestion only: can send telemetry, can't read; doesn't expire, so rotate by recreating the resource | Databricks secret scope `dental`, key `appinsights_connection_string` |
  | Kaggle API token (MedGemma on Kaggle) | kaggle.com → Settings → API → Generate New Token | the Kaggle account (no narrower scope offered); delete it on Kaggle when not running | GitHub environment `dev` secret `KAGGLE_API_TOKEN` |
