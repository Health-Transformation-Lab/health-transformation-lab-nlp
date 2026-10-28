# Implementation Plan: the PerioDx phenotype method of Patel et al. 2022 (spec 024)

**Spec**: [spec.md](spec.md) · **Issues**: #201 (US1), #202 (US2), #203 (US3), #204 (US4) · **Source**:
Patel et al., Methods Inf Med 2022;61(S2):e125–e133 (references item 4), Fig. 1, Fig. 2, Table 1.

## Approach

1. **Diagnoser** (`python/health_transformation_lab_nlp/periodx.py`):
   - `diagnose(chart, age, cigarettes_per_day, diabetes, hba1c) -> PerioDxDiagnosis` follows Fig. 2 top to
     bottom: health and gingivitis, then stage, extent, grade.
   - Constants are named after the figure's boxes (`BOP_LOCALIZED_PCT = 10`, `BOP_GENERALIZED_PCT = 30`,
     `MIDDLE_THIRD_BL_PCT = 33`, `OCCLUDING_PAIRS_MIN = 10`, ...), each citing Fig. 2.
   - It reads the chart fields the generator already writes. Inputs the synthetic chart lacks (occluding pairs,
     recession, drifting/bite collapse) map from existing fields where spec 006/013 provide them (`aces.py`'s
     `occluding_pairs`, `remaining_teeth`, `complex_rehab`, `mobility_degree`), or use the documented fallback.
2. **Extractor** (same module):
   - `extract(note, negation=False) -> PerioDxDiagnosis | None`.
   - Step 1: normalise and filter on `PERIODX_TERMS`, a checked-in table of 2017 classification terms plus the
     repo's synthetic abbreviations.
   - Step 2: stem with a small suffix stripper, and match with `difflib.SequenceMatcher` at a declared
     threshold, so no new dependency. Gensim word vectors are named as the paper's choice and not reproduced.
   - With negation on, it uses the NegEx-style cue window the repo's note reader already uses, if one exists;
     otherwise a minimal cue list.
3. **Stepwise phenotype**:
   - `phenotype.py` gets `DESIGN_GROUPS`-style order `PATEL2022_ORDER = ["dx_code", "notes_periodx", "chart_periodx"]`
     and `phenotype_patel2022(row)`, which returns the label and the deciding section.
   - Wherever methods are listed, `algorithm_patel2022` joins `algorithm_design`: `grader_tables.EVIDENCE`,
     `gold_names` (`rules_patel2022_status_code`), the dashboards, and `scripts/18_phenotype_order.py`'s
     comparison.
4. **Completeness**: `completeness.section_completeness(v, sections, merged)` writes
   `data/results/data_quality/completeness_patel2022.csv`. The paper's Fig. 1 shares are cited in the doc,
   not the CSV.
5. **Scores**: the existing agreement and kappa tables pick up the method. A confusion-matrix row (TP, FP, TN,
   FN, precision, recall, F1) for the Diagnoser and for the Extractor goes against the reviewer key, using
   `reliability.py`'s functions where they match. A new function gets an R twin.
6. **R**: `r/R/14_spec024.R` mirrors `diagnose` and the stepwise order, and `make_parity_inputs.sh` writes
   charts and labels for `test_parity.R`. The Extractor is NLP, so its parity is on its outputs over a fixed
   snippet set: R reads the Python extraction table and checks the stepwise merge only.
7. **Docs (US4)**:
   - References item 4 gets the full citation, what is implemented, and the three inconsistencies.
   - `evidence_rules.md`, `code_walkthrough.md`, the `phenotype.py` comment and `action_items.md` A2: the
     exam-form-first order is the repo's; the paper's is `algorithm_patel2022`.
   - `test_rule_order_citation.py` is updated first, so it fails on today's wording.

## Tests first

- `test_periodx.py`:
  - one chart per Fig. 2 branch;
  - grade not assessable without age or bone loss;
  - bone-loss categories accepted;
  - Extractor snippets with negation off and on, abbreviations, and no-diagnosis.
- `test_phenotype.py`: the stepwise order (code beats note beats chart; exam form never used); deciding
  section reported.
- `test_completeness.py`: section and merged completeness on a hand-built table.
- `test_rule_order_citation.py`: the corrected wording.
- `r/tests/test_parity.R`: Diagnoser labels and the stepwise merge.

## Environments

None change. The gold column `rules_patel2022_status_code` reaches dev, uat and prod with their next Load
results; the implementation PR says so.
