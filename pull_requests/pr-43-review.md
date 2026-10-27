---
pr: 43
branch: claude/awesome-cannon-7xnqm6
title: "LLM judge scorecard on Databricks, dev deploys on merge (spec 012)"
author: jcbowyer
reviewed_at: 2026-10-27
reviewer: superpowers requesting-code-review subagent + coordinator verification + owner feedback
verdict: approve after fixes
---

# PR Review: LLM judge scorecard on Databricks, dev deploys on merge (spec 012)

## Summary
The numbers check out. The reviewer ran the checks below; nothing differed:
- Recomputed `judge_metrics` from the committed `judgments.csv`: difference 1e-16.
- Compared each system's "correct" with the ladder accuracy: exact match.
- R parity on the real and the simulated runs: largest difference 0.
- Regenerated `docs/results.md` and the README: byte for byte the same.

The review raised three Important findings; all three held up when checked and are fixed on the branch. The owner also flagged the judge write-up as hard
to read, and it was rewritten. A real LLM judge run in dev is committed and labelled *LLM judgment*;
simulated runs stay `simulated_*` and are never shown.

## Scope of Change
- Areas touched: python (judge_scorecard, judge, readme_results), R twin, Databricks notebook, job,
  dashboard, bundle, deploy workflow, docs, spec 012
- Range reviewed: `origin/main...HEAD`

## Findings and outcome
| # | Severity | Finding | Outcome |
|---|---|---|---|
| 0 | Owner | The judge section was jargon ("verdict specificity", unexplained Rogan-Gladen) | Fixed: plain-words rewrite. It names whose mistakes the judge misses (one step off), says what the usual correction would have read (about 100%) and why it isn't shown, and the column names say what they count. Tests check it |
| 1 | Important | With `judge_endpoint=none` (the uat/prod default) the judge columns are all empty, Spark can't infer their type, and no `judgments` table is written | Fixed: `spark_ddl`/`spark_rows`/`empty_judgments` give typed tables; the notebook writes an empty `judgments` table if none exists |
| 2 | Important | dev is now deployed by CI as the service principal, but the docs still said "you, your home folder"; a laptop deploy would make a second state | Fixed in docs: dev is CI-deployed, run (don't deploy) from a laptop. A shared `root_path` for dev would start a new state and duplicate every job, so not changed |
| 3 | Important | Migrate step `|| echo` hid real failures | Fixed: step removed (dev already migrated, uat/prod never deployed); a one-off manual command is in docs/deployment.md |
| 4 | Minor | Resume ignored the prompt version, and the script didn't filter by endpoint | Fixed: `reusable()` keeps only the same endpoint, the current prompt and no endpoint error; used by `run_judge`, the script and the notebook |
| 5 | Minor | An endpoint that omits `usage` would make gate failures look like endpoint errors | Not changed: Databricks endpoints return usage; noted |
| 6 | Minor | The R parity check hard-codes the 0.50/1.50 prices | Not changed: they are the committed run's prices |
| 7 | Minor | A workspace-specific `storage_root` is committed for dev | Not changed: not secret, and needed so the plan keeps the adopted catalog |
| 8 | Minor | The notebook reads the token once | Not changed: resuming covers a token that expires mid-run |

## Verification
- `python -m pytest -q tests`: 384 passed, 12 skipped
- `actionlint .github/workflows/deploy.yml`: clean
- ruff: no new findings in changed files
- R parity (reviewer run): judge sections match to 0
