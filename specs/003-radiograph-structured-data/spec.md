# Feature Specification: Structured radiograph findings as an evidence source and model input

**Feature Branch**: `003-radiograph-structured-data`

**Created**: 2026-10-25

**Status**: In progress (vendor-neutral v1; awaiting vendor export spec)

**Input**: "Incorporate structured data extracted from radiographs to increase accuracy."

## Context

Radiographic bone loss (RBL) is one of the three severity criteria for staging
periodontitis (with interdental CAL and tooth loss), and the % RBL ÷ age ratio
sets the grade. Radiograph AI tools now return structured measurements: FDA-cleared bone-level measurement tools report the
CEJ-to-bone-crest distance in millimetres at each site; research CNNs on
bitewings detect horizontal bone loss well but miss vertical defects, and find
calculus and furcation defects with sensitivity ~0.82 and precision ~0.66
(Yavuz et al., EuroPerio10, 2022).

Today the study's seven sources don't include radiographs except as a sentence
in the note. Adding the AI's structured output gives (a) an eighth source to
compare, (b) a better rule-based algorithm when the probing chart is missing,
and (c) numeric features for the AI model, which reads text only.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Radiograph AI as an eighth source (Priority: P1)

As the study lead, I want each visit's radiograph AI output (per-tooth bone
level, % RBL, vertical defects, furcation, calculus, missing teeth) stored,
read into a status, and compared with the other sources.

**Independent Test**: The answer key has a `radiograph_ai` status column and a
summary; the method agreement and reliability tables include it.

**Acceptance Scenarios**:

1. **Given** max RBL 38% with 6 teeth missing, **When** read, **Then** stage IV is not claimed from the radiograph alone (cause of tooth loss isn't visible) and stage III is returned.
2. **Given** no bone loss on the radiograph, **Then** the reader returns `unknown` (a radiograph can't separate health from gingivitis).
3. **Given** no radiograph at the visit or a failed read, **Then** `unknown`.

### User Story 2 - Note + radiograph fusion model (Priority: P1)

As the data scientist, I want a model that uses the note text and the
radiograph features together, so we can measure how much the radiograph adds.

**Independent Test**: `fusion_tfidf_rad` trains and predicts; reliability shows
it next to `tfidf_logreg`, by difficulty level.

**Acceptance Scenarios**:

1. **Given** a visit with no radiograph, **Then** the fusion model still predicts (missing-value indicator), falling back to the text.
2. **Given** the dry run, **Then** fusion's agreement on L3 charts (no or conflicting written diagnosis) is reported against text-only.

### User Story 3 - Reviewers and the algorithm see the radiograph (Priority: P2)

Reviewers see the radiograph AI summary in Label Studio and can tick it as a
deciding source; the rule-based algorithm uses it after the probing chart.

### Edge Cases

- AI overestimates bone loss near restorations / calculus; measurement noise.
- Bitewings show posterior teeth only; anterior bone loss is invisible on BWX.
- Vertical defects are often missed by the AI.
- Images older than 12 months: excluded (flagged stale).

## Requirements *(mandatory)*

- **FR-001**: Generate per-visit radiograph AI output consistent with the chart, with documented error (bone-level noise, missed vertical defects, calculus/furcation sens 0.82 / prec 0.66, read failures).
- **FR-002**: Store the full per-tooth output as JSON and derive features: max and mean % RBL, share of imaged teeth with ≥15% RBL, vertical defect count, furcation count, calculus teeth, missing teeth, image type, present flag.
- **FR-003**: `read_radiograph` returns stage I–III from % RBL (never IV, never health/gingivitis).
- **FR-004**: `fusion_tfidf_rad` rung: TF-IDF text + scaled radiograph features + missing indicator; registered in `models.yaml` ladders.
- **FR-005**: Rule-based algorithm v0 priority: probing chart → radiograph AI → notes → codes …
- **FR-006**: Label Studio task and config show the radiograph summary; `decided_by` includes it.
- **FR-007**: OMOP: per-tooth measurements as `MEASUREMENT` rows linked to teeth via `SITE_EVENT`; local concepts added. Provenance (device, model version) recorded.
- **FR-008**: R parity holds (radiograph is just another compared method).

## Success Criteria *(mandatory)*

- **SC-001**: Radiograph source appears in method agreement, reliability, by-level and harm tables (Python = R).
- **SC-002**: Dry run reports fusion vs text-only overall and on L3.
- **SC-003**: Tests cover the reader's stage rules and the no-radiograph path.

## Assumptions

- Bone-level noise (SD 0.6 mm), failure rate (4%) and radiograph availability
  (85% of visits) are planning assumptions until vendor output on real images
  is profiled.
- Vendor-agnostic schema; any tool that outputs per-site bone level can feed it.
- Images themselves are out of scope here: only the structured output, which
  is far easier to de-identify than DICOM (no burned-in or header PHI).
