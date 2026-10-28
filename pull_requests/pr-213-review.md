---
pr: 213
branch: docs/209-algorithm-sources
title: "One page for where each diagnosis algorithm comes from"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator (new doc page, a test, two links)
verdict: approve
---

# PR Review: One page for where each diagnosis algorithm comes from

## Summary
This PR adds `docs/algorithms.md`: every method that assigns a periodontal status, with its source and its accuracy
from results.md. A test keeps the page complete and its numbers current. Verdict: approve.

## Scope of Change
- Files changed: 5 (new page, new test, two links, this review)
- Commits:
  - 27c72dd One page for where each diagnosis algorithm comes from
- Range reviewed: `origin/main..27c72dd`

## Rubric
- Companies and papers cited, not overclaimed: each source is a numbered reference or "this repo's own". The page
  says only part of `algorithm_design` follows Patel 2022, as the paper's full text shows.
- Synthetic results labelled: the page says every number is scored against the generator's truth, not clinical
  performance. The phenotype-order scores are called a dry run on simulated reviewers.
- Tests first: `test_algorithms_doc.py` failed before the page existed.
- Python/R parity: not affected.

## Overlap
Spec 024 (#208) implements `algorithm_patel2022` and corrects the citation in evidence_rules.md, the walkthrough
and phenotype.py. This PR touches none of those sections. Its test will need the Patel row's number when spec 024
adds the method to the results; that session has been told.

## CI Status
| Check | Status |
|---|---|
| python | 835 passed, 15 skipped locally |
| check (branch and issue) | pending |
