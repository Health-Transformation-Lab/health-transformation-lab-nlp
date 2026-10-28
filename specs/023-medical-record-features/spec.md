# Feature Specification: synthetic medical-record features for the status classifier

**Feature Branch**: `spec/198-023-medical-record-features`

**Created**: 2026-10-28

**Status**: draft

**Input**: "Synthetic medical-record features for the status classifier, after Patel 2026. The generator adds
seeded synthetic systemic conditions (diabetes, hypertension, CKD and others), HbA1c, blood pressure and ASA
class, plausibly linked to periodontal status. The classifier runs dental-only, dental+medical and
medical-only, mirroring the paper's experiments 1 and 5, on synthetic data labelled synthetic. R parity
applies where scoring changes."

> Personal learning project; synthetic data; published sources only (`DISCLAIMER.md`). The paper this follows
> is Patel JS, Tellez M, Katiyar R, et al., *Periodontitis prediction model using linked electronic health and
> dental records*, JDR Clin Trans Res 2026;11(4):555–570 ([references](../../docs/references.md), item 53).
> Its data is real patient data and never comes into this repo. Only its design and its published figures are
> used, and the figures only as cited reference points.

## Why

Spec 013 G10 built the status classifier (`classify_status.py`) on dental-record features: the chart, age,
smoking, diabetes and HbA1c. Patel et al. 2026 asked whether medical-record features add to dental ones, using
three feature sets:
- dental records only (experiment 1): average AUC 84%;
- dental and medical records (experiment 1): 86%;
- medical records only (experiment 5): 57%.

All three are from Table 2, averaged over 4 classes. The paper found dental factors dominated, and medical
conditions added little overall.

The repo can't test that claim: it has no medical-record side. This spec adds one, synthetic and seeded, so
the same three-way comparison runs here end to end. On synthetic data, the comparison shows only that the
pipeline works and how the generator's links come through. It says nothing about real patients, and every
output says so.

## User Scenarios & Testing

### User Story 1 - The synthetic visits carry seeded medical-record features (Priority: P1) #198

Each synthetic person gets a medical record:
- **Systemic conditions:** diabetes, hypertension, chronic kidney disease, cardiovascular disease, and the other
  groups the paper lists among contributing conditions (respiratory, haematologic, and endocrine/metabolic other
  than diabetes).
- **Measures:** an HbA1c when one is measured, systolic and diastolic blood pressure, and ASA physical-status
  class (I–IV).

The conditions are linked plausibly to periodontal status. Each link is a direction and size taken from a
published, cited source, so a model can find a signal, but a weak one.

**Why this priority**: nothing else in this spec can run without the features.

**Independent Test**: generate a study with a fixed seed twice and get identical files. Check that:
- every existing column is unchanged from before this spec;
- the new columns have the declared types and ranges;
- each condition's rate is higher in periodontitis than in health, by about the declared amount, within
  sampling error.

**Acceptance Scenarios**:

1. **Given** the default seed, **When** the study datasets are rebuilt, **Then** every file that existed
   before is byte-identical, and the medical record is a new file (`medical_record.csv`, one row per person,
   joined on `person_id`).
2. **Given** a person with diabetes in the existing generator (HbA1c ≥ 6.5), **When** the medical record is
   drawn, **Then** diabetes is recorded with that same HbA1c: the two never disagree.
3. **Given** 10,000 generated people, **When** each condition's rate is compared by periodontal status
   within age bands, **Then** the age-adjusted (Mantel–Haenszel) odds ratio is within the declared tolerance
   of the value the generator was given. The generator conditions each condition only on periodontal status
   and age band, so the adjusted odds ratio is the cited one by construction. Diabetes is the exception: it
   comes from the existing generator and is reported, not tested against a source.
4. **Given** any generated file, **When** a reader opens it or its data card, **Then** it says the medical
   records are synthetic.

---

