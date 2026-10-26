# dental-omop-nlp

> **Personal learning project.** Built on my own time while waiting for internal
> approvals. Not affiliated with or endorsed by any employer, institution or
> vendor, and nothing here reflects official business or research of any
> organization, including CareQuest. Synthetic data only. See [DISCLAIMER.md](DISCLAIMER.md).

Can periodontal status be phenotyped from a dental EHR, and can AI reading the
chart notes match clinicians? This repo runs that study end to end on **synthetic**
data, to learn the pipeline, the reviewer workflow and the analysis.

<img src="docs/img/process.png" alt="Study process" width="420">

**What a phenotype is:** a computable definition of a condition, meaning a rule or model that reads a
patient's record and assigns a label the same way every time. Here the label is periodontal status:
healthy, gingivitis or periodontitis stage I–IV (with grade and extent). Dental records rarely hold a
reliable assigned diagnosis, so the phenotype has to be derived from the evidence below.

**Data sources for each visit.** Here "source" means a part of the patient's dental record
(not a citation). Each one suggests a periodontal status, and they often disagree:

| # | Source | What it is | Rule-based phenotype |
|---|---|---|---|
| 1 | Chart note | Free text the clinician writes | 3rd |
| 2 | Exam form | Structured fields, e.g. PSR score, perio status | 1st |
| 3–4 | Procedure diagnoses, completed / planned | ICD-10-CM codes, e.g. K05.3x | 2nd |
| 5–6 | Procedure codes, completed / planned | CDT codes, e.g. D4341 scaling and root planing | compared, not used |
| 7 | Probing chart | Attachment loss, bone loss, teeth lost | 4th |

The phenotype takes the first source in that order with an answer; all 24 orders are scored
against the reviewers so a better one can replace it. A radiograph AI reading can only raise the stage.

**Free text:** here the chart notes are the only free text and the only AI input; real records have
more (form and chart comments, radiograph reports, referral letters): [action items](docs/action_items.md). Details: [process.md](docs/process.md).

