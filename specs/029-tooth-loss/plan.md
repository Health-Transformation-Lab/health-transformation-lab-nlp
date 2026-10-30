# Implementation Plan: tooth lost to periodontitis (spec 029)

**Spec**: [spec.md](spec.md) · **Issues**: #369 (US1), #370 (US2), #371 (US3)

## Approach

1. **Schema check (T001).**
   - Read Open Dental's published schema documentation for the eleven tables in FR-001.
   - Record each column used, with its type and meaning, in `TABLES` (`open_dental.py`), with a link to the doc
     page.
   - Columns this plan expects to use, to be confirmed:
     - `patient`: PatNum, Birthdate, Gender
     - `procedurelog`: ProcNum, PatNum, ProcDate, ProcStatus, CodeNum, ToothNum, Dx, DiagnosticCode
     - `procedurecode`: CodeNum, ProcCode, Descript
     - `treatplan` / `proctp`: plans and their planned procedures
     - `perioexam`: PerioExamNum, PatNum, ExamDate
     - `periomeasure`: PerioExamNum, SequenceType, IntTooth, ToothValue, and the six site values
     - `toothinitial`: PatNum, ToothNum, InitialType (Missing)
     - `definition`: DefNum, Category, ItemName (the diagnosis list)
     - `disease` / `diseasedef`: medical problems (diabetes, smoking)
   - Any expected column the docs don't have is dropped or replaced before code is written.
2. **Generator** (`open_dental.py`, `@traced`).
   - For each synthetic person (study visits), take the mouth `sites.draw_mouth` makes at each visit. Its
     `missing_reason` is the truth.
   - Split the person's missing teeth into missing at the first exam (`toothinitial`) and extracted during the
     record (`procedurelog`, completed, D7140/D7210, dated between exams), by the share parameters.
   - Attach `Dx` / `DiagnosticCode` to extractions by the diagnosis-rate parameters (periodontal, other, none,
     mismatch).
   - Write perio exams and measures for every visit from the site table. Medical problems come from the existing
     risk factors.
   - Own stream `random.Random(f"{seed}:open_dental")`. Output: `data/datasets/open_dental/*.csv`, plus
     `tooth_loss_truth.csv` apart from them.
3. **Bench and bundle.**
   - `schemas.LAYERS["tooth_loss_bench"] = ("bronze", "silver", "gold")`.
   - `unity_catalog.yml` declares the three schemas with `prevent_destroy`.
   - A job `tooth_loss_load`: bronze from the CSVs (overwrite per run); silver and gold from the Python
     functions; rows carry `run_id`, `run_ts` and `git_commit_sha`.
4. **Silver tooth table** (`tooth_loss.py`). `tooth_table(extract)` returns one row per patient and tooth:
   - status, the five codes in the spec;
   - loss date;
   - own last measures before the loss;
   - neighbour and mouth features;
   - tooth type, age, smoking, diabetes.

   Its base-R twin is `r/R/15_spec029.R`. (Check the next free R number at implementation time: specs 023 and
   024 have planned 13 and 14.)
5. **Model** (`tooth_loss.py`, `scripts/45_tooth_loss.py`; check the next free script number then).
   - Logistic regression (scikit-learn, standardized) and XGBoost (the `ml` extra).
   - 70/30 split, grouped by patient and stratified by label.
   - Two feature sets: shared (applied) and with own measures (comparison only).
   - Threshold fixed at 0.5, and also reported at Youden's J on the training fold.
   - Writes `data/results/synthetic_tooth_loss_{scores,calibration,stage_recount}.csv`.
6. **Stage recount.** `labels.stage4_rule` gains `expected_perio_loss`: recorded periodontal losses plus the sum of
   predicted probabilities over the unlabelled missing teeth. Stage IV when that is 5 or more. Its R twin goes in
   the same file.
7. **Docs.** `docs/tooth_loss.md` is a plain page covering:
   - the question;
   - the extract's tables, with links to Open Dental's schema docs;
   - the results, labelled synthetic;
   - what a real extract can and can't check.

## Tests first

- `test_open_dental.py`:
  - seeded and identical;
  - existing datasets unchanged;
  - every column has a source;
  - no extract column carries the truth;
  - the shares and rates are recovered within tolerance.
- `test_tooth_loss.py`:
  - each status on hand-built extracts;
  - no feature dated after the loss;
  - the shared feature set has no own measures;
  - the answer key is never a feature;
  - the split is grouped and stratified;
  - the metrics on hand-worked cases;
  - the expected-count stage rule.
- `test_schemas.py` and `test_bundle.py`: the new bench and its three schemas.
- `r/tests/test_parity.R`: statuses, the stage rule and the metrics.

## Environments

dev, uat and prod get the three new schemas and the job on their next deploy. The implementation PR says so.
