# Code walkthrough

> Personal learning project; synthetic data only. See [DISCLAIMER](../DISCLAIMER.md).

Three levels, the same way throughout: the **[README](../README.md)** says what
the study does, this page explains **how the code does it, step by step in
run order**, and each step links the **code**. The Databricks notebook
[`databricks/notebooks/00_walkthrough.py`](../databricks/notebooks/00_walkthrough.py)
has one section per step below, with a cell that shows that step's output.

Every number from these steps is from synthetic patients and simulated reviewers.

## The steps in run order

| # | Step | Command | README section |
|---|---|---|---|
| 1 | [Generate the synthetic study](#1-generate-the-synthetic-study) | `python scripts/10_build_study.py` | [Seven sources](../README.md#dental-omop-nlp) |
| 2 | [De-identify and gate](#2-de-identify-and-gate) | (inside step 1) | [Ground rules](../README.md#ground-rules) |
| 3 | [Read each source](#3-read-each-source) | (inside step 1) | [Seven sources](../README.md#dental-omop-nlp) |
| 4 | [Compare the sources](#4-compare-the-sources) | (inside step 1) | [Study process](process.md) |
| 5 | [Rule-based phenotype](#5-rule-based-phenotype) | (inside step 1) | [Staging and grading](../README.md#dental-omop-nlp) |
| 6 | [AI models read the notes](#6-ai-models-read-the-notes) | `python scripts/11_ai_predict.py --rung <id>` | [Models evaluated](../README.md#models-evaluated) |
| 7 | [Reviewers stage charts](#7-reviewers-stage-charts) | Label Studio, then `12_import_review.py` | [How results are measured](../README.md#how-results-are-measured) |
| 8 | [Reliability and the acceptance test](#8-reliability-and-the-acceptance-test) | `python scripts/13_reliability.py` | [How results are measured](../README.md#how-results-are-measured) |
| 9 | [Five categories and source order](#9-five-categories-and-source-order) | `python scripts/18_phenotype_order.py` | [Action items](../README.md#action-items) |
| 10 | [Over time: plausibility and data quality](#10-over-time-plausibility-and-data-quality) | `python scripts/20_data_quality.py` | [Action items](../README.md#action-items) |
| 11 | [Clinic prevalence](#11-clinic-prevalence) | `python scripts/19_prevalence.py` | [Action items](../README.md#action-items) |
| 12 | [Predict progression](#12-predict-progression) | `python scripts/21_predict_progression.py` | [Action items](../README.md#action-items) |
| 13 | [Site-level charts, both classifications](#13-site-level-charts-both-classifications) | `python scripts/22_build_sites.py` | [Drill-downs](../README.md#drill-downs) |
| 14 | [OMOP storage designs on Postgres](#14-omop-storage-designs-on-postgres) | `python scripts/23_site_designs.py --url ...` | [Drill-downs](../README.md#drill-downs) |
| 15 | [OMOP into Lakebase](#15-omop-into-lakebase) | `python scripts/05_load_omop_db.py --url ...` | [Drill-downs](../README.md#drill-downs) |
| 16 | [LLM judge and cost at 1M notes](#16-llm-judge-and-cost-at-1m-notes) | `14_benchmark_cost.py`, `15_judge.py`, `16_cost_effectiveness.py` | [Drill-downs](../README.md#drill-downs) |
| 17 | [MedGemma](#17-medgemma) | `11_ai_predict.py --rung medgemma-1.5-4b-it`, `17_medgemma_lora.py` | [Drill-downs](../README.md#drill-downs) |
| 18 | [Deploy: dev, UAT, prod](#18-deploy-dev-uat-prod) | `databricks bundle deploy -t <target>` | [Drill-downs](../README.md#drill-downs) |
| — | [R side and parity](#r-side-and-parity) | `python/scripts/make_parity_inputs.sh && Rscript r/tests/test_parity.R` | [Ground rules](../README.md#ground-rules) |

Commands run from `python/` unless they start with `python/` or `r/`.

## 1. Generate the synthetic study

Synthetic people with **histories**: 1–6 recall visits about six months apart,
in one of 8 clinics. Attachment and bone loss never recover; smoking and diabetes
speed progression; therapy lowers pockets and bleeding; 2% of charted follow-up
visits get a charting error (answer key only). Each visit gets all seven sources
plus a structured radiograph AI read.

- Code: [`study.py`](../python/dental_omop_nlp/study.py) `generate_visits`, `build_study`;
  [`synthetic.py`](../python/dental_omop_nlp/synthetic.py) `draw_history`, `draw_chart`, `draw_risk`;
  [`clinical_notes.py`](../python/dental_omop_nlp/clinical_notes.py) (published note styles, [note_realism.md](note_realism.md));
  [`sources.py`](../python/dental_omop_nlp/sources.py) (forms, CDT, ICD-10); [`radiograph.py`](../python/dental_omop_nlp/radiograph.py).
- Truth: [`labels.py`](../python/dental_omop_nlp/labels.py), the AAP worksheet ([staging_grading.md](staging_grading.md)).
- Output: `data/datasets/train.csv`, `review_tasks.json`, `visits_structured.csv`; `answer_key/` (truth; reviewers never see it).
- Check: `build_summary.json` (counts, de-id recall, errors injected, review mix).

## 2. De-identify and gate

Notes carry fake PHI at known positions. A regex engine with a dental allowlist
removes it; a **leak gate** drops any note where an injected value survived; a
residual scan flags anything PHI-shaped.

- Code: [`phi.py`](../python/dental_omop_nlp/phi.py), [`deid.py`](../python/dental_omop_nlp/deid.py) (`deidentify`, `leak_check`, `residual_scan`); `study.apply_deid`.
- Output: `data/datasets/deid_report.csv`. Raw notes with fake PHI stay in `data/raw/` (gitignored).
- Check: recall 1.0, nothing blocked, over-redaction 0 in `build_summary.json`.

## 3. Read each source

One status per source per visit, or `unknown` when it's silent.

- Code: [`note_reader.py`](../python/dental_omop_nlp/note_reader.py) (stated diagnosis in any scheme, else findings; copy-forward ignored);
  `sources.READERS` (exam form, CDT completed/planned, ICD-10 completed/planned); probing chart staged from the **recorded** chart;
  `radiograph.read_radiograph` (stage II–III lower bound only).
- Output: one column per source in `answer_key/review_key.csv` and `visits_structured.csv`.

## 4. Compare the sources

Pairwise agreement and kappa between sources, and how often each says anything.
This is the input to the qualitative review.

- Code: [`phenotype.py`](../python/dental_omop_nlp/phenotype.py) `agreement_matrix`, `coverage`.
- Output: `data/datasets/method_agreement.csv`, `method_coverage.csv`.

## 5. Rule-based phenotype

Two orders, both kept: the study design's starting order (exam form → diagnosis
code → note NLP → periodontal chart) as `algorithm_design`, and the earlier
placeholder (chart first, radiograph as a lower bound) as `algorithm_v0`.

- Code: `phenotype.RULES_DESIGN`, `RULES_V0`, `phenotype()`.
- Output: `algorithm_design`, `algorithm_v0` columns. Differences: [action_items.md](action_items.md) A2–A6.

## 6. AI models read the notes

Every model reads **only** the de-identified note. Baselines (rules, TF-IDF,
TF-IDF + radiograph features), the 12-model BERT ladder, and LLM readers.

- Code: [`rungs.py`](../python/dental_omop_nlp/rungs.py) `make_rung`; [`models.yaml`](../models.yaml) (Hugging Face ids, papers);
  [`llm_reader.py`](../python/dental_omop_nlp/llm_reader.py); [`scripts/11_ai_predict.py`](../python/scripts/11_ai_predict.py).
- Output: `data/datasets/ai_predictions_<rung>.csv` (LLMs also `llm_details_<rung>.csv`).
- Status: baselines run; BERT and MedGemma need Hugging Face downloads.

## 7. Reviewers stage charts

Each reviewer gets their own Label Studio project with `review_tasks.json`
and stages every chart independently, following the protocol.

- Code / config: [`labelstudio/chart_review.xml`](../labelstudio/chart_review.xml), [`labelstudio/README.md`](../labelstudio/README.md),
  [`labeling_protocol.md`](labeling_protocol.md); [`labelstudio.py`](../python/dental_omop_nlp/labelstudio.py), [`scripts/12_import_review.py`](../python/scripts/12_import_review.py).
- Dry run: `12_import_review.py --simulate 4` writes `simulated_*` files.
- Output: `data/review/[simulated_]reviewer_labels.csv`.

## 8. Reliability and the acceptance test

Fleiss' kappa across reviewers; each source, the phenotype and each AI model
against the reviewers; errors by clinical severity and by difficulty; and the
**acceptance test**: does the method agree with the reviewers at least as much
as they agree with each other ([process.md](process.md#validation-criterion-as-reliable-as-a-human-reviewer), [statistics.md](statistics.md)).

- Code: [`reliability.py`](../python/dental_omop_nlp/reliability.py) (`reliability_report`, `agreement_vs_humans`), [`harm.py`](../python/dental_omop_nlp/harm.py);
  [`scripts/13_reliability.py`](../python/scripts/13_reliability.py); R [`r/R/04_reliability.R`](../r/R/04_reliability.R).
- Output: `data/review/[simulated_]reliability/` (`methods_vs_reviewers.csv`, `agreement_vs_humans.csv`, `by_level.csv`).

## 9. Five categories and source order

The same report with healthy and gingivitis combined, and every ordering of the
four source groups scored: chosen on half the charts, reported on the other half.

- Code: `phenotype.collapse5`, `score_orders`; [`scripts/18_phenotype_order.py`](../python/scripts/18_phenotype_order.py).
- Output: `data/review/[simulated_]reliability_5cat/` (`agreement_vs_humans.csv`, `phenotype_orders.csv`).

## 10. Over time: plausibility and data quality

Conformance, completeness and plausibility checks (OHDSI Data Quality Dashboard
terms), including temporal checks: CAL or bone loss dropping, teeth regained,
periodontitis "resolving", stage dropping.

- Code: [`plausibility.py`](../python/dental_omop_nlp/plausibility.py), [`dq.py`](../python/dental_omop_nlp/dq.py); [`scripts/20_data_quality.py`](../python/scripts/20_data_quality.py); R [`r/R/06_validation.R`](../r/R/06_validation.R).
- Output: `data/datasets/data_quality/` (`dq_overall.csv`, `dq_by_clinic.csv`, `temporal_by_method.csv`, `injected_error_recall.csv`).

## 11. Clinic prevalence

Person-level (latest visit with a known status) prevalence of periodontitis and
stage III–IV per clinic, with Wilson 95% intervals, compared with NHANES 2009–2014.

- Code: [`prevalence.py`](../python/dental_omop_nlp/prevalence.py); [`scripts/19_prevalence.py`](../python/scripts/19_prevalence.py); R `06_validation.R`.
- Output: `data/datasets/prevalence/`.

## 12. Predict progression

Next-visit progression from the current visit's phenotype, chart values and
risk factors; people split 70/30; AUROC with bootstrap CI; permutation importance.

- Code: [`prediction.py`](../python/dental_omop_nlp/prediction.py); [`scripts/21_predict_progression.py`](../python/scripts/21_predict_progression.py).
- Output: `data/datasets/prediction/`.

## 13. Site-level charts, both classifications

32 teeth × 6 sites per charted exam, generated to reproduce the visit chart; the
derived-measure layer; the 2017 AAP/EFP stage and the 2012 CDC/AAP category from
the same sites.

- Code: [`sites.py`](../python/dental_omop_nlp/sites.py) (`draw_mouth`, `derive`, `aap_from_derived`, `cdc_aap`);
  [`scripts/22_build_sites.py`](../python/scripts/22_build_sites.py); R [`r/R/07_sites.R`](../r/R/07_sites.R).
- Output: `data/sites/derived.csv`, `aap_vs_cdc.csv` (site rows in gitignored Parquet).

## 14. OMOP storage designs on Postgres

The same mouths stored three ways (SITE/SITE_EVENT; pre-coordinated concepts;
site columns), the same derived query on each, results checked against Python.

- Code: [`site_designs.py`](../python/dental_omop_nlp/site_designs.py); SQL [`omop/sql/site_designs/`](../omop/sql/site_designs/);
  [`scripts/23_site_designs.py`](../python/scripts/23_site_designs.py). Findings: [site_level_omop.md](site_level_omop.md).
- Output: `data/sites/site_designs.csv`.

## 15. OMOP into Lakebase

OMOP CDM 5.4 (OHDSI Postgres DDL) + dental extension + synthetic data into any
Postgres, including Lakebase; `perio_chart` view.

- Code: [`db.py`](../python/dental_omop_nlp/db.py); [`scripts/05_load_omop_db.py`](../python/scripts/05_load_omop_db.py);
  notebook [`04_load_lakebase.py`](../databricks/notebooks/04_load_lakebase.py); DDL [`omop/ddl/`](../omop/ddl/); R full CDM [`r/R/01_etl_synthea.R`](../r/R/01_etl_synthea.R).
- Storage overall: [results_storage.md](results_storage.md).

## 16. LLM judge and cost at 1M notes

A judge calibrated against the reviewers estimates each method's accuracy on
a corpus sample; a cost model prices each method over every note.

- Code: [`judge.py`](../python/dental_omop_nlp/judge.py), [`cost_effectiveness.py`](../python/dental_omop_nlp/cost_effectiveness.py);
  scripts 14–16; [`costs.yaml`](../costs.yaml) (illustrative); SQL judge [`02_llm_judge.sql`](../databricks/notebooks/02_llm_judge.sql).
- Docs: [cost_effectiveness.md](cost_effectiveness.md), [financial_tradeoffs.md](financial_tradeoffs.md).

## 17. MedGemma

MedGemma as a note reader (local, served or simulated), a LoRA fine-tune, and
the judge family rule.

- Code: `llm_reader.py`; [`scripts/17_medgemma_lora.py`](../python/scripts/17_medgemma_lora.py); notebook [`03_medgemma_reader.py`](../databricks/notebooks/03_medgemma_reader.py).
- Docs: [medgemma.md](medgemma.md).

## 18. Deploy: dev, UAT, prod

A Databricks Asset Bundle: per-environment catalog/schema, Lakebase instance,
endpoints and GPU settings; GitHub Actions for tests and deploys.

- Code: [`databricks.yml`](../databricks.yml), [`databricks/resources/jobs.yml`](../databricks/resources/jobs.yml),
  [`.github/workflows/`](../.github/workflows/). Docs: [deployment.md](deployment.md).

## R side and parity

R twins of every computation behind a reported number (labels, scorer,
reliability and acceptance test, by level, cost-effectiveness, judge bake-off,
five categories, plausibility, prevalence, site-derived measures). The parity
test regenerates the Python outputs and compares them.

- Code: [`r/R/`](../r/R/), [`r/tests/test_parity.R`](../r/tests/test_parity.R), [`python/scripts/make_parity_inputs.sh`](../python/scripts/make_parity_inputs.sh). Setup: [r/README.md](../r/README.md).