### User Story 2 - The classifier runs dental-only, dental+medical and medical-only (Priority: P1) #199

The status classifier is trained and tested three times on the same split, mirroring the paper's experiments
1 and 5:
- dental-record features only;
- dental and medical-record features;
- medical-record features only.

It uses the paper's 4 classes (healthy, stage I, stage II, stages III+IV) and a 70/30 split, stratified by
class and kept by person. SHAP importances are reported per feature set. The results page puts the three runs
side by side, labelled synthetic. Next to them, it may cite the paper's averages as published reference
points, never as a target or a replication.

**Why this priority**: it is the comparison the paper makes and the reason for US1.

**Independent Test**: run the comparison script with a fixed seed. It writes one row per feature set and class
with the US3 metrics, the feature list it used, and an `is_simulated`-style synthetic flag, and is reproducible.

**Acceptance Scenarios**:

1. **Given** the study data, **When** the comparison runs, **Then** each feature set uses exactly its declared
   features, and none of them uses any feature the label was computed from directly, unless it's declared.
2. **Given** the 70/30 split, **When** it is drawn, **Then** class shares in test and train differ by at most
   one visit per class from proportional, and no person is in both.
3. **Given** the results, **When** they're written to docs or Databricks, **Then** they are marked synthetic,
   and any figure from the paper names the paper, its table and its population.

---

### User Story 3 - Per-class sensitivity, specificity, AUC and Brier score, the same in R (Priority: P2) #200

For each class, one-vs-rest, the comparison reports sensitivity, specificity, AUC and Brier score, plus their
class averages, as Table 2 of the paper does. These are scoring functions, so Python and R give the same
numbers to 1e-9 on the same predictions.

**Why this priority**: the metrics make the three runs comparable with each other and with the published
table; parity is a repo rule for scoring.

**Independent Test**: on a fixed table of labels and class probabilities, Python and base R give identical
metrics. Hand-worked cases include a perfect model, a constant model and a class missing from test.

**Acceptance Scenarios**:

1. **Given** class probabilities that sum to 1, **When** the Brier score is computed, **Then** it is the mean
   over visits of the squared error for that class, one-vs-rest, and its average is the mean over classes.
2. **Given** the parity inputs, **When** `r/tests/test_parity.R` runs, **Then** the new metrics match Python to
   1e-9.

### Edge Cases

- **A class with no test visits:** its AUC is undefined and reported as missing, not zero. Averages are taken
  over the classes present, and the report says how many there were.
- **HbA1c not measured** (most people without diabetes): it stays missing, not imputed to a normal value. The
  medical-only set must handle a missing value, as the current classifier already does.
- **ASA class:** the paper counts it among the dental-record factors (its abstract lists it with oral hygiene,
  periodontal treatment and smoking). It goes in the dental set. ASA class reflects systemic disease, so it
  carries medical signal into the dental-only run, as it does in the paper. A fourth run, dental without ASA,
  shows how much.
- **Medical-only runs that do worse than chance in a class:** reported as they are.
- **Smaller runs (`limit`):** they keep the stratification or fail clearly, never silently unstratified.

## Requirements

### Functional Requirements

- **FR-001** The medical record is drawn from its own seeded random stream, after the existing draws, and is
  written to its own file (`medical_record.csv`), so the existing datasets and every committed result built
  from them stay byte-identical. A test compares a rebuild
  against the committed files.
- **FR-002** Conditions, HbA1c, blood pressure and ASA class are declared in one table. For each one it gives:
  - the column name, following AGENTS.md naming: `is_` prefix for booleans, `_pct`, `_code` and so on;
  - the base rate by age band;
  - the odds ratio, or mean shift, by periodontal status;
  - the published source of each number, with the table or page.
  A number without a source fails a test. Existing diabetes/HbA1c from the generator is reused, not redrawn.
