# Feature Specification: case profiles and record-mismatch flags

**Feature Branch**: `spec/234-026-case-profiles` (the spec); then one branch per story: #234, #235, #236

**Created**: 2026-10-28

**Status**: Draft

**Input**: "Update the Genie dashboards with something like KEEPER in OMOP, to give case profiles that help in
phenotyping; ideally the key attributes could be used to find records whose recorded diagnosis doesn't fit."
KEEPER is Schuemie, Ostropolets et al., *npj Digital Medicine* 2025, cited in `docs/rag_and_vocabulary.md`
(test R6).

> Personal learning project; synthetic data only (`DISCLAIMER.md`). We find gum disease in records; we don't
> diagnose (`AGENTS.md`, "Words"). A flagged record is a **record mismatch**, a place where the recorded code
> doesn't fit the chart. That is usually a coding or charting gap, not a clinical error, and nothing here says
> a dentist got it wrong. Every number is measured on synthetic records against the generator's own truth, and
> is labelled synthetic wherever it is shown.

## Why

Reviewers, the chart review agent (spec 015) and Genie users all need the same thing to judge a visit: the
evidence that bears on it, laid out the same way every time. Today it is spread over a dozen columns of
`visits_structured`, the truth file and the plausibility checks. KEEPER showed that a standard structured
profile, grouped into fixed clinical categories, lets humans and LLMs review cases about as reliably as each
other, without reading notes.

The same profile shows where parts of a record disagree: a stage III code beside a chart with no attachment
loss, or a "healthy" code beside deep, bleeding pockets. Rules that flag those disagreements give a short list
of **records to recheck**. Because the synthetic study knows the truth, and injects charting errors on purpose,
each rule's precision and recall can be measured, not guessed.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A standard case profile for every visit (Priority: P1) #234

For each synthetic visit, the study produces a profile grouped into KEEPER's categories, adapted to
periodontal records. It holds only structured values, never note text:

| Category | What it shows for the visit |
|---|---|
| Demographics | age; clinic |
| Presentation | the recorded diagnosis codes (completed, planned) and the exam form's status |
| Visit context | visit number for the patient, whether a chart was taken, treated before |
| Measurements | max probing depth, bleeding on probing %, max attachment loss (CAL), bone loss %, teeth lost to periodontitis, % teeth involved |
| Tests and imaging | the probing-chart reading ("not taken" when no chart) and the radiograph AI reading |
| Risk factors | cigarettes per day, diabetes, HbA1c |
| Treatment | periodontal procedures completed and planned |
| Other readings | what the note reader and the rule phenotypes say |
| After the visit | the next visit's status, and any temporal-plausibility check it fails (spec 005) |

A value missing from the record is shown as "not recorded", never left out or filled in.

**Why this priority**: every other story reads the profile. It is useful on its own: a reviewer or a Genie
user can see a visit's whole record in one place.

**Independent Test**: build profiles for the study's visits. Every visit has one, every category is present,
missing values read "not recorded", and no profile contains note text.

**Acceptance Scenarios**:

1. **Given** a visit with no probing chart, **When** its profile is built, **Then** the measurements read
   "not recorded" and the probing-chart reading says "not taken".
2. **Given** a patient's last visit, **When** its profile is built, **Then** "after the visit" says there is
   no later visit.
3. **Given** any profile, **When** it is checked for note text, **Then** none is found.

---

### User Story 2 - Record-mismatch flags, scored against the truth (Priority: P1) #235

A set of named rules flags visits whose recorded code (the completed diagnosis code) doesn't fit the rest of the
record. The first set:

