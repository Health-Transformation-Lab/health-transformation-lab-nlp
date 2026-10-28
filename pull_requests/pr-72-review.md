---
pr: 72
branch: claude/great-cerf-qwbqck
title: "Fix Load results finding no result files on Databricks"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator (small fix with a regression test)
verdict: approve
---

# PR Review: Fix Load results finding no result files on Databricks

## Summary
This is a small fix with a regression test. Closes #71. In dev, the run output showed `CANNOT_INFER_EMPTY_SCHEMA`
from `display()` on an empty list of files, even though the workspace listing shows 33 deployed files in
`files/data/datasets/`. The notebook now reads the deployed files relative to itself, which is the path
notebook 03 already uses successfully. It names the folder, stops clearly when the folder holds no files,
and never displays an empty table.

## Findings
None blocking. One risk remains: the exact reason the package path found no files on serverless isn't proven.
The fix no longer depends on that path, and if the relative path also finds nothing, the job now stops with
the folder's name instead of a Spark error. The first run after merge will settle it.

## Checks
- `pytest -q tests`: 586 passed, 12 skipped.
- `ruff check` on the notebook: clean.
- Ran the notebook twice on local Spark: the first run loaded the files, the second found nothing new and
  finished cleanly.
- Scans: no secrets, no PHI.

## Compliance
| Rule | Result |
|---|---|
| No secrets, synthetic only, no org claims | Pass |
| Test first | Pass |
| Configuration | Pass (fails fast, naming the folder) |
| Idempotent writes | Unchanged (delete-then-append by file SHA) |
| Branches and issues | Pass (`claude/*` branch, `Closes #71`) |
