# Feature Specification: Realistic synthetic dental notes from published examples

**Feature Branch**: `001-realistic-dental-notes`

**Created**: 2026-10-25

**Status**: Implemented (v1)

**Input**: User description: "Use published samples to create as realistic samples as possible."

## Context

The current generator (`clinical_notes.py`) was written from general knowledge
of dental charting. Its notes are clean, and the rules that read them were
written by the same author, so rule-based scores are inflated. Published work
on real dental EHR notes (UTHealth Houston; Indiana University) shows how
diagnoses are actually written: lowercase, terse prefixes, Arabic or Roman
stages, hedging, misspellings, extent words in confusing places. The synthetic
notes should reproduce those published patterns so that the benchmark is
harder in the same ways real notes are.

Sources: `docs/note_realism.md` maps each pattern to its source.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Diagnosis lines written the way clinicians write them (Priority: P1)

As the study lead, I want the diagnosis line in synthetic notes to follow the
published real-note patterns, so that the rules and models are tested on the
variation they'll meet in the real corpus.

**Why this priority**: The diagnosis line is what every reader (rules, BERT,
LLM, reviewers) leans on. If it's unrealistically clean, every downstream
number is optimistic.

**Independent Test**: Generate 1,000 notes; check the share of each published
pattern (prefix forms, stage numerals, hedging, misspellings, extent position)
falls in its configured range, and that every pattern appears.

**Acceptance Scenarios**:

1. **Given** a periodontitis visit, **When** a note is generated in the
   "EHR progress note" style, **Then** its diagnosis line uses one of the
   published forms (e.g. `d:` / `d-` / `d :` / `Diagnosis:` prefix; stage as
   `iii` or `3`; grade with or without trailing punctuation; extent before or
   after the stage; optional "tentative diagnosis is").
2. **Given** a localized periodontitis visit with generalized recession,
   **When** the note says so, **Then** the extent reader returns `localized`
   (the published extent error case).
3. **Given** a note with a misspelled extent ("generalzied"), **When** read,
   **Then** the extent reader still returns `generalized`.

---

### User Story 2 - Readers handle the published variation (Priority: P1)

As the data engineer, I want `note_reader` to read status, grade and extent
from every published diagnosis form, so that the rule-based baseline is a fair
comparator, not a strawman.

**Independent Test**: A table of published-pattern sentences (paraphrased, not
copied) with expected status / grade / extent; every row passes.

**Acceptance Scenarios**:

1. **Given** "d- stage iii grade b periodontitis.", **Then** status = stage 3, grade = B.
2. **Given** "d: tentative diagnosis is stage 3 grade c generalized", **Then**
   status = stage 3, grade = C, extent = generalized.
3. **Given** "d : generalized plaque induced gingivitis", **Then** status = gingivitis, extent = NA.
4. **Given** a grade written as a Roman numeral ("grade ii"), **Then** grade = B.

---

### User Story 3 - Diagnosis presence matches the published rate (Priority: P2)

As the study lead, I want almost every note to carry a diagnosis section, as in
the UTHealth corpus (98.7% of records), so the share of "infer from findings
only" notes isn't overstated.

**Independent Test**: In the EHR style, the share of notes with no diagnosis
line is between 0.5% and 3%.

---

### User Story 4 - Realistic note body (Priority: P3)

As a reviewer, I want the rest of the note to read like a dental progress note
(chief complaint, medical history review, perio charting, radiographs,
diagnosis, treatment, next visit; common abbreviations), so that Label Studio
review feels like real chart review.

**Independent Test**: A dental clinician reads 20 generated notes and rates
plausibility; target ≥ 4/5 average. (Manual; tracked as a task, not a unit test.)

### Edge Cases

- Diagnosis line present but contradicts the findings (already modeled: 25% clinician disagreement). Keep.
- Copied-forward diagnosis from a prior visit. Keep; readers ignore it.
- Extent word attached to a non-periodontal finding (recession, inflammation): extent reader must not take it.
- Grade written as Roman numeral (published) vs letter.
- Gingivitis/health notes: no stage, grade or extent.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The generator MUST add an `ehr` note style whose diagnosis line
  is drawn from the published pattern catalogue (`dx_patterns.py`), each
  pattern with a configurable weight.
- **FR-002**: The catalogue MUST include: prefixes `d:`, `d-`, `d :`,
  `diagnosis:`, `Dx:`, none; stage as Roman or Arabic; grade as letter, letter
  with trailing period, or Roman numeral; extent before label, after stage, or
  absent; hedges ("tentative diagnosis is"); lower/upper/sentence case;
  misspellings of generalized/localized; the "with generalized recession" trap.
- **FR-003**: In the `ehr` style, the share of notes without a diagnosis line
  MUST be configurable and default to 1.5%.
- **FR-004**: `note_reader` MUST expose `read_grade` and `read_extent`, and
  `read_stated_dx` MUST handle every catalogue form.
- **FR-005**: Every generated note MUST record which pattern produced its
  diagnosis line (`dx_pattern` in the answer key), so errors can be broken
  down by pattern.
- **FR-006**: The R side MUST NOT need changes for this feature (no new
  reported metric); parity tests MUST still pass.
- **FR-007**: No published sentence is copied into generated data; patterns
  are re-composed from parts. Short examples quoted in docs carry citations.

### Key Entities

- **Diagnosis pattern**: id, source citation, template parts, weight.
- **Note style**: `soap`, `narrative`, `chart_summary` (existing), `ehr` (new).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every catalogue pattern appears at least once in 1,000 generated `ehr` notes.
- **SC-002**: `read_stated_dx` returns the generator's stated status on ≥ 99% of `ehr` notes that have a diagnosis line.
- **SC-003**: The extent reader is correct on 100% of "with generalized recession" trap notes.
- **SC-004**: Study datasets rebuild with the `ehr` style as the majority style; tests and parity pass.

## Assumptions

- Patterns are taken from UTHealth Houston notes (Chuang et al., arXiv 2311.10809
  and 2407.21050). Other institutions write differently; the catalogue is
  extensible, and weights are a guess until a real-note sample is profiled.
- The IEEE DataPort synthetic set is not used here (subscription; license unknown).
