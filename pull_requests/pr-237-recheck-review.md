---
pr: pending
branch: docs/237-recheck-deck-citations
title: "Say \"with teeth\" where the decks cite Eke et al. 2018; mark it checked"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator review against the rubric's deck step (a two-string change and two register entries)
verdict: approve
---

# PR Review: Say "with teeth" where the decks cite Eke et al. 2018; mark it checked

## Summary
The rubric's deck step (5), applied to the EDR problem slide: Eke et al. 2018 (PMID 29957185, read from PubMed on
2026-10-28) reports "42% of dentate US adults 30 years or older had periodontitis, with 7.8% having severe
periodontitis". The slide said "US adults 30+", a wider population than the source. It now says "with teeth" on the
slide and in the notes, and `docs/claims.yaml` records the quote and `checked: 2026-10-28`. Approve.

## Findings
None. The figures match the source exactly; only the population was narrowed to the source's.

## Checks
- `cd python && python -m pytest -q tests`: 962 passed, 15 skipped; decks rebuilt and match the builder.
- Scans: no secrets, PHI or organization claims (a published paper, cited).
- Not checkable from this session (hosts blocked): GlobalDentBench (arxiv.org), OpenAI's 40 million (openai.com),
  REDCap (projectredcap.org); they stay `checked: null` under #237.
