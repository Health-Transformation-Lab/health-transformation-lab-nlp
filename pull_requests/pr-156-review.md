---
pr: 156
branch: fix/154-deploy-genie-tables
title: "Break the deploy's Genie deadlock: load results, then deploy again"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: self-review against .claude/review-rubric.md
verdict: approve
---

# PR Review: break the deploy's Genie deadlock

## Summary
Closes #154. When the only deploy errors are Genie spaces whose tables don't exist, the Deploy step runs Load
results, waits for it, and deploys again. Any other failure still fails the step. One file of workflow, one test.

## Findings
- **Narrow retry (checked).** The retry happens only when every `Error:` line names `genie_spaces` and the log
  says `does not exist`. A failure that mixes in another error (as in run 40724655638, where the catalog failed
  first) exits 1 without retrying. This was shown by running the step's own shell against a fake `databricks`.
- **No double load.** The step records `loaded=true`, and the later no-wait Load results step is skipped.
- **Idempotent.** Load results deletes and re-appends by file sha256 (spec 016), so running it from here and on
  later deploys is safe.
- **Fails loudly.** With `pipefail`, a Load results failure or a second deploy failure fails the step.
- **Not covered here (owner step).** The catalog must be owned by the dev admin group before any of this runs
  (`docs/deployment.md`). Without that, the deploy fails on the catalog, and this retry correctly doesn't fire.

## Rubric
Test first: yes. Configuration: no new settings. Secrets: none. Idempotent writes: yes (above). No PHI.
