# Feature Specification: the PerioDx phenotype method of Patel et al. 2022

**Feature Branch**: `spec/201-024-patel-2022-phenotype`

**Created**: 2026-10-28

**Status**: draft

**Input**: "We also want to have a method that uses the methods in the article and references it." The
article is Patel JS, Brandon R, Tellez M, Albandar JM, Rao R, Krois J, Wu H. *Developing automated computer
algorithms to phenotype periodontal disease diagnoses in electronic dental records.* Methods Inf Med
2022;61(S2):e125–e133, doi:10.1055/s-0042-1757880, open access under CC BY-NC-ND 4.0
([references](../../docs/references.md), item 4).

> Personal learning project; synthetic data; published sources only (`DISCLAIMER.md`). The paper's data is
> 27,138 patients' dental records from one dental school, used under its IRB. It has no data-availability
> statement and is not public, so it can't be compared against directly, and it would never come into this
> repo anyway. The method runs on this repo's synthetic notes and charts. The paper's figures are cited only as
> published reference points from a different population.

## Why

The repo cites this paper for `algorithm_design`, its exam-form-first rule order, marked "not yet checked
against the full text" (action item A2). With the full text in hand, two things are clear:

1. **The paper describes a complete method the repo doesn't have.** It has two parts, combined in a stepwise
   phenotype:
   - **PerioDx Diagnoser** (Fig. 2): a rule tree from the periodontal chart to status, stage, extent and grade
     under the 2017 AAP/EFP classification.
   - **PerioDx Extractor**: a two-step keyword NLP program that pulls the diagnosis out of free-text notes.

   The phenotype takes the structured diagnosis (M1), then the Extractor on notes (M2), then the Diagnoser on
   the chart (M3). It reports completeness per section before and after merging (Fig. 1).
2. **The paper's order is not the one the repo attributes to it.** Its sources are the diagnosis section, then
   clinical notes, then charting. It has no exam-form or PSR step. `algorithm_design` puts the exam form first,
   so that order is the repo's own, not the paper's.

Running the paper's method as one more method, scored against the reviewer key like the rest, answers "how does
the published approach do on this benchmark" and fixes the attribution.

## User Scenarios & Testing

### User Story 1 - PerioDx Diagnoser: status, stage, extent and grade from the chart (Priority: P1) #201

A function reads a synthetic chart (and age, smoking, diabetes, HbA1c) and follows Fig. 2 as drawn:

- **Entry.** It asks three questions:
  - Is there detectable marginal bone loss?
  - Is interproximal CAL > 2 mm at 2+ non-adjacent teeth?
  - Is there buccal or lingual recession with CAL > 2 mm and PD > 3 mm at 2+ teeth?
- **No to all three.** BOP decides: < 10% periodontal health, 10–30% localized gingivitis, > 30% generalized
  gingivitis.
- **Yes to any.** It asks "any PD ≥ 4 mm".
  - Yes: a periodontitis case, so assess stage.
  - No: BOP decides between "reduced but healthy periodontium" (< 10%) and "gingival inflammation / past
    periodontitis" (≥ 10%).
- **Stage.** It checks the four III/IV criteria in the figure's order:
  - bone loss into the middle third (> 33%);
  - CAL ≥ 5 mm at 2+ adjacent teeth;
  - furcation class II/III or vertical bone loss ≥ 3 mm;
  - PD > 5 mm at 2+ adjacent teeth.

  If any criterion holds ("stage III or IV"):
  - Fewer than 10 occluding pairs gives IV.
  - With 10 or more, secondary occlusal trauma (mobility degree ≥ 2) at ≥ 5 teeth gives IV.
  - Under 5 such teeth, drifting, bite collapse, flaring or a severe ridge defect gives IV.
  - Otherwise the case goes to "tooth loss due to perio".

  If none holds, the case also goes to "tooth loss due to perio". Every path passes through this box, so stage
  I or II is never decided before it:
  - 1–4 teeth lost to periodontitis gives stage III;
  - 5 or more gives stage IV;
  - none goes to the bone-loss box: BL < 15%, PD 4 mm, CAL 1–2 mm is stage I; BL 15–33%, PD 5 mm, CAL 3–4 mm
    is stage II.

  The figure's dead end: a III/IV case with no complexity factor and no teeth lost reaches the bone-loss box,
  which has no branch for BL > 33%. This is parameter `III_IV_NO_TOOTH_LOSS`, default stage III (the criteria
  already placed it at III or IV, and nothing pointed to IV). Charts that meet the stage I and stage II
  measures at once go to the higher stage.
