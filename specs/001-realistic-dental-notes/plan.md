# Implementation Plan: Realistic synthetic dental notes from published examples

**Branch**: `001-realistic-dental-notes` | **Date**: 2026-10-25 | **Spec**: [spec.md](spec.md)

## Summary

Add a published-pattern catalogue for diagnosis lines and an `ehr` note style
that uses it, extend the note reader to read every catalogue form (status,
grade, extent), and rebuild the study datasets with `ehr` as the main style.

## Technical Context

**Language/Version**: Python 3.10+ (R unchanged)
**Primary Dependencies**: none new
**Storage**: CSV/JSON/Parquet under `data/` (unchanged)
**Testing**: pytest; `r/tests/test_parity.R`
**Target Platform**: laptop, Databricks Free Edition
**Project Type**: single project (library + scripts)
**Performance Goals**: generating 3,000 notes stays under 10 s
**Constraints**: synthetic only; no copied published sentences in generated data
**Scale/Scope**: catalogue of ~15 patterns; one new style

## Constitution Check

| Principle | Status |
|-----------|--------|
| I. Synthetic only, no PHI | Pass: patterns are re-composed parts, fake PHI unchanged, de-id gate unchanged |
| II. One contract, two languages | Pass: no new reported metric; R untouched; parity re-run |
| III. Test-first | Pass: reader tests and catalogue coverage tests written before code (tasks T003–T005) |
| IV. Honest outputs | Pass: weights documented as a guess; limits in `docs/note_realism.md` |
| V. Published evidence | Pass: every pattern cites its source |
| VI. Simple, seeded | Pass: no new dependency; all sampling via the existing `rng` |

## Project Structure

### Documentation (this feature)

```text
specs/001-realistic-dental-notes/
├── spec.md
├── plan.md      # this file
└── tasks.md
```

### Source Code

```text
python/dental_omop_nlp/
├── dx_patterns.py       # NEW: published pattern catalogue + renderer
├── clinical_notes.py    # add "ehr" style; record dx_pattern
├── note_reader.py       # read_grade, read_extent; broader read_stated_dx
└── study.py             # style weights; dx_pattern in answer key
python/tests/
└── test_note_realism.py # NEW
docs/
└── note_realism.md      # NEW: pattern → source table, limits
```

## Design decisions

1. **Catalogue as data, not prose.** Each pattern is a small function of
   (status, stage, grade, extent, rng) returning the line, with an id and a
   citation. Adding an institution's patterns = adding entries.
2. **Two-step realism.** Diagnosis-line realism comes from the catalogue (published).
   Body realism (sections, abbreviations) comes from common dental charting
   conventions and is flagged for clinician review (User Story 4).
3. **Readers stay rules.** No ML in the reader; it's the baseline.
4. **Weights are explicit and documented** so the clinician review or a real
   sample profile can retune them.

## Complexity Tracking

None.
