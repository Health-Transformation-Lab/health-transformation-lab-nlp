---
pr: 212
branch: docs/191-diagnosis-wording
title: "Say we find gum disease in records, not that we diagnose"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: superpowers requesting-code-review subagent + coordinator verification
verdict: approve-with-nits
---

# PR Review: Say we find gum disease in records, not that we diagnose

## Summary
Adds a "Words" rule to AGENTS.md, so every agent sees it: "diagnosis" only names what a dentist recorded, never
what our rules, models or agents do. The PR adds `python/tests/test_wording.py` to enforce it and rewords the
README and the PerioBench deck cover. The first review found the test's pattern missed common phrasings ("AI
diagnosis", "the rule diagnoses", "diagnosed by the model", "incorrect diagnosis"). It also found two live texts
that still called a method's label a diagnosis. Both were fixed in 4106b81: the pattern is now checked against
sample phrases both ways, and the two texts are reworded. Verdict: approve with nits. The remaining items are
minor and listed below.

## Scope of Change
- Files changed: 9 (+105 / -18), including the rebuilt `docs/edr/deck.html` and `full_text_and_notes.md` and a re-rendered PNG
- Areas touched: docs, python (tests; one docstring)
- Commits:
  - 6330305 Add a wording rule: we find gum disease in records, we don't diagnose
  - ba07873 Move the wording rule to AGENTS.md, check it in CI, reword README and deck
  - 4106b81 Catch more ways of saying we diagnose, and reword the two that slipped through
  - plus a merge of `main`
- Range reviewed: `c276aeb..4106b81`

## CI Status
| Check | Status |
|---|---|
| python | pending on push; locally `pytest -q tests`: 854 passed, 15 skipped |
| postgres, r-parity, bundle | not affected (no SQL, labels, scoring or bundle change); pending on push |

## Secrets, PHI and Claims Scan
- **Secrets:** clean.
- **PHI / real data:** clean. Only wording and a re-rendered cover image changed.
- **Organization claims:** clean. The excluded organization isn't named anywhere in the diff.

## Strengths
- The rule now lives in AGENTS.md, so Codex, Cursor and Copilot see it too. CLAUDE.md keeps no copy that could drift.
- The test is cheap. It reads `git ls-files`, skips binaries, and its failure message points to the rule.
- The pattern is pinned by examples that must be caught and examples that must pass ("diagnosis codes",
  "the recorded diagnosis", "Dental Diagnostic System"), so a later edit can't silently weaken it.
- The cover text agrees in all five places: slide, `deck.html`, `full_text_and_notes.md`, README alt text and PNG.
  The decks are byte-identical to a rebuild with `docs/build_decks.py`.

## Findings
### 🔴 Blocking (Critical)
None.

### 🟡 Should fix (Important, non-blocking)
Fixed in 4106b81; kept here as the record:
- `python/tests/test_wording.py`: the pattern missed "AI diagnosis", "the rule diagnoses", "BERT diagnoses",
  "we diagnose", "diagnosed by the model", "automated/model-based diagnosis", "diagnostic model" and
  "incorrect diagnosis". Verified by running each phrase against the old pattern; all now caught and tested.
- `python/health_transformation_lab_nlp/readme_results.py:295`: the docstring said "incorrect diagnosis" for a method's error. Reworded.
- `docs/dentbench_methods.md:15`: "How can a diagnosis be unsafe?" referred to a model's label. Now "a wrong label".

### 🔵 Nits / suggestions (Minor)
- `test_wording.py`: a sentence that forbids the act ("never ask the model to diagnose") is still flagged.
  That is acceptable for now. If a Genie instruction or agent prompt needs to say it, add a marker to `QUOTED`.
- `QUOTED` exempts a whole line by a marker word, which is coarse but readable. Tighten it only if it gets abused.
- `docs/code_walkthrough.md` and `databricks/notebooks/00_walkthrough.py` say "diagnostic evidence". That means
  evidence a dentist recorded, so it fits the rule and was left as is.
- The reviewer reported a wrong PR footer. That finding was dropped: the PR body ends with the required lines.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets | Yes | |
| Synthetic only, no PHI | Yes | |
| No organization claims; vendors cited | Yes | |
| Test first | Yes | The test failed on the old wording and on the missed phrases before the fixes |
| Python and R in parity | N/A | No labels, scoring, reliability or cost-effectiveness change |
| Simulated is labelled simulated | Yes | The README numbers were unchanged and are already labelled synthetic |
| Spec for big changes | N/A | A wording rule with a test; issue #191 |
| Commits | Yes | Imperative subjects, bodies say why, co-author trailers |
| Docs | Yes | README length unchanged |
| Configuration, secrets register, writes, alerts | N/A | |

## Test Coverage
`test_wording.py` covers three things: the repo-wide scan, that the rule is stated in AGENTS.md, and 20
example phrases (14 that must be caught, 6 that must pass). The full suite ran locally: 854 passed, 15 skipped.
`ruff check tests/test_wording.py` is clean. `readme_results.py` has the same 26 ruff findings as `main`, all
predating this PR, and CI doesn't run ruff. `scripts/42_build_dashboards.py --check` is clean.

## Verdict
Approve with nits. Nothing has to change before merge once CI is green.