- **Extent.** Count the share of teeth lost to periodontitis or with CAL/PD at the case's stage. The figure
  gives these pairs:

  | Stage | A tooth is involved when |
  |---|---|
  | III/IV | CAL ≥ 5 and PD ≥ 4, or CAL 3–4 and PD ≥ 6 |
  | II | CAL 3–4 and PD 4–5, or CAL 1–2 and PD ≥ 5 |
  | I | CAL 1–2 and PD = 4 |

  Under 30% is localized, 30% or more generalized, or a molar/incisor pattern.
- **Grade.** It follows % bone loss / age.
  - Under 0.25:
    - A current smoker goes to "≥ 10 per day": yes is C, no goes on to "HbA1c ≥ 7.0".
    - A non-smoker with diabetes goes to "HbA1c ≥ 7.0".
    - A non-smoker without diabetes gets A.
  - "HbA1c ≥ 7.0": yes is C, no is B.
  - From 0.25 to 1.0: the arrow enters at "≥ 10 per day", so the result is C or B, never A.
  - Over 1.0: C.

Every threshold cites the figure. Where the figure's arrows leave a step open, the step is a named parameter
whose default is the reading the spec records (FR-002).

**Why this priority**: the Diagnoser fills 51% of the paper's final cohort; it is the core of the method.

**Independent Test**: hand-built charts, one through each branch of Fig. 2, give the figure's answer. The R
twin gives the same labels on the parity inputs.

**Acceptance Scenarios**:

1. **Given** a chart with no bone loss, no qualifying CAL or recession, and BOP 25%, **When** the Diagnoser
   runs, **Then** it returns localized gingivitis.
2. **Given** bone loss of 40%, 12 occluding pairs, no mobility ≥ 2, no bite collapse and 2 teeth lost to
   periodontitis, **When** it runs, **Then** it returns stage III.
3. **Given** bone loss of 10%, no III/IV criterion and 2 teeth lost to periodontitis, **When** it runs,
   **Then** it returns stage III: tooth loss is checked before stage I or II.
4. **Given** the parity inputs, **When** `r/tests/test_parity.R` runs, **Then** Python and R agree on every
   label.

---

### User Story 2 - PerioDx Extractor: the diagnosis from notes by keyword (Priority: P1) #202

The Extractor reads a note and, as the paper describes, works in two steps:
1. Normalize the note (case, special characters, stop words) and keep it only if it mentions a periodontal
   diagnosis, using a bag of words from the 2017 classification's extent, stage, grade and severity terms.
2. Read extent, stage and grade with stemming and string similarity against that word list.

The output is the most specific diagnosis the words support, or "no diagnosis". Negation is off by default,
as published; the paper names missed negation ("not the presence of bone loss") and abbreviations ("ging",
"st. 2 perio") as its error sources. A switch turns negation on, so both versions can be scored.

**Why this priority**: notes are the paper's second source, and the repo's synthetic notes include exactly
these abbreviations and negations, so the published error modes can be measured.

**Independent Test**: a fixed set of synthetic note snippets, including negated and abbreviated ones, gives
expected outputs with negation off and with it on.

**Acceptance Scenarios**:

1. **Given** "Generalized periodontitis Stage III Grade B", **When** the Extractor runs, **Then** it returns
   generalized, stage III, grade B.
