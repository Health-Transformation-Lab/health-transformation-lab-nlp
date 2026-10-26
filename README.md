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
healthy; **gingivitis** (bleeding gums, no lasting damage); or **periodontitis** (lost gum attachment
and bone), with a **stage** I–IV (how severe), **grade** A–C (how fast) and **extent** (how many teeth):
[in plain words](docs/staging_grading.md#in-plain-words). Dental records rarely hold a
reliable assigned diagnosis, so the phenotype has to be derived from the evidence below.

**Diagnostic evidence for each visit:** seven parts of the dental record that each suggest a
periodontal status. They often disagree:

| # | Diagnostic evidence | What it is | Phenotype order |
|---|---|---|---|
| 1 | Chart note | Free text the clinician writes | 3rd |
| 2 | Exam form | Structured fields, e.g. PSR score, perio status | 1st |
| 3–4 | Procedure diagnoses, completed / planned | ICD-10-CM codes on procedures done / on the treatment plan, e.g. K05.3x | 2nd |
| 5–6 | Procedure codes, completed / planned | CDT codes done / planned, e.g. D4341 ([planned vs completed](docs/process.md#planned-vs-completed-procedures)) | compared, not used |
| 7 | Probing chart | Attachment loss, bone loss, teeth lost | 4th |

When the evidence disagrees, the phenotype uses the first one in this order that gives a status.
The four can be ranked 24 ways (4×3×2×1); each ranking is checked against the human reviewers, and a
ranking that agrees better can replace this one. A radiograph AI reading can only raise the stage.

**Free text:** here the chart notes are the only free text and the only AI input; real records have
more (form and chart comments, radiograph reports, referral letters): [action items](docs/action_items.md). Details: [process.md](docs/process.md).

**Classification: 2017 AAP/EFP by default**, the current clinical standard for diagnosis; truth,
reviewers and AI all follow the AAP worksheet ([PDF](https://www.perio.org/wp-content/uploads/2019/08/Staging-and-Grading-Periodontitis.pdf), [staging_grading.md](docs/staging_grading.md)).
The 2012 CDC/AAP surveillance definitions, behind national prevalence, are computed too ([site_level_omop.md](docs/site_level_omop.md)).

## What it does, step by step

Summary here; **[code walkthrough](docs/code_walkthrough.md)** for how the code does each
step, with links to the code; the Databricks notebook
[`00_walkthrough.py`](databricks/notebooks/00_walkthrough.py) runs one section per step.

| # | Step | Walkthrough |
|---|---|---|
| 1 | Generate synthetic patients over time (8 clinics): notes, exam forms, procedure codes and diagnoses, probing chart; fake PHI in notes | [1](docs/code_walkthrough.md#1-generate-the-synthetic-study) |
| 2 | Remove names, dates and other identifiers; a final check holds back any note with one left | [2](docs/code_walkthrough.md#2-de-identify-and-gate) |
| 3 | Read and compare the diagnostic evidence; build the rule-based phenotype | [3–5](docs/code_walkthrough.md#3-read-the-diagnostic-evidence) |
| 4 | AI models read the notes only: baselines, 12 BERT models, MedGemma | [6](docs/code_walkthrough.md#6-ai-models-read-the-notes) |
| 5 | Periodontists label the same 240 charts, each on their own, in a labeling tool (Label Studio) | [7](docs/code_walkthrough.md#7-reviewers-stage-charts) |
| 6 | Does the AI agree with the periodontists as often as they agree with each other? Also: which order of checking the evidence agrees best | [8–9](docs/code_walkthrough.md#8-reliability-and-the-acceptance-test) |
| 7 | Over time: catch impossible changes and bad data; compare clinics; predict who gets worse | [10–12](docs/code_walkthrough.md#10-over-time-plausibility-and-data-quality) |
| 8 | Tooth-by-tooth measurements; both classifications; three ways to store them in OMOP | [13–15](docs/code_walkthrough.md#13-site-level-charts-both-classifications) |
| 9 | Scale to 1M+ notes: an AI judge spot-checks answers; costs; deploy to dev, test, production | [16–18](docs/code_walkthrough.md#16-llm-judge-and-cost-at-1m-notes) |

Run every step (seeded, simulated reviewers): `cd python && pip install -e ".[dev]" && cd .. && python/scripts/make_parity_inputs.sh`; tests: `pytest -q python/tests`, `Rscript r/tests/test_parity.R`.

## Ground rules

- **Synthetic data only**, never PHI or employer data; no note reaches Label Studio or a model until
  a final check finds no identifier left. **Python and R** give the same numbers (parity-tested).

## How results are measured

- **Acceptance test:** an AI passes if it agrees with the reviewers at least as much as
  they agree with each other (OHDSI case validation: [video](https://www.youtube.com/watch?v=scUssf863TI)
  from ~49 min, [paper](https://doi.org/10.1038/s41746-025-01433-4)).
- **Kappa** is agreement beyond chance. **95% confidence intervals** (bootstrap over
  charts) give the range the true value plausibly falls in; overlapping intervals mean two
  methods can't be called different. [statistics](docs/statistics.md)
- **Unsafe mistakes:** labels that could harm a patient if acted on, e.g. missed stage III–IV (tooth
  loss). Results also split by how hard the chart is ([details](docs/dentbench_methods.md#in-plain-words)).
- **De-identification** is scored on two numbers that pull against each other, like a spam filter.
  **Recall:** share of identifiers removed; *higher is better* (0.96 = 4 in 100 slip through).
  **Over-redaction:** share of identifier-free text changed anyway; *lower is better* (0.89 = 89 in 100
  clean notes damaged, which is bad). Best so far: hf_stanford+regex_v2+guard, recall 0.96,
  over-redaction 0.35 ([details](docs/deidentification.md#how-to-read-the-numbers)).

## Models evaluated (the 12 from the evaluation sheet; `models.yaml`)

All 12 are BERT-type models: AI that reads text and picks a label. [What is a BERT model?](docs/bert.md)

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
**Status:** DistilBERT has run (CPU, 3 epochs, 2026-10-26): on the 240 synthetic review charts it
labels 79% correctly, level with the TF-IDF (77%) and note-rule (79%) baselines; the rest are queued.
Agreement with *simulated* reviewers (kappa 0.62) is a dry run, not a result.

## Action items

Differences from the study design and open decisions: **[docs/action_items.md](docs/action_items.md)**.
Also: [how we work](CLAUDE.md) · [references](docs/references.md) · [protocol](docs/labeling_protocol.md) · [plan](docs/plan.md) · owner John Bowyer · MIT.

## Drill-downs

| Topic | |
|---|---|
| **Diagrams**: [medallion architecture](diagrams/d0_medallion_architecture.png), study process, platform, ERD, site storage, MLOps, flows | [diagrams/](diagrams/README.md) |
| Tooth-by-tooth data in OMOP; 2017 AAP/EFP **and 2012 CDC/AAP**; storage designs on Postgres/Lakebase | [site_level_omop.md](docs/site_level_omop.md) |
| Study design vs this repo; open decisions | [process.md](docs/process.md#integrated-phenotype-and-validation-spec-005), [action_items.md](docs/action_items.md) |
| Dental vs medical data in OMOP; synthetic notes, review set, public datasets | [omop_dental_vs_medical.md](docs/omop_dental_vs_medical.md), [note_realism.md](docs/note_realism.md), [data_sources.md](docs/data_sources.md) |
| MLflow, Unity Catalog models gated by the acceptance test, LLM judge; deploying to **dev, UAT, prod** | [mlops.md](docs/mlops.md), [deployment.md](docs/deployment.md) |
| Results storage and Lakebase; retrieval with OMOP synonyms and ancestors | [results_storage.md](docs/results_storage.md), [rag_and_vocabulary.md](docs/rag_and_vocabulary.md) |
| De-identification methods and cost; financial trade-offs; radiographs; MedGemma | [deidentification.md](docs/deidentification.md), [financial_tradeoffs.md](docs/financial_tradeoffs.md), [radiograph.md](docs/radiograph.md), [medgemma.md](docs/medgemma.md) |