- **FR-003** Links run from periodontal status (and age, smoking, diabetes) to the condition. The generator
  never changes the chart or the label to fit a condition. The data card says the links are associations
  built in, not causes.
- **FR-004** `classify_status.py` takes a named feature set (`dental`, `dental_no_asa`, `dental_medical`,
  `medical`) and the
  4-class scheme (`healthy`, `I`, `II`, `III_IV`) alongside its existing 5- and 3-level ones. Gingivitis
  counts as healthy (not periodontitis), as in the existing 3-level scheme.
- **FR-005** The split is 70/30, stratified by class and grouped by person, with a fixed default seed. The
  existing 80/20 split stays the default for the existing schemes.
- **FR-006** The metrics are sensitivity, specificity, AUC and Brier score per class, one-vs-rest, plus their
  class means. Each has a base-R twin, and `r/tests/test_parity.R` checks it to 1e-9. Fitting the model stays
  Python only (spec 013 FR-007).
- **FR-007** A script writes the comparison as a CSV under the results folder, with a synthetic marker in its
  name and its rows. Its numbers go to `docs/results.md` only through the existing results path, labelled
  synthetic. The paper's averages may appear beside them, cited to Table 2, never mixed into the same column.
- **FR-008** PROBAST and TRIPOD-AI: `docs/` gets a checklist page for this classifier. It names which items
  apply to a synthetic benchmark and which don't (spec 013 G10 suggests both).
- **FR-009** Gold tables, if the results go to Databricks, follow the SQL naming rules (`fact_`/`dim_`, column
  suffixes) and `gold_names.to_gold`.

### Key Entities

- **Medical record** (one row per synthetic person, in `medical_record.csv`): conditions as `is_` booleans
  (`is_hypertension`, `is_ckd`, ...); systolic and diastolic blood pressure (`systolic_bp_mmhg`,
  `diastolic_bp_mmhg`); ASA class (`asa_class_code`, I–IV). HbA1c is not repeated: the existing visit column
  `hba1c` is reused. CSV columns keep these analysis names. If the comparison goes to gold, the
  implementation PR declares their gold names in `gold_names.py` and adds a `_mmhg` row to AGENTS.md's
  suffix table, since no suffix there holds a pressure.
- **Feature set**: a named list of features: dental, dental+medical, medical.
- **Comparison row**: feature set × class → sensitivity, specificity, AUC, Brier score, test count, seed,
  synthetic flag.

## Success Criteria

- **SC-001** A rebuild with the default seed leaves every existing dataset file unchanged and adds the medical
  record, twice in a row identically.
- **SC-002** Every number in the condition table names its published source; none is invented.
- **SC-003** The comparison runs end to end in under 10 minutes on a laptop CPU for the default study size.
  It reports the three feature sets with all four metrics per class.
- **SC-004** The R parity test covers the new metrics and passes.
- **SC-005** No page or table shows a synthetic result without saying it is synthetic. Every figure from the
  paper names its source.

## Assumptions

- The paper's 4-class target has no gingivitis class; gingivitis is grouped with healthy here (FR-004). This is
  a choice, not the paper's.
- Medical-only means the medical-record features plus age. The generator has no sex column (spec 013 G11
  lists it as missing), so sex is left out rather than added here. Smoking and ASA class are dental-record
  factors, as in the paper's abstract.
- Condition rates and links will come from published population sources (for example NHANES-based
  prevalence) and published periodontitis–systemic association studies. Each is to be checked against its
  paper before use, and listed in the plan's research section. None of the paper's own patient-level data is
  used.
- The classifier keeps XGBoost; the paper's other three models (naive Bayes, random forest, LightGBM) are out
  of scope.

## Out of scope

- Any real medical or dental record, or anything from the paper's data.
- The paper's experiments 2–4 (raw codes, aggregated codes, disease-complexity system): the synthetic record has
  no code-level detail to reduce.
- Changing the existing 5- and 3-level schemes or their results.
