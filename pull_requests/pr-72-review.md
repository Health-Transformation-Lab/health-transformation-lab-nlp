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
This is a small fix with a regression test. Closes #71. Load results succeeded once, at 11:29 on 2026-10-28, and
loaded all 16 committed files: `result_files` has 16 rows, `ai_predictions` 3,600 rows (15 methods),
`llm_reader_runs` 240 MedGemma rows. Every later run had nothing new and crashed in `display()` on the empty
table (`CANNOT_INFER_EMPTY_SCHEMA`).

The first diagnosis, that the job found no files through the package path, was wrong. The tables and the
one successful run show the files were found. The fix:
- skips display when nothing is new;
- reads the files next to the notebook, as notebook 03 does;
- stops with a clear message naming the folder if it finds no result files.

The PR also records the renewed agent token in the secrets register (expires 2026-11-11) and adds
`docs/model_inventory.md` (#85).

## Findings
None blocking.

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
