# CLAUDE.md

Instructions for Claude Code (and other agents) working in this repo.

## Ground rules

Read `DISCLAIMER.md` and `.specify/memory/constitution.md` first. The short version:

- **Personal learning project, not affiliated.** Don't describe anything here as
  an organization's plan, study, finding or partnership. Mention companies only
  as their public sources describe them, with a citation.

- **Synthetic only. No PHI, ever.** Don't add real notes, real names, or
  employer data anywhere, including tests and prompt examples.
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
