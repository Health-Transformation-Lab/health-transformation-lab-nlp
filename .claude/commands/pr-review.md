---
description: Review a PR or branch against this repo's rules and write pull_requests/pr-<n>-review.md
argument-hint: "[PR number | branch] (default: current branch)"
---

Review `$ARGUMENTS` (a PR number, a branch, or empty for the current branch) using
`.claude/review-rubric.md`. Read the rubric first and follow it exactly.

1. Resolve the target. For a PR number, read it with the GitHub tools (title, author, base, head
   SHA, CI check runs). For a branch, use `git merge-base origin/main <branch>` as `BASE_SHA`.
2. Run the three scans (secrets, PHI / real data, organization claims) on the full diff.
3. Dispatch the Superpowers `requesting-code-review` reviewer over `BASE_SHA..HEAD_SHA` with the
   rubric, `AGENTS.md` and `CLAUDE.md` as requirements; then verify each finding with `receiving-code-review`.
   Keep only verified findings.
4. Run `cd python && pytest -q tests` and `ruff check` on changed Python files if the diff touches
   Python; note R changes and whether CI `r-parity` passed.
5. Write the review file in the rubric's format and print the verdict, the counts per severity
   and the path. Don't post to GitHub unless asked.