2. **Given** "no evidence of bone loss, gingivitis localized", **When** it runs with negation off, **Then** it
   may report periodontitis (the published behaviour). With negation on, it returns localized gingivitis.
3. **Given** a note with no periodontal terms, **When** it runs, **Then** it returns no diagnosis, not
   healthy.

---

### User Story 3 - The stepwise phenotype, scored like the other methods (Priority: P1) #203

A new method, `algorithm_patel2022`, gives each visit the first available of:
- M1, the structured diagnosis: the repo's diagnosis codes, completed then planned;
- M2, the Extractor on the chart note;
- M3, the Diagnoser on the probing chart.

The exam form is not used: the paper has none. The method reports completeness per section, and of the merged
result, as Fig. 1 does. It is scored against the reviewer key with everything else: agreement, kappa, the
order comparison (spec 005) and the data-quality tables. It also gets the paper's confusion matrix, with
precision, recall and F1, for the Diagnoser and the Extractor separately.

**Why this priority**: it is the method the user asked for, and the reason for US1 and US2.

**Independent Test**: on the 240 review visits, the method has a value for every visit that has any of the
three sections. Its scores appear in the existing method tables, and the completeness table shows each
section's share before and after.

**Acceptance Scenarios**:

1. **Given** a visit with a completed diagnosis code, **When** the phenotype runs, **Then** the code decides,
   and the notes and chart are not read.
2. **Given** a visit with no code and a note with no diagnosis, **When** it runs, **Then** the chart decides.
3. **Given** the results pages, **When** they show the paper's published figures, **Then** each is cited as
   the paper's own, on real records, beside this repo's synthetic result, never in the same column. The
   figures are: completeness of 36%, 18% and 80% by section, rising to 100%; Diagnoser F1 97%; Extractor
   F1 95% (as stated; inconsistent with its own 91% precision and 87% recall, see Edge Cases).

---

### User Story 4 - Check A2 against the full text and correct what cites the paper (Priority: P2) #204

Item 4 in `docs/references.md`, `docs/evidence_rules.md`, `docs/code_walkthrough.md`, the `phenotype.py`
comment and `docs/action_items.md` A2 say what the paper supports:
- its order is diagnosis section, then notes, then chart;
- the exam form first is the repo's own choice;
- `algorithm_patel2022` is the paper's order.

`test_rule_order_citation.py` changes with them.

**Why this priority**: a citation that says more than the paper does is a correctness problem in the docs,
but it is quick to fix once US3 names the paper's own order.

**Independent Test**: the citation test fails on the current wording and passes on the corrected one.

**Acceptance Scenarios**:

1. **Given** the rules page, **When** a reader looks up `algorithm_design`, **Then** it says the exam-form-first
   order is the repo's, and points to `algorithm_patel2022` for the paper's.

### Edge Cases

- **Charts missing what a Fig. 2 step needs** (no bone-loss reading, no occluding-pair count): the step uses
  the parameter's documented fallback, and the visit is counted as decided on partial data.
- **Bone loss recorded as the paper's form categories** (< 15%, 15–33%, > 33%) rather than a percentage: both
  are accepted.
- **Grade without age or bone loss:** "grade not assessable", not a default B. This differs from
  `labels.grade_of`; the paper's figure has no default.
- **Notes with several diagnoses** (history and current): the Extractor takes the most severe current one,
  and the rule is a parameter.
- **The paper's own inconsistencies,** recorded in the reference entry and not resolved by guessing:
  - **Fig. 1 vs the text.** The text puts diagnosis codes at 36% (n = 9,834) and notes at 18% (n = 4,867).
    Fig. 1 attaches those two figures to the other section.
  - **Extractor scores.** The text gives 91% precision and 87% recall, which makes F1 0.89, not the 95% it
    states. Table 1 shows recall 1.0 (0 false negatives).
  - **Table 1.** It gives 112 actual positives but 224 true positives with 0 false negatives, and a
    prevalence of 0.59 where 224/400 = 0.56.
  - **HbA1c annotation bands.** "Normal < 5" and "pre-diabetes 5.7–6.4" leave 5.0–5.7 unassigned.

