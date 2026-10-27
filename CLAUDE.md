# CLAUDE.md

Instructions for Claude Code (and other agents) working in this repo.

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

## Workflow: Spec Kit + Superpowers

| Stage | Tool | Output |
|-------|------|--------|
| What and why | `/speckit-specify` (then `/speckit-clarify` if needed) | `specs/NNN-name/spec.md` |
| How, at feature level | `/speckit-plan`, `/speckit-tasks` (`/speckit-analyze` to cross-check) | `plan.md`, `tasks.md` in the same folder |
| Open design questions | Superpowers `brainstorming` | `docs/superpowers/specs/YYYY-MM-DD-topic-design.md` |
| Session plan | Superpowers `writing-plans`, then `executing-plans` or `subagent-driven-development` | `docs/superpowers/plans/YYYY-MM-DD-topic.md` |
| Each task | Superpowers `test-driven-development` | failing test → code → passing test |
| Before saying done | Superpowers `verification-before-completion` | commands run, output checked |
| Open a PR | `/create-pr` (checks, opens the PR, reviews it) | PR + `pull_requests/pr-<n>-review.md` |
| Before merge | `/pr-review <n>` (Superpowers `requesting-code-review`, rubric in `.claude/review-rubric.md`) | `pull_requests/pr-<n>-review.md` |

Small fixes (a typo, a one-line bug with a regression test) don't need a spec.
Anything that changes a dataset, a metric, a label rule or the review workflow does.

## Commands

```bash
cd python && pip install -e ".[dev]"
pytest -q tests                                   # Python tests
cd .. && python/scripts/make_parity_inputs.sh && Rscript r/tests/test_parity.R   # R vs Python parity
cd python && python scripts/10_build_study.py     # rebuild study datasets (seeded)
cd python && python scripts/35_readme_results.py  # refresh the README results leaderboards after new results
```

Full pipeline and dry runs: `README.md`. Study design: `docs/process.md`.

## Setup for Superpowers

`.claude/settings.json` enables Superpowers from the official plugin
marketplace. If Claude Code reports it isn't installed, run once:

```
/plugin install superpowers@claude-plugins-official
```

or from Superpowers' own marketplace:

```
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```

Spec Kit's skills are checked in under `.claude/skills/speckit-*`; no install
needed to use them. To refresh them to a newer Spec Kit:
`uvx --from git+https://github.com/github/spec-kit.git specify init --here --force --integration claude`.

## Conventions

- Commits: imperative subject, body says why. Co-author trailer when an agent wrote it.
- Seeds: every generator and sampler takes one; defaults are fixed.
- Paths: use `dental_omop_nlp.paths`, never hard-code `data/`.
- Names: simulated files `simulated_*`, simulated methods `sim:<name>`, calibration-only methods `calib:<name>`.
- Databricks names: identical in every target (catalog `dental_omop`, schemas
  `landing_`/`bronze_`/`silver_`/`gold_dental_omop_perio`). Never add `dev_`,
  `[dev <user>]` or per-environment prefixes or suffixes, and never use
  `mode: development` (it adds them): each environment is its own workspace.
- Secrets and tokens: whenever you tell the user to create one, give the exact scope(s)
  to select, a short lifetime, and where it goes. Never ask for it in chat. For this repo:

  | Credential | Where it's made | Scope | Goes to |
  |---|---|---|---|
  | `dental-omop-ci` OAuth secret | Databricks → Settings → Identity and access → Service principals → Secrets | `all-apis` (bundle deploy touches jobs, workspace files, Unity Catalog, MLflow, SQL) | GitHub environment secret `DATABRICKS_CLIENT_SECRET` |
  | Workspace personal access token (admin setup only) | Databricks → Settings → Developer → Access tokens | `all-apis`, 1 day; revoke after | cloud environment variable `DATABRICKS_TOKEN` |
  | `gh` login for `gh secret set` / `gh variable set` | `gh auth login` | `repo` (classic), or fine-grained: this repo, Secrets, Variables and Environments read and write | your laptop only |
  | Hugging Face token for MedGemma | huggingface.co → Settings → Access tokens | Read | Databricks secret scope `dental`, key `hf_token` |
