---
pr: 66
branch: claude/great-cerf-qwbqck
title: "Never append to a log on a Unity Catalog volume (MedGemma job: Illegal seek)"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator (small fix with a regression test)
verdict: approve
---

# PR Review: Never append to a log on a Unity Catalog volume

## Summary
A one-function fix with a regression test. `runlog.run` opened its log in append mode. Unity Catalog volumes
can't append to an existing file, so every MedGemma reader run after the first failed with `OSError: [Errno 29]
Illegal seek` before the script started. Now each run writes a new file: the path given if it doesn't exist
yet, else a time-stamped file next to it. The run prints which file it used.

## Findings
None. Checked:
- `telemetry.py` also opens a file with `"a"`, but only for local profiling (`DENTAL_TELEMETRY_PROFILE`), never on a volume.
- The encoder GPU job uses the same helper, so it's fixed too.
- Name collisions within one second get a `-2`, `-3` suffix.

## Checks
- `python -m pytest -q tests`: 546 passed, 12 skipped.
- `ruff check` on the changed files: clean.
- Scans: no secrets, no PHI, no organization claims.

## Compliance
| Rule | Result |
|---|---|
| No secrets, synthetic only, no org claims | Pass |
| Test first | Pass (the new test failed before the fix) |
| Python/R parity | n/a |
| Spec | n/a (small fix with a regression test) |
| Commits | Pass |
