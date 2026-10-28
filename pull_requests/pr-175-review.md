---
pr: 175
branch: fix/174-nhanes-site-abbreviations
title: "Read NHANES sites from the abbreviations in the real labels"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: coordinator review after merge (recorded under #176)
verdict: approve
---

# PR Review: Read NHANES sites from the abbreviations in the real labels

## Summary
`sites_from_labels` reads the site tokens the real OHXPER files use (`DF`, `MdF`, `MF`, `DL`, `MdL`, `ML`) as whole
words, because `DF` is inside `MdF`. It keeps the full-word fallback. The earlier word list didn't match the real
files. Verified against the 2009–2014 CDC files and by running the job. Approve.

## Scope of Change
- Files: `nhanes.py`, `test_nhanes.py` (+22 / -3)
- Commit: `d856af5`; merged as `59960e9`

## CI Status
| Check | Status |
|---|---|
| python, postgres, r-parity, bundle, azure-infra, check | success on `d856af5` |

## Secrets, PHI and Claims Scan
Clean. The test holds real NHANES variable labels: public CDC metadata, no person-level data.

## Findings
None. The prevalence printed by the local check is close to the published figures (e.g. ACES Stage 4 12.6% vs
12.4% in Tay et al. 2025). That is a sanity check of the site mapping, as spec 013 G4 intends, not a new finding.

## Repo-Rule Compliance
Test first (the real-label test reproduced the job's exact `ValueError`), R not affected, no settings change.

## Verification on Databricks
NHANES perio run `797567382684027` on `59960e9`: **TERMINATED SUCCESS**. Aggregates are written to
`landing_perio_bench/data/nhanes`.

## Verdict
**approve.**
