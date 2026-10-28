# PR review rubric (shared by /create-pr and /pr-review)

Adapted from the open-navigator `/create-pr` review flow (Superpowers code-review skills,
verified findings only, mandatory secrets scan), with this repo's rules from `AGENTS.md` (and `CLAUDE.md`),
`DISCLAIMER.md` and `.specify/memory/constitution.md`.

## How the review runs

1. **Range.** `BASE_SHA` = merge base with `main`; `HEAD_SHA` = branch head. Review only
   `BASE_SHA..HEAD_SHA`. Leave out generated outputs from the line counts (`data/**/*.csv`,
   `data/**/*.json`, notebooks' outputs) but still scan them (step 2).
2. **Scans, before any reading for style.** Run all three on the diff, including data files:
   - **Secrets:** keys, tokens, passwords, credentialed URLs, `.env` content, Databricks/Azure/AWS/
     Hugging Face tokens. Any real credential is 🔴 Blocking.
   - **PHI / real data:** real notes, names, dates of service, MRNs, employer data, files that belong
     in `data/raw/` (ASQ-PHI, the John Snow Labs CSV, i2b2/n2c2). Public, redistributable datasets in
     `data/external/<name>/` with a source-and-licence README are allowed (constitution v1.2.0). Fake PHI from the generators is
     expected; anything that could be real is 🔴 Blocking.
   - **Organization claims:** text describing any organization's plan, study, finding or partnership;
     company claims without a citation (`AGENTS.md` ground rules). 🔴 Blocking.
3. **Reviewer.** Use Superpowers `requesting-code-review`: a read-only reviewer subagent over the
   range, with this rubric, `AGENTS.md` and `CLAUDE.md` appended to the requirements.
4. **Verify.** Use Superpowers `receiving-code-review`: reproduce or trace each finding against the
   code before writing it down. Drop what doesn't survive. Severity: Critical → 🔴 Blocking,
   Important → 🟡 Should fix, Minor → 🔵 Nit.
5. **Deck figures (when a PR touches `docs/<deck>/slides/` or `docs/claims.yaml`).** For each changed figure, open
   the source its `docs/claims.yaml` entry names and re-derive the number: a measured figure from the repo file, a
   cited one from the source itself (set `checked` to today's date only after reading it), a derived one from its
   inputs. Then read the slide's sentence against the entry's `covers`: the wording must not claim more than the
   source shows (a wider population, a larger model, "even", "any", "cheap"). An unchecked or widened claim is
   🟡 Should fix; a figure that doesn't match its source is 🔴 Blocking.
6. **Checks.** Read CI on `HEAD_SHA` (`python`, `postgres`, `r-parity`, `bundle`). Run locally what CI
   can't show: `cd python && pytest -q tests`, `ruff check` on changed Python files.

## Repo rules (the compliance table)

| Rule | What to check |
|---|---|
| No secrets | Scan result above |
| Synthetic only, no PHI | Scan result above; `data/raw/` untouched in git; anything real is a public, redistributable dataset in `data/external/<name>/` with a README (constitution v1.2.0) |
| No organization claims; vendors cited | Scan result above; prices and vendor figures name a source |
| Test first | Every behaviour change has a test that would have failed before it |
| Python and R in parity | Changes to labels, scoring, reliability or cost-effectiveness touch both sides; `r-parity` green |
| Simulated is labelled simulated | `simulated_*` files, `sim:` / `calib:` methods; no dry-run number presented as a result in README or docs |
| Seeds fixed | New generators and samplers take a seed with a fixed default |
| Paths | `health_transformation_lab_nlp.paths`, never a hard-coded `data/` |
| Spec for big changes | A dataset, metric, label rule or review-workflow change has a `specs/NNN-*/` entry (spec, tasks updated) |
| Prices | Service prices name their source and date; placeholders say ILLUSTRATIVE |
| Deck figures | Every slide figure is in `docs/claims.yaml` (`test_deck_claims.py`); changed figures re-derived from their sources (step 5) |
| Commits | Imperative subject, body says why, co-author trailer when an agent wrote it |
| Docs | README stays about 3 printed pages; plain-language docs updated when behaviour changes |
| Configuration | New or changed settings are declared once (bundle variable or documented env var), checked before work starts, and the PR says which environments change |
| Secrets register | A credential made, rotated or newly used is in `ops/secrets_register.yaml` with its expiry and owner; no values anywhere |
| Idempotent writes | Every table write is overwrite, MERGE, or delete-then-append by batch key; rows carry their batch key; append only for event logs |
| Alerts | New alerts have a severity (SEV1–4), an owner and an action; SEV3/4 go to the digest, not straight to people |

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

Commit the review file with the PR's branch (or after merge) so the record stays in git; don't post it
to GitHub as a comment unless asked. It must pass the same scans: no secrets, PHI or real data in it.