## Requirements

### Functional Requirements

- **FR-001** `periodx.py` holds the Diagnoser and the Extractor; R twins sit in `r/R/` and are checked by the
  parity test to 1e-9 for any number, and exactly for labels. Every public function is `@traced`.
- **FR-002** Every Fig. 2 threshold and every reading of an unclear arrow is a named constant with a comment
  citing "Patel et al. 2022, Fig. 2". The spec's readings are the defaults.
- **FR-003** The Extractor's word list is a checked-in table of 2017 classification terms and the repo's
  synthetic abbreviations. It is built from the classification paper (Tonetti, Greenwell & Kornman 2018) and
  the synthetic note templates, never from real notes. It uses only libraries the repo already depends on, or
  a declared optional extra.
- **FR-004** `algorithm_patel2022` joins the method list (`grader_tables.EVIDENCE`). That means `gold_names.py` declares its
  gold column and the dashboards list it. It doesn't replace `algorithm_design` or `algorithm_v0`.
- **FR-005** Completeness per section and after merging uses `completeness.py`, so it reads like spec 013 G7.
- **FR-006** The confusion matrix is computed per status class, one-vs-rest. "Positive" means the reviewer
  key's class, and the counts are also pooled over classes; for the Extractor, "no diagnosis" counts as a
  negative prediction. Precision, recall and F1 are new scoring functions: they are written test first, with a
  base-R twin and a parity check to 1e-9.
- **FR-010** The per-visit PerioDx outputs go to a new file next to the study data (`periodx_visits.csv`), not
  into `visits_structured.csv`, so existing datasets stay byte-identical (and spec 023's rebuild test holds in
  either merge order). `scripts/18_phenotype_order.py` keeps its 24 orderings of the four design groups; the
  paper's order is scored as one extra row, not added to the permutations.
- **FR-007** Published figures appear only with a citation to the paper's figure or table and the words "real
  records, one dental school". They are never computed into this repo's results.
- **FR-008** References item 4 gains the DOI, volume, pages and licence, what the method implements, and the
  inconsistencies above.

### Key Entities

- **PerioDx diagnosis**: status (health, reduced but healthy, gingival inflammation/past periodontitis,
  localized or generalized gingivitis, periodontitis), stage (I–IV), extent (localized, generalized,
  molar/incisor), grade (A–C or not assessable), and which section decided it (M1, M2, M3).
- **Section completeness**: section, visits with a value, share before and after merging.

## Success Criteria

- **SC-001** Each branch of Fig. 2 has a test chart, and all of them pass in Python and R.
- **SC-002** `algorithm_patel2022` appears in the method tables for the 240 review visits beside the existing
  methods.
- **SC-003** The completeness table shows each section's share and the merged share, as the paper's Fig. 1
  does.
- **SC-004** No document says `algorithm_design`'s order comes from the paper.
- **SC-005** Every figure from the paper names its source, and no result in the repo is presented as a
  replication.

## Assumptions

- The repo's diagnosis codes (`proc_dx_completed`, then `proc_dx_planned`) stand in for the paper's
  structured diagnosis section (SNODDS terms from a dropdown). Planned codes count after completed ones, as in
  `algorithm_design`, and the spec flags this as the repo's choice.
- The paper's Extractor also used word vectors (gensim) for similarity. A pinned, lightweight string-similarity
  measure replaces them unless the plan finds a reason not to, and the docs say so.
- The paper excludes necrotizing, aggressive and systemic-disease periodontitis; so does this method.

## Out of scope

- The paper's data, or any request for it. It is real patient data under an IRB.
- Re-annotating notes with eHOST, or the paper's inter-annotator kappa: the repo's reviewer key (spec 005)
  plays that role.
