---
pr: 17
branch: claude/awesome-cannon-7xnqm6
title: "Get the bundle deploying from CI as the dental-omop-ci service principal"
author: jcbowyer
reviewed_at: 2026-10-26
reviewer: superpowers requesting-code-review subagent + coordinator verification
verdict: approve
---

# PR Review: Get the bundle deploying from CI as the dental-omop-ci service principal

## Summary
Fixes the four things that stopped the bundle deploying from GitHub Actions as the
`dental-omop-ci` service principal: host/client id stored as environment variables, a CLI whose
Terraform signing key expired, the experiment passed by name (Terraform "inconsistent final plan"),
and a job notebook cell with a literal `<catalog>.<schema>`. A dev `validate` + `deploy` from this
branch succeeded. No blocking findings; the three verified minor findings were fixed in `b28ed7a`.
Verdict: approve.

## Scope of Change
- Files changed: 7 (+~65 / -~32)
- Areas touched: .github, databricks, python tests, docs, CLAUDE.md
- Commits:
  - 4764555 Say which scope to set whenever a secret or token is created
  - e1725c7 Read Databricks host and client id from secrets or variables
  - f5ca4a8 Upgrade Databricks CLI to v0.297.2 in CI and deploy
  - 74f84d7 Pass the MLflow experiment to the benchmark job by id, not name
  - a384f2a Make the benchmark notebook's LLM cell runnable as a job, off by default
  - b28ed7a Fix review nits: comment target, deployment doc wording, endpoint name check
- Range reviewed: `origin/main..b28ed7a`

## CI Status
| Check | Status |
|---|---|
| bundle | passed on a384f2a |
| python, r-parity, postgres | running at time of writing |

## Secrets, PHI and Claims Scan
Secrets: clean. PHI / real data: no data files changed. Organization claims: clean.

## Strengths
- Each commit names its root cause (expired HashiCorp key, `/Workspace` vs `/Users` path normalisation).
- Experiment passed by id, matching the judge monitoring job.
- Only host and client id may be variables; the client secret stays a secret.
- New regression tests each fail before their fix.

## Findings
### 🔴 Blocking (Critical)
None.
### 🟡 Should fix (Important, non-blocking)
None.
### 🔵 Nits / suggestions (Minor)
- `01_run_benchmark.py:37` comment pointed at `mlops.yml`; parameter is set in `jobs.yml`. Fixed in b28ed7a.
- `docs/deployment.md:73-75` said "secret scope `all-apis`" and implied the host comes from the service principal. Fixed in b28ed7a.
- `01_run_benchmark.py` `llm_endpoint` interpolated into SQL unchecked. Now validated against `[\w.-]+`. Fixed in b28ed7a.
- `test_bundle.py` placeholder test only matches `<catalog>`/`<schema>`. Left as is: it guards the failure that happened; a general `<...>` match risks false positives on SQL/HTML in code cells.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets | ✅ | |
| Synthetic only, no PHI | ✅ | no data changes |
| No organization claims; vendors cited | ✅ | CLI issue cited (databricks/cli#5022) |
| Test first | ✅ | two new tests, each failed before its fix |
| Python and R in parity | n/a | no labels/scoring/reliability/CE change |
| Simulated is labelled simulated | n/a | |
| Seeds fixed | n/a | |
| Paths | ✅ | |
| Spec for big changes | n/a | deployment fixes only |
| Prices | n/a | |
| Commits | ✅ | imperative, why, trailers |
| Docs | ✅ | deployment.md updated |

## Test Coverage
`cd python && pytest -q tests`: 280 passed, 12 skipped. Bundle validate/deploy to dev from CI
succeeded before the notebook-only commits. Benchmark job not yet run end to end.

## Verdict
Approve. Merge when CI is green.
