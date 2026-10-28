# CLAUDE.md

@AGENTS.md

The rules above (in `AGENTS.md`) apply to every agent. This file adds Claude Code's own workflow.

## Organization names: never CareQuest

Never reference CareQuest anywhere in this repo: CareQuest Institute for Oral Health, CareQuest Innovation
Partners, their programs, people, data, plans or strategy. That covers code, docs, tests, data, slide decks, commit
messages, issues and pull requests, and disclaimers too: write "any employer or organization" instead. Content that
came from CareQuest work is made generic before it comes in, with nothing that identifies it.

This file is the only place the name may appear, to state this rule. An exception needs this section changed first,
naming the file and why. `python/tests/test_no_org_references.py` fails CI if the name appears in any other tracked
file.

## Words: we find gum disease in records, we don't diagnose

We aren't clinicians. "Diagnosis" is only ever something a dentist recorded (`diagnosis code`, "the recorded
diagnosis"), never something our rules, models or agents do. What we do is phenotyping, but most readers don't know
the word: say it plainly first and give the term once in brackets, e.g. "finding gum disease in dental records
(phenotyping)", then "case finding".

| Avoid | Write |
|---|---|
| diagnose, AI diagnoses, diagnostic tool | identify or find gum disease in the record; record-reading or case-finding tool |
| accurate diagnosis, diagnosis accuracy | agreement with gum specialists reviewing the same record |
| inaccurate or wrong diagnosis, misdiagnosis | record mismatch ("the recorded code doesn't fit the chart"); records to recheck |

A mismatch is often a coding or charting gap, not a clinical error: never imply a dentist got it wrong. This covers
docs, decks, dashboards, Genie instructions, table and column names, issues and PRs. Quoting a cited paper's own
words is fine.

## Workflow: Spec Kit + Superpowers

| Stage | Tool | Output |
|-------|------|--------|
| What and why | `/speckit-specify` (then `/speckit-clarify` if needed) | `specs/NNN-name/spec.md` |
| One issue per user story, then its branch | GitHub issue; branch `<type>/<issue>-<slug>` (AGENTS.md, "Branches and issues") | issue `#n`, branch `feat/<n>-NNN-slug` |
| How, at feature level | `/speckit-plan`, `/speckit-tasks` (`/speckit-analyze` to cross-check) | `plan.md`, `tasks.md` in the same folder |
| Open design questions | Superpowers `brainstorming` | `docs/superpowers/specs/YYYY-MM-DD-topic-design.md` |
| Session plan | Superpowers `writing-plans`, then `executing-plans` or `subagent-driven-development` | `docs/superpowers/plans/YYYY-MM-DD-topic.md` |
| Each task | Superpowers `test-driven-development` | failing test → code → passing test |
| Before saying done | Superpowers `verification-before-completion` | commands run, output checked |
| Settings, secrets, writes | AGENTS.md "Configuration and secrets", "Failures, retries and reruns"; background in `docs/operations.md` | register updated, settings checked at start, writes idempotent |
| Open a PR | `/create-pr` (checks, opens the PR with `Closes #<issue>`, reviews it) | PR + `pull_requests/pr-<n>-review.md` |
| Before merge | `/pr-review <n>` (Superpowers `requesting-code-review`, rubric in `.claude/review-rubric.md`) | `pull_requests/pr-<n>-review.md` |

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
