---
pr: 179
branch: docs/178-reveal-decks
title: "Page the decks one slide at a time, with a nav back to the site"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: superpowers requesting-code-review subagent + coordinator verification
verdict: approve-with-nits
---

# PR Review: Page the decks one slide at a time, with a nav back to the site

## Summary
`docs/build_decks.py` now builds each deck as a pinned reveal.js 5.1.0 presentation: one slide at a time,
keyboard and swipe paging, a counter, a progress bar and `#/<slide>` links. A fixed top bar links back to
healthtransformationlab.org and the other deck, and has a go-to-slide menu, a Notes toggle (N) and GitHub in a
new tab. The rebuilt decks match the builder byte for byte, and both behave as intended in Chromium at phone and
desktop widths. The first review found the disclaimer cut off with an ellipsis below about 1150 px, which hid the
synthetic-data line. That was fixed on the branch (b1ca997), along with four smaller findings, so the verdict is
approve-with-nits.

## Scope of Change
- Files changed: 4 code and test files (`docs/build_decks.py`, `python/tests/test_decks.py`), plus the two
  generated `deck.html` files
- Areas touched: docs, python tests
- Commits:
  - 5088fed Page the decks one slide at a time, with a nav back to the site
  - 2c867d7 Merge remote-tracking branch 'origin/main' into docs/178-reveal-decks
  - 82b22e1 Test that each deck pages one slide at a time and links home
  - b1ca997 Keep the deck disclaimer whole on small screens; fix review nits
- Range reviewed: `40e5eed..b1ca997`

## CI Status
| Check | Status |
|---|---|
| python | pending on b1ca997 at the time of writing |
| postgres | pending |
| r-parity | pending (no labels, scoring, reliability or cost-effectiveness change) |
| bundle | pending |

## Secrets, PHI and Claims Scan
- Secrets: clean (public CDN and site URLs only).
- PHI / real data: clean (no data files touched).
- Organization claims: clean (none added).

## Strengths
- Notes stay in each slide's `<aside class="notes">`, so reveal's speaker view (S) works with no extra code.
- Slide titles and notes go through `html.escape`. The `{{ }}` escaping for `str.format` is consistent.
- The browser Back button returns to the site, because `history:false` keeps slide changes out of history.

## Findings
### 🔴 Blocking (Critical)
None.

### 🟡 Should fix (Important, non-blocking)
- **Fixed in b1ca997.** `docs/build_decks.py`, `.disclaimer` rule:
  - `white-space:nowrap; text-overflow:ellipsis` cut the line off below about 1150 px. On phones only "A personal idea, not affiliated…" showed.
  - Verified with scrollWidth 1143 against clientWidth 375.
  - It now wraps, and `fit()` places the slide area below it. At 375 px, scrollWidth equals clientWidth and the full text shows.
  - `test_deck_disclaimer_is_never_cut_off` covers it.

### 🔵 Nits / suggestions (Minor)
- **Fixed.** Space on a focused Notes button paged the deck instead of toggling the notes. `keyboardCondition` now skips the top bar, and Space on the button now opens the notes (verified).
- **Fixed.** `fit()` ran only on toggle and slide change, so resizing with the notes open left a gap. It now also runs on `resize`; the panel and slide bottom match after a resize (verified).
- **Fixed.** reveal.js loaded from the CDN with no `integrity` attribute. All three files now carry sha384 SRI with `crossorigin`. The hashes are of the npm 5.1.0 files, and the page loads with them (verified). The decks now need the network to page, as they already did for fonts.
- **Fixed.** Element ids `jump` and `notes` could clash with a slide id taken from a file name. They are now `deck-*`. The dead `.hint` CSS was removed.
- **Kept, by request.** `scrollActivationWidth:null` keeps one-slide paging on phones rather than reveal's scroll view below 435 px. This was asked for, and a comment now says why. Slide text is small on a portrait phone, as it was before.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets | ✅ | scan clean |
| Synthetic only, no PHI | ✅ | no data touched |
| No organization claims; vendors cited | ✅ | none added |
| Test first | ✅ | the markup and disclaimer tests fail on the old builder |
| Python and R in parity | n/a | presentation only |
| Simulated is labelled simulated | ✅ | the disclaimer is now whole at every width |
| Seeds fixed | n/a | |
| Paths | ✅ | test uses `paths.REPO_ROOT` |
| Spec for big changes | n/a | presentation only; issue #178 |
| Prices | n/a | |
| Commits | ✅ | imperative subjects, bodies say why, co-author trailer |
| Docs | ✅ | builder docstring updated |
| Configuration / Secrets register / Idempotent writes / Alerts | n/a | none touched |

## Test Coverage
`tests/test_decks.py` checks that the built files match the builder, the pinned reveal.js with SRI, the link home,
one menu entry and one set of notes per slide, GitHub in a new tab, and a disclaimer that is never cut off. The
inline JS has no automated test. It was driven in Playwright at 375, 1400 and 420 px tall: paging, the jump menu,
notes, Space on the button, resize, and no console errors. Locally, `pytest -q tests` gave 765 passed, 15 skipped,
and `ruff check` was clean.

## Verdict
approve-with-nits. The one finding that mattered (the cut-off disclaimer) is fixed on the branch. Merge once CI is
green on b1ca997.
