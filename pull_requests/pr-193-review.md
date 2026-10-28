---
pr: 193
branch: docs/192-cite-rule-order
title: "Cite where the exam-form-first rule order comes from"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator (docs and a code comment, plus a test)
verdict: approve
---

# PR Review: Cite where the exam-form-first rule order comes from

## Summary
This PR cites Patel et al., Methods Inf Med 2022, as the source of the exam-form-first rule order everywhere
`algorithm_design` is defined. It says the order is not yet checked against the paper, and marks the
gum-measurements-first order as the repo's own. No behaviour changes. Verdict: approve.

## Scope of Change
- Files changed: 6 (docs, one code comment, one test, this review)
- Commits:
  - 3a72345 Cite where the exam-form-first rule order comes from
- Range reviewed: `origin/main..3a72345`

## Rubric
- Published work cited, not overclaimed: yes. Each mention says the match with the paper is unchecked (A2).
- Tests first: `test_rule_order_citation.py` failed before the edits.
- Telemetry: no public function changed.
- Python/R parity: not affected (comment only).

## CI Status
| Check | Status |
|---|---|
| python | 799 passed, 15 skipped locally |
| check (branch and issue) | pending |
