# Implementation Plan: synthetic medical-record features for the status classifier (spec 023)

**Spec**: [spec.md](spec.md) · **Issues**: #198 (US1), #199 (US2), #200 (US3) · **Follows**: Patel et al. 2026
(references item 53); spec 013 G10–G11.

## Approach

1. **Medical record, declared once.** `python/health_transformation_lab_nlp/medical_record.py`:
   - The table `CONDITIONS` gives each condition's column, base rate by age band, odds ratio by periodontal
     status, and source (citation plus table or page).
   - `draw_medical_record(person, status, risk, rng)` draws one record. It reuses the generator's
     `RiskFactors.hba1c`: diabetes = HbA1c ≥ 6.5, as `study.py` already decides.
   - Blood pressure is drawn from a hypertension flag (normal or raised ranges). ASA class follows from the
     number and kind of conditions (ASA Physical Status definitions: I healthy, II mild systemic disease, III
     severe systemic disease, IV a constant threat to life).
2. **Own random stream.** `study.generate_visits` keeps its current draws in the same order. The medical record
   uses `random.Random(f"{seed}:medical")` after them, so existing outputs are byte-identical (FR-001).
3. **Feature sets and scheme.** `classify_status.py` gets:
   - `FEATURE_SETS = {"dental": [...], "dental_medical": [...], "medical": [...]}`;
   - a `four` scheme (healthy+gingivitis, I, II, III+IV);
   - `split_stratified(f, seed, test_share=0.3)`, grouped by person and stratified by class;
   - `compare_feature_sets(visits, seed)`, which returns one row per feature set and class.
4. **Metrics.** `classify_status.class_metrics(y, proba)` computes sensitivity, specificity, AUC (rank-based,
   ties averaged) and Brier score per class, one-vs-rest, plus their means. Its base-R twin is
   `r/R/13_spec023.R`, and `make_parity_inputs.sh` writes a fixed prediction table for `test_parity.R`.
   Sensitivity and specificity use the arg-max class, as the paper's confusion matrices do.
5. **Script and results.** `python/scripts/44_medical_features.py --seed 0` writes
   `data/results/synthetic_medical_feature_sets.csv`. Gold names are declared in `gold_names.py` if Load
   results takes it; the plan's default is not to load it into gold until the spec is reviewed.
6. **Docs.** These pages change:
   - `docs/classify_status.md` (or the existing walkthrough section): the three runs, labelled synthetic,
     with the paper's Table 2 averages cited beside them;
   - `docs/probast_tripod_ai.md`: the items that apply and don't;
   - the data card: medical records are synthetic.

## Research (to check before any number is used)

Each source is checked against the paper itself before its figure enters `CONDITIONS`. None is used from
memory.

| Link | Candidate source |
|---|---|
| Diabetes ↔ periodontitis | Preshaw PM et al., *Periodontitis and diabetes: a two-way relationship*, Diabetologia 2012 |
| Hypertension ↔ periodontitis | Muñoz Aguilera E et al., *Periodontitis is associated with hypertension*, Cardiovasc Res 2020 |
| Cardiovascular disease ↔ periodontitis | Sanz M et al., *Periodontitis and cardiovascular diseases: consensus report*, J Clin Periodontol 2020 |
| CKD ↔ periodontitis | Chambrone L et al., systematic review of periodontitis and CKD, J Clin Periodontol 2013 |
| Base rates by age | CDC NCHS NHANES data briefs (hypertension, diabetes) and the CDC CKD surveillance system |
| ASA class | American Society of Anesthesiologists, *ASA Physical Status Classification System* |
| Respiratory, haematologic, other endocrine | named in Patel et al. 2026's results as contributing; a rate source is needed, or they're left out |

## Tests first

- `test_medical_record.py`:
  - seeded and reproducible;
  - existing columns byte-identical;
  - every `CONDITIONS` row has a source;
  - diabetes agrees with HbA1c;
  - odds ratios recovered within tolerance on 10,000 people;
  - ranges and AGENTS.md column names.
- `test_classify_status.py`:
  - the `four` scheme;
  - each feature set uses exactly its features;
  - the stratified split's shares and grouping;
  - `class_metrics` on hand-worked cases (perfect, constant, missing class).
- `r/tests/test_parity.R`: `class_metrics` to 1e-9.

## Environments

None change. If gold tables are added later, dev, uat and prod get them on their next deploy, and that PR says so.
