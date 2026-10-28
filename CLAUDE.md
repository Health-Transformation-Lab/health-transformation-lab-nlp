# CLAUDE.md

@AGENTS.md

The rules above (in `AGENTS.md`) apply to every agent. This file adds Claude Code's own workflow.

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
