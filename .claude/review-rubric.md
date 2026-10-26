# PR review rubric (shared by /create-pr and /pr-review)

Adapted from the open-navigator `/create-pr` review flow (Superpowers code-review skills,
verified findings only, mandatory secrets scan), with this repo's rules from `CLAUDE.md`,
`DISCLAIMER.md` and `.specify/memory/constitution.md`.

## How the review runs

1. **Range.** `BASE_SHA` = merge base with `main`; `HEAD_SHA` = branch head. Review only
   `BASE_SHA..HEAD_SHA`. Leave out generated outputs from the line counts (`data/**/*.csv`,
   `data/**/*.json`, notebooks' outputs) but still scan them (step 2).
2. **Scans, before any reading for style.** Run all three on the diff, including data files:
   - **Secrets:** keys, tokens, passwords, credentialed URLs, `.env` content, Databricks/Azure/AWS/
     Hugging Face tokens. Any real credential is 🔴 Blocking.
   - **PHI / real data:** real notes, names, dates of service, MRNs, employer data, files that belong
     in `data/raw/` (ASQ-PHI, the John Snow Labs CSV, i2b2/n2c2). Fake PHI from the generators is
     expected; anything that could be real is 🔴 Blocking.
   - **Organization claims:** text describing any organization's plan, study, finding or partnership;
     company claims without a citation (`CLAUDE.md` ground rules). 🔴 Blocking.
3. **Reviewer.** Use Superpowers `requesting-code-review`: a read-only reviewer subagent over the
   range, with this rubric and `CLAUDE.md` appended to the requirements.
4. **Verify.** Use Superpowers `receiving-code-review`: reproduce or trace each finding against the
   code before writing it down. Drop what doesn't survive. Severity: Critical → 🔴 Blocking,
   Important → 🟡 Should fix, Minor → 🔵 Nit.
5. **Checks.** Read CI on `HEAD_SHA` (`python`, `postgres`, `r-parity`, `bundle`). Run locally what CI
   can't show: `cd python && pytest -q tests`, `ruff check` on changed Python files.

## Repo rules (the compliance table)

| Rule | What to check |
|---|---|
| No secrets | Scan result above |
| Synthetic only, no PHI | Scan result above; `data/raw/` untouched in git |
| No organization claims; vendors cited | Scan result above; prices and vendor figures name a source |
| Test first | Every behaviour change has a test that would have failed before it |
| Python and R in parity | Changes to labels, scoring, reliability or cost-effectiveness touch both sides; `r-parity` green |
| Simulated is labelled simulated | `simulated_*` files, `sim:` / `calib:` methods; no dry-run number presented as a result in README or docs |
| Seeds fixed | New generators and samplers take a seed with a fixed default |
| Paths | `dental_omop_nlp.paths`, never a hard-coded `data/` |
| Spec for big changes | A dataset, metric, label rule or review-workflow change has a `specs/NNN-*/` entry (spec, tasks updated) |
| Prices | Service prices name their source and date; placeholders say ILLUSTRATIVE |
| Commits | Imperative subject, body says why, co-author trailer when an agent wrote it |
| Docs | README stays about 3 printed pages; plain-language docs updated when behaviour changes |

## Output

Write `pull_requests/pr-<n>-review.md` (or `pull_requests/<branch-slug>-review.md` before a PR exists),
overwriting any earlier review of the same PR:

```markdown
---
pr: <n>
branch: <branch>
title: "<PR title>"
author: <login>
reviewed_at: <YYYY-MM-DD>
reviewer: superpowers requesting-code-review subagent + coordinator verification
verdict: approve | approve-with-nits | request-changes
---

# PR Review: <title>

## Summary
<3-6 sentences: what it does, whether it works, the verdict and why>

## Scope of Change
- Files changed: N (+A / -D, excluding generated data)
- Areas touched: python / r / databricks / docs / specs / data
- Commits: <sha> <subject>, one per line
- Range reviewed: `BASE..HEAD`

## CI Status
| Check | Status |
|---|---|

## Secrets, PHI and Claims Scan
<result of each scan; "clean" or the findings>

## Strengths

## Findings
### 🔴 Blocking (Critical)
### 🟡 Should fix (Important, non-blocking)
### 🔵 Nits / suggestions (Minor)
<each: file:line, what's wrong, how it was verified, the fix>

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|

## Test Coverage
<what's tested, what isn't, what was run locally>

## Verdict
<approve / approve-with-nits / request-changes, and what must change first>
```

Review files are working notes: not committed (`.gitignore`), not posted to GitHub unless asked.
