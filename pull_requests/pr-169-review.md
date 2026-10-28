---
pr: 169
branch: docs/168-site
title: "A website for the lab at healthtransformationlab.org"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator (static page, workflow, tests)
verdict: approve
---

# PR Review: A website for the lab at healthtransformationlab.org

## Summary
This PR adds a one-page static site in `website/`, published by GitHub Pages at healthtransformationlab.org. It
also softens the landing README's goal to better answers and better care. Verdict: approve.

## Scope of Change
- Files changed: 5 (+242 / -7)
- Commits:
  - 8097bf3 A website for the lab at healthtransformationlab.org
- Range reviewed: `origin/main..8097bf3`

## Rubric
- Synthetic only, no PHI: yes. Every number is the README's synthetic result, with "not clinical performance".
- Personal project, not affiliated: stated in the hero tag and the footer, which links DISCLAIMER.md.
- Organization names: `test_no_org_references` passes.
- Secrets: none. The Pages workflow uses the built-in `id-token` and `pages` permissions only.
- Tests first: `test_site.py` failed before the page existed.

## Risks
- Pages must be set to "GitHub Actions" in the repository settings, or the workflow's deploy step fails.
- The README links healthtransformationlab.org before the DNS records exist, so the link is dead until then.

## CI Status
| Check | Status |
|---|---|
| check (branch and issue) | pending |
| python | 13 passed locally on the touched tests |
