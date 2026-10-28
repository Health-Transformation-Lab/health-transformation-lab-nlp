# Where each diagnosis algorithm comes from, and how it scores

Every method in the results answers one question per chart: healthy, gingivitis, or periodontitis stage 1–4.
This page lists each one with what it reads, how it decides, where the method comes from, and its accuracy.
Some come from published work, cited by number from [references.md](references.md). Others were designed here,
and say so. Exact rules and worked examples: [evidence_rules.md](evidence_rules.md). Every model's paper and
licence: [model_inventory.md](model_inventory.md).

**Correct (95% CI)** is the share of the 240 synthetic review charts given the right status, copied from
[results.md](results.md). It is scored against the generator's truth, not clinical performance: the generator's
error rates are design choices, not measured from real clinics. `tests/test_algorithms_doc.py` fails if a number
here stops matching results.md, or if a rule phenotype or evidence reader in the results has no row.

## Rules on the whole record

Each takes the first part of the record, in a fixed order, that gives an answer.

| Algorithm | Reads | How it decides | Source | Correct (95% CI) |
|---|---|---|---|---|
| `algorithm_v0` | whole record | Gum measurements → note → diagnosis codes → exam form → procedure codes; the X-ray reading is a floor when the measurements didn't decide | this repo's own placeholder (spec 003); not from a published algorithm | 97.5 (95.4–99.2) |
| `algorithm_design` | whole record | Exam form → diagnosis codes → note → gum measurements | The study design's starting order (spec 005). Its diagnosis codes → note → charting part follows Patel et al. 2022 [[4]](references.md); putting the exam form first does not: the paper never uses an exam form (corrected throughout by spec 024) | 72.1 (66.2–77.5) |
| `algorithm_patel2022` | whole record | Diagnosis section (M1) → the PerioDx Extractor on notes (M2) → the PerioDx Diagnoser on the chart (M3), as published | Patel et al. 2022 [[4]](references.md), spec 024 ([#208](https://github.com/healthtransformationlab/health-transformation-lab-nlp/pull/208)) | not built yet |

The same rules read in other orders: `scripts/18_phenotype_order.py` scores all 24 orders of the four evidence
groups against **simulated** reviewers (`data/review/simulated_reliability_5cat/phenotype_orders.csv`). That is a
dry run, not a result.

## One part of the record alone

| Algorithm | Reads | How it decides | Source | Correct (95% CI) |
|---|---|---|---|---|
| `probing_chart` | probing chart | Stage from the worst attachment loss, raised by teeth lost and complexity; healthy or gingivitis by bleeding on probing | 2017 AAP/EFP classification [[7, 26]](references.md) | 80.4 (75.0–85.4) |
| `note_rules` | chart note | A written diagnosis in any scheme (2017 stage, pre-2017 severity, AAP case type), else the findings through the probing-chart rules | Keyword list and mapping are this repo's own; the schemes it reads are the 2017 classification and the 1999 one it replaced [[7, 8]](references.md) | 78.8 (73.3–83.8) |
| `exam_form` | exam form | The perio-status checkbox, else the PSR screening score | Mapping is this repo's own | 62.1 (56.7–68.3) |
| `proc_dx_completed` | diagnosis codes, done treatment | ICD-10-CM code on the procedure mapped to a status | Mapping is this repo's own | 45.0 (39.2–50.8) |
| `proc_dx_planned` | diagnosis codes, planned treatment | Same mapping, on planned procedures | Mapping is this repo's own | 50.0 (43.3–56.7) |
| `proc_codes_completed` | procedure codes, done | CDT treatment code mapped to a rough status | Mapping is this repo's own | 47.1 (40.8–53.3) |
| `proc_codes_planned` | procedure codes, planned | Same mapping, on planned procedures | Mapping is this repo's own | 50.8 (44.6–57.5) |
| `radiograph_ai` | X-ray bone-loss reading | 15% bone loss on at least two teeth; up to 33% stage 2, over 33% stage 3; a lower bound only | Bone-loss bands from the 2017 classification [[7]](references.md); the two-teeth rule is this repo's own (spec 003) | 17.5 (12.9–22.5) |

## AI and text methods on the note

The best of each kind; every variant is in [results.md](results.md).

| Algorithm | Reads | How it decides | Source | Correct (95% CI) |
|---|---|---|---|---|
| `modernbert-base+cw+s2+rules4` | chart note | ModernBERT fine-tuned on the synthetic training notes, class-weighted, then the stage 4 rule | Model: ModernBERT ([model inventory](model_inventory.md)); fine-tuning recipe is this repo's own (spec 002) | 91.2 (87.5–94.6) |
| `fusion_tfidf_rad+rules4` | chart note + X-ray reading | Word counts plus bone-loss features, logistic regression, then the stage 4 rule | this repo's own | 87.1 (82.9–90.8) |
| `tfidf_logreg+rules4` | chart note | Word counts (TF-IDF) and logistic regression, then the stage 4 rule | this repo's own standard baseline | 86.7 (82.5–90.8) |
| `llama-3.3-70b-instruct` | chart note | Asked for the status with no training on these notes, through Databricks | Model: Llama 3.3 70B ([model inventory](model_inventory.md)); prompt is this repo's own (spec 017) | 83.8 (78.8–88.3) |
| `medgemma-1.5-4b-it+rules4` | chart note | MedGemma asked for the status with no training on these notes, then the stage 4 rule | Model: MedGemma [[22, 23]](references.md); prompt is this repo's own (spec 004) | 77.1 (71.2–82.5) |

**Stage 4 rule (`+rules4`)**: when the keyword rules read stage 4, that replaces the model's answer, because the
trained models saw few stage 4 notes. This repo's own.

## Other models that predict status

| Algorithm | Reads | How it decides | Source | Correct (95% CI) |
|---|---|---|---|---|
| `classify_status` | recorded chart plus age, smoking, diabetes, HbA1c and prior treatment | Gradient-boosted trees (XGBoost), 80/20 split by person, 5-fold cross-validation | Design follows Patel et al. 2022, *Front Artif Intell* [[51]](references.md) (spec 013) | not in the leaderboard: a different task and split, see `data/datasets/classify_status/` |
