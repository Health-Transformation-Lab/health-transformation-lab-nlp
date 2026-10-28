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
- Names: simulated files `simulated_*`, simulated methods `sim:<name>`, calibration-only methods `calib:<name>`.
- R: base R only, matching Python to 1e-9 (`r/tests/test_parity.R`).
- Databricks names: identical in every target (catalog `dental_omop`, schemas
  `landing_`/`bronze_`/`silver_`/`gold_dental_omop_perio`). Never add `dev_`,
  `[dev <user>]` or per-environment prefixes or suffixes, and never use
  `mode: development` (it adds them): each environment is its own workspace.
  dev is deployed by CI on every merge to `main`; don't `bundle deploy` it from a laptop.
- Secrets and tokens: whenever you tell the user to create one, give the exact scope(s)
  to select, a short lifetime, and where it goes. Never ask for it in chat. For this repo:

  | Credential | Where it's made | Scope | Goes to |
  |---|---|---|---|
  | `dental-omop-ci` OAuth secret | Databricks → Settings → Identity and access → Service principals → Secrets | `all-apis` (bundle deploy touches jobs, workspace files, Unity Catalog, MLflow, SQL) | GitHub environment secret `DATABRICKS_CLIENT_SECRET` |
  | Workspace personal access token (admin setup only) | Databricks → Settings → Developer → Access tokens | `all-apis`, 1 day; revoke after | cloud environment variable `DATABRICKS_TOKEN` |
  | `gh` login for `gh secret set` / `gh variable set` | `gh auth login` | `repo` (classic), or fine-grained: this repo, Secrets, Variables and Environments read and write | your laptop only |
  | Hugging Face token for MedGemma | huggingface.co → Settings → Access tokens | Read | Databricks secret scope `dental`, key `hf_token` |
  | Application Insights connection string (telemetry, spec 014) | Azure portal → Application Insights `dental-omop-nlp-appi` → Overview, or `terraform -chdir=infra/azure output -raw connection_string` piped straight into the secret (docs/telemetry.md); also in the git-ignored Terraform state | ingestion only: can send telemetry, can't read; doesn't expire, so rotate by recreating the resource | Databricks secret scope `dental`, key `appinsights_connection_string` |