**Two classification systems:** the 2017 AAP/EFP staging and grading, following the AAP worksheet
([PDF](https://www.perio.org/wp-content/uploads/2019/08/Staging-and-Grading-Periodontitis.pdf)),
for the truth, reviewers and LLMs ([staging_grading.md](docs/staging_grading.md)); and the 2012 CDC/AAP
surveillance definitions behind national prevalence, computed from tooth- and site-level charts
([site_level_omop.md](docs/site_level_omop.md)).

## What it does, step by step

Summary here; **[code walkthrough](docs/code_walkthrough.md)** for how the code does each
step, with links to the code; the Databricks notebook
[`00_walkthrough.py`](databricks/notebooks/00_walkthrough.py) runs one section per step.

| # | Step | Walkthrough |
|---|---|---|
| 1 | Generate synthetic patients over time (8 clinics): notes, exam forms, procedure codes and diagnoses, probing chart; fake PHI in notes | [1](docs/code_walkthrough.md#1-generate-the-synthetic-study) |
| 2 | De-identify; a leak gate blocks any note with PHI left | [2](docs/code_walkthrough.md#2-de-identify-and-gate) |
| 3 | Read each source; compare them; build the rule-based phenotype (sources in the order above) | [3–5](docs/code_walkthrough.md#3-read-each-source) |
| 4 | AI models read the notes only: baselines, 12 BERT models, MedGemma | [6](docs/code_walkthrough.md#6-ai-models-read-the-notes) |
| 5 | Reviewers stage the same charts in Label Studio | [7](docs/code_walkthrough.md#7-reviewers-stage-charts) |
| 6 | Reliability and the acceptance test, on six and five categories; all 24 source orders scored | [8–9](docs/code_walkthrough.md#8-reliability-and-the-acceptance-test) |
| 7 | Over time and at scale: plausibility, data quality, clinic prevalence, progression | [10–12](docs/code_walkthrough.md#10-over-time-plausibility-and-data-quality) |
| 8 | Site-level charts, both classifications, three OMOP storage designs, Lakebase | [13–15](docs/code_walkthrough.md#13-site-level-charts-both-classifications) |
| 9 | 1M+ notes: LLM judge and cost; deploy to dev, UAT, prod | [16–18](docs/code_walkthrough.md#16-llm-judge-and-cost-at-1m-notes) |

Run every step (seeded, simulated reviewers): `cd python && pip install -e ".[dev]" && cd .. && python/scripts/make_parity_inputs.sh`; tests: `pytest -q python/tests`, `Rscript r/tests/test_parity.R`.

## Ground rules

- **Synthetic data only.** No PHI, real records, or employer or partner data, ever; a leak gate
  guards Label Studio and every model. **Python and R** give the same numbers (parity-tested to 1e-9).

## How results are measured

- **Acceptance test:** an AI passes if it agrees with the reviewers at least as much as
  they agree with each other (OHDSI case validation: [video](https://www.youtube.com/watch?v=scUssf863TI)
  from ~49 min, [paper](https://doi.org/10.1038/s41746-025-01433-4)).
- **Kappa** is agreement beyond chance. **95% confidence intervals** (bootstrap over
  charts) give the range the true value plausibly falls in; overlapping intervals mean two
  methods can't be called different. [statistics](docs/statistics.md)
- **Unsafe rate** and **results by difficulty**, after [GlobalDentBench](docs/dentbench_methods.md).

## Models evaluated

The 12 models from the evaluation sheet (also in `models.yaml`):

| Model · paper · domain, role | Model · paper · domain, role |
|---|---|
| [BERT base](https://huggingface.co/google-bert/bert-base-uncased) · [1810.04805](https://arxiv.org/abs/1810.04805) · general, classifier | [BiomedBERT](https://huggingface.co/microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext) · [2007.15779](https://arxiv.org/abs/2007.15779) · biomedical, classifier |
| [DistilBERT](https://huggingface.co/distilbert/distilbert-base-uncased) · [1910.01108](https://arxiv.org/abs/1910.01108) · general, classifier | [BioClinical ModernBERT base](https://huggingface.co/thomas-sounack/BioClinical-ModernBERT-base) · [2506.10896](https://arxiv.org/abs/2506.10896) · clinical, classifier, long context |
| [ModernBERT base](https://huggingface.co/answerdotai/ModernBERT-base) · [2412.13663](https://arxiv.org/abs/2412.13663) · general, classifier, long context | [BioClinical ModernBERT large](https://huggingface.co/thomas-sounack/BioClinical-ModernBERT-large) · [2506.10896](https://arxiv.org/abs/2506.10896) · clinical, classifier, long context |
| [ModernBERT large](https://huggingface.co/answerdotai/ModernBERT-large) · [2412.13663](https://arxiv.org/abs/2412.13663) · general, classifier, long context | [Clinical-Longformer](https://huggingface.co/yikuan8/Clinical-Longformer) · [2201.11838](https://arxiv.org/abs/2201.11838) · clinical, long context |
| [Longformer](https://huggingface.co/allenai/longformer-base-4096) · [2004.05150](https://arxiv.org/abs/2004.05150) · general, long context | [SapBERT](https://huggingface.co/cambridgeltl/SapBERT-from-PubMedBERT-fulltext) · [2010.11784](https://arxiv.org/abs/2010.11784) · biomedical, concept mapping |
| [SciBERT](https://huggingface.co/allenai/scibert_scivocab_uncased) · [1903.10676](https://arxiv.org/abs/1903.10676) · scientific, classifier | [GTE-ModernColBERT](https://huggingface.co/lightonai/GTE-ModernColBERT-v1) · card · general, retrieval |

Plus baselines and MedGemma ([1.5 4B](https://huggingface.co/google/medgemma-1.5-4b-it),
[27B text](https://huggingface.co/google/medgemma-27b-text-it); [arXiv 2507.05201](https://arxiv.org/abs/2507.05201)).
**Status:** all train and predict, but none has been run yet (needs the Hugging Face downloads).

## Action items

Differences from the study design and open decisions: **[docs/action_items.md](docs/action_items.md)**.
Also: [how we work](CLAUDE.md) · [references](docs/references.md) · [protocol](docs/labeling_protocol.md) · [plan](docs/plan.md) · owner John Bowyer · MIT.

## Drill-downs

| Topic | |
|---|---|
| **Diagrams**: [medallion architecture](diagrams/d0_medallion_architecture.png), study process, platform, ERD, site storage, MLOps, flows | [diagrams/](diagrams/README.md) |
| Site-level data in OMOP: 32 teeth × 6 sites, derived measures, 2017 AAP/EFP **and 2012 CDC/AAP**, three storage designs on Postgres/Lakebase, concept mapping, Atlas feasibility | [site_level_omop.md](docs/site_level_omop.md) |
| Integrated phenotype (five categories, source order), patients over time, clinic prevalence, data quality, prediction | [process.md](docs/process.md#integrated-phenotype-and-validation-spec-005), [action_items.md](docs/action_items.md) |
| Dental vs medical data in OMOP; synthetic notes, review set, public datasets | [omop_dental_vs_medical.md](docs/omop_dental_vs_medical.md), [note_realism.md](docs/note_realism.md), [data_sources.md](docs/data_sources.md) |
| MLflow, Unity Catalog models gated by the acceptance test, LLM judge; deploying to **dev, UAT, prod** | [mlops.md](docs/mlops.md), [deployment.md](docs/deployment.md) |
| Results storage and Lakebase; retrieval with OMOP synonyms and ancestors | [results_storage.md](docs/results_storage.md), [rag_and_vocabulary.md](docs/rag_and_vocabulary.md) |
| Financial trade-offs; exploratory radiograph findings and MedGemma | [financial_tradeoffs.md](docs/financial_tradeoffs.md), [cost_effectiveness.md](docs/cost_effectiveness.md), [radiograph.md](docs/radiograph.md), [medgemma.md](docs/medgemma.md) |