| Rule | Flags a visit when | Source |
|---|---|---|
| Code against the chart reading | the code's status is more than one step from the probing-chart reading (healthy, gingivitis, stage I–IV) | the study's own chart reader |
| Code higher than the chart | a stage III code (the synthetic codes stop at III), but the chart is within stage I: max CAL under 3 mm, bone loss under 15%, no tooth lost to periodontitis and max probing depth under 6 mm | 2017 AAP/EFP staging |
| Code lower than the chart | a healthy or gingivitis code, but max CAL of 3 mm or more or bone loss of 15% or more (attachment and bone loss beyond stage I, which gingivitis doesn't have) | 2017 AAP/EFP staging |
| No periodontal care | a periodontitis code, and no periodontal procedure completed or planned | study design |
| Code against the radiograph | a healthy or gingivitis code, and the radiograph AI reads stage II or worse (the synthetic radiograph AI reads only stage II or III, so the reverse can't occur) | the study's radiograph AI |
| Stage drops | a code lower than a periodontitis stage the same patient had recorded before, or no longer periodontitis (a stage never goes down under the 2017 classification, even after treatment) | 2017 AAP/EFP; spec 005 checks |

The stage-drop rule involves two visits and either code may be the wrong one: it is reported on the later visit
with the earlier visit named in its evidence, and it counts as a true flag when either visit's code is wrong.

A visit gets every rule it fails and a count of them, so the visits failing most rules sort to the top. Each
rule is scored against the generator's truth, over **the visits it can check** (they have a code and the evidence
the rule needs), with that count shown beside every score:
- **precision**: of the visits it flags, the share whose recorded code differs from the truth;
- **recall**: of the checkable visits whose recorded code differs from the truth, the share it flags;
- **only this rule**: how many of its flags no other rule makes, so a rule that adds nothing shows it;
- **injected errors**: of the injected charting errors at visits it can check, the share it flags.

The same scores for "any rule" use every visit with a code. Python and R compute the flags and scores
identically.

**Why this priority**: this is the "find records to recheck" part of the request, and the scores show which
rules are worth a reviewer's time.

**Independent Test**: hand-built visits, one per rule, each fail exactly their rule. On the study data, every
rule has a precision and recall, and the R twin gives the same flags and scores.

**Acceptance Scenarios**:

1. **Given** a stage III code with max CAL 2 mm, bone loss 10%, no tooth lost and max probing depth 4 mm,
   **When** the rules run, **Then** "code higher than the chart" flags it.
2. **Given** a visit with no probing chart, **When** the rules run, **Then** the rules that need the chart
   don't flag it, and it is counted as "not checkable" for those rules, not as passing.
3. **Given** the scored rules, **When** they are shown anywhere, **Then** they are labelled as measured on
   synthetic records against the generator's truth.

---

### User Story 3 - "Records to recheck" in the DQ grader and its Genie space (Priority: P2) #236

The EHR DQ grader dashboard (spec 019) gains a **Records to recheck** page:
- a list of flagged visits, most rules failed first, filtered by clinic and by rule;
- the selected visit's profile, by category;
- each rule's precision and recall, with how many visits it flags and how many it couldn't check.

The DQ grader's Genie space gets the profile and flag tables, instructions that follow the "Words" rule, and
sample questions, e.g. "Which visits have a stage III code but max CAL under 3 mm?" and "Show the case profile of
visit 1234."

**Why this priority**: it puts US1 and US2 where people already look, but both are usable without it.

**Independent Test**: the dashboard and Genie files build from code, `--check` passes, and the page's queries
read only the new gold tables.

**Acceptance Scenarios**:

1. **Given** the deployed dashboard, **When** a user picks a flagged visit, **Then** its profile shows beside
   the rules it failed.
2. **Given** the Genie space, **When** a user asks about mismatches, **Then** its instructions tell it to call
   them record mismatches and say the data is synthetic. (Genie's actual wording is LLM output: the test checks
   the instructions, and the dev deploy is checked by hand.)

### Edge Cases

- **Missing evidence.** A rule that needs a value the record lacks marks the visit "not checkable" for that
  rule. Not-checkable visits count in neither precision nor recall, and the count is shown.
- **No recorded code.** A visit whose completed code is unknown fails no rule (outcome "no code"); its profile
  shows the code as "not recorded".
- **Planned versus completed codes.** Completed codes are the recorded code; planned codes are shown in the
  profile but don't trigger rules (matching how the rule phenotypes treat them).
- **First visits.** The stage-drop rule needs an earlier visit with a periodontitis code; without one the visit is
  not checkable for it.
- **Few injected errors.** 45 visits carry an injected charting error and 34 of them have a code, so no rule can
  catch more than 34. Per-clinic counts of injected errors are too few to read and are shown as counts only.
- **Thresholds.** The figures above are starting values, named so they can change, and cited to the 2017
  AAP/EFP classification where they come from it. A change is a new run, not an edit to past results.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The study MUST build one profile per synthetic visit with the categories in US1, from structured
  values only.
- **FR-002**: A profile MUST show a missing value as "not recorded" and MUST NOT contain note text.
- **FR-003**: The study MUST evaluate each rule in US2 for every visit, giving fails, passes or not checkable.
- **FR-004**: Rule thresholds MUST be named parameters with the defaults above, each with its source.
- **FR-005**: Each rule MUST be scored for precision, recall, flags no other rule makes, and injected errors
  caught, over the visits it can check, with that count shown; overall and per clinic.
- **FR-006**: The flags and scores MUST be computed the same way in Python and R, covered by the parity test.
- **FR-007**: Results MUST be written to gold tables named per `AGENTS.md` "SQL and data names" (one row per
  visit and profile item; one row per visit and failed rule; one row per rule's score), each row carrying its
  batch key, written idempotently by the Load results job.
- **FR-008**: The DQ grader dashboard and Genie space MUST gain the page and tables in US3, built from code.
- **FR-009**: Every place a result appears MUST say it is synthetic, and all text MUST follow `AGENTS.md`
  "Words" (`test_wording.py` passes).

### Key Entities

- **Case profile item**: one visit, one category, one item: its value, or "not recorded".
- **Mismatch rule**: a named rule, its thresholds, their source, and the evidence it needs.
- **Record mismatch**: one visit failing one rule, with the values that triggered it.
- **Rule score**: one rule's checkable, flagged, not-checkable and code-truth-mismatch counts, precision, recall,
  flags no other rule makes, and injected errors caught, overall and per clinic.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every synthetic visit (4,343 in the current study) has a profile with all nine categories.
- **SC-002**: A reviewer can see everything structured about a visit in one view, without opening the note or
  another table.
- **SC-003**: Every rule reports precision, recall and its not-checkable count on the synthetic study, and
  Python and R agree on every flag and score.
- **SC-004**: The share of injected charting errors the rules catch is reported against its ceiling (the 34 of 45
  with a code) and beside what the existing temporal checks catch (`dq_injected_error`), so it is clear whether
  the rules add to them.
- **SC-005**: Every dashboard page, Genie answer and doc calls a flag a record mismatch, and none uses the phrases
  `AGENTS.md` "Words" lists to avoid (`test_wording.py` passes).

## Assumptions

- The profile reads the study's existing synthetic outputs (`visits_structured` and the answer key); no new
  data is generated. Sex is not in the synthetic data and is left out of demographics.
- A code-truth mismatch means the recorded completed code differs from the generator's truth status.
- The new tables sit beside `fact_visit_evidence` (statuses per visit) and `dq_injected_error` (the temporal
  checks' catch rate) and join them on `visit_id`; they don't replace them.
- The rule set is a start. Adding a rule is a change to this spec's table, with its score reported.
- The profile is built from the study's tables, which hold the same evidence as the OMOP tables KEEPER reads.

## Out of scope

- An OMOP-native profile (from `CONDITION_OCCURRENCE`, `MEASUREMENT`, `PROCEDURE_OCCURRENCE`, as KEEPER builds it).
- The profile as a tool for the chart review agent (spec 015), and test R6 (an LLM reading the note, the profile,
  or both).
- Rules on planned codes, and any rule that would say which clinician recorded a code.
