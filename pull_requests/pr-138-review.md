---
pr: 138
branch: docs/135-adr-separate-from-action-items
title: "Keep decision records apart from action items; ADR 0002 no feature store"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator (docs-only, 5 files; no subagent needed)
verdict: approve
---

# PR Review: Keep decision records apart from action items; ADR 0002 no feature store

## Summary
Decisions were being filed as `action-item` issues (#135). This PR gives them a home in `docs/adr/`
(README with the rule and an index, a template), adds the rule to `AGENTS.md`, links it from the
README, and writes #135 as ADR 0002 (no feature store for now, with the conditions to revisit). Docs
only. Verdict: approve.

## Scope of Change
- Files changed: 6 (5 docs, plus this review); +86 / -1
- Areas touched: docs, AGENTS.md, pull_requests
- Range reviewed: `origin/main..HEAD`

## CI Status
| Check | Status |
|---|---|
| python, postgres, r-parity, bundle, check | run on push; no code, data or bundle files touched |

## Secrets, PHI and Claims Scan
All three clean: no credentials, no data, no organization named. The ADR describes Databricks'
feature store generically, as its public docs do.

## Repo Rules
| Rule | Status |
|---|---|
| No secrets / PHI / org claims | ✅ |
| Test first | n/a (docs) |
| Python and R parity | n/a |
| Simulated labelled | n/a (no numbers) |
| Docs | ✅ README gains one link |

## Findings
None blocking. 🔵 `docs/action_items.md` still mixes open decisions (A2, A5, A6, F1) with work;
once each is decided it becomes an ADR and its row links to it. Not in this PR's scope.

## Checks run
- `cd python && pytest -q tests` after merging `main`: 719 passed, 15 skipped.
