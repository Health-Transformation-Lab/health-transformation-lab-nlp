# dental-omop-nlp

> **Personal learning project.** Built on my own time while waiting for internal
> approvals. Not affiliated with or endorsed by any employer, institution or
> vendor, and nothing here reflects official business or research of any
> organization, including CareQuest. Synthetic data only. See [DISCLAIMER.md](DISCLAIMER.md).

Can periodontal status be phenotyped from a dental EHR, and can AI reading the
chart notes match clinicians? This repo runs that study end to end on **synthetic**
data, to learn the pipeline, the reviewer workflow and the analysis.

![Study process](docs/img/process.png)

**Seven sources per visit:**

- Chart notes · Exam forms
- Procedure codes, completed · planned
- Procedure diagnoses, completed · planned
- Probing chart (CAL, radiographic bone loss, tooth loss from perio)

Details: [docs/process.md](docs/process.md).

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
| 1 | Generate synthetic patients over time (8 clinics), all seven sources, notes with fake PHI | [1](docs/code_walkthrough.md#1-generate-the-synthetic-study) |
| 2 | De-identify; a leak gate blocks any note with PHI left | [2](docs/code_walkthrough.md#2-de-identify-and-gate) |
| 3 | Read each source; compare them; build the rule-based phenotype (study-design order) | [3–5](docs/code_walkthrough.md#3-read-each-source) |
| 4 | AI models read the notes only: baselines, 12 BERT models, MedGemma | [6](docs/code_walkthrough.md#6-ai-models-read-the-notes) |
| 5 | Reviewers stage the same charts in Label Studio | [7](docs/code_walkthrough.md#7-reviewers-stage-charts) |
| 6 | Reliability and the acceptance test, on six and five categories; every source order scored | [8–9](docs/code_walkthrough.md#8-reliability-and-the-acceptance-test) |
| 7 | Over time and at scale: plausibility, data quality, clinic prevalence, progression | [10–12](docs/code_walkthrough.md#10-over-time-plausibility-and-data-quality) |
| 8 | Site-level charts, both classifications, three OMOP storage designs, Lakebase | [13–15](docs/code_walkthrough.md#13-site-level-charts-both-classifications) |
| 9 | 1M+ notes: LLM judge and cost; deploy to dev, UAT, prod | [16–18](docs/code_walkthrough.md#16-llm-judge-and-cost-at-1m-notes) |

Run every step (seeded, simulated reviewers): `cd python && pip install -e ".[dev]" && cd .. && python/scripts/make_parity_inputs.sh`; tests: `pytest -q python/tests`, `Rscript r/tests/test_parity.R`.

## Ground rules

- **Synthetic data only.** No PHI, real records, or employer or partner data, ever.
  A de-identification leak gate guards Label Studio and every model.
- **Python and R, one contract:** same files, same numbers (parity-tested to 1e-9).

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

| Model | Paper | Domain | Role |
|---|---|---|---|
| [BERT base](https://huggingface.co/google-bert/bert-base-uncased) | [arXiv 1810.04805](https://arxiv.org/abs/1810.04805) | general | classifier |
| [DistilBERT](https://huggingface.co/distilbert/distilbert-base-uncased) | [arXiv 1910.01108](https://arxiv.org/abs/1910.01108) | general | classifier |
| [ModernBERT base](https://huggingface.co/answerdotai/ModernBERT-base) | [arXiv 2412.13663](https://arxiv.org/abs/2412.13663) | general | classifier, long context |
| [ModernBERT large](https://huggingface.co/answerdotai/ModernBERT-large) | [arXiv 2412.13663](https://arxiv.org/abs/2412.13663) | general | classifier, long context |
| [Longformer](https://huggingface.co/allenai/longformer-base-4096) | [arXiv 2004.05150](https://arxiv.org/abs/2004.05150) | general | long context |
| [SciBERT](https://huggingface.co/allenai/scibert_scivocab_uncased) | [arXiv 1903.10676](https://arxiv.org/abs/1903.10676) | scientific | classifier |
| [BiomedBERT](https://huggingface.co/microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext) | [arXiv 2007.15779](https://arxiv.org/abs/2007.15779) | biomedical | classifier |
| [BioClinical ModernBERT base](https://huggingface.co/thomas-sounack/BioClinical-ModernBERT-base) | [arXiv 2506.10896](https://arxiv.org/abs/2506.10896) | clinical | classifier, long context |
| [BioClinical ModernBERT large](https://huggingface.co/thomas-sounack/BioClinical-ModernBERT-large) | [arXiv 2506.10896](https://arxiv.org/abs/2506.10896) | clinical | classifier, long context |
| [Clinical-Longformer](https://huggingface.co/yikuan8/Clinical-Longformer) | [arXiv 2201.11838](https://arxiv.org/abs/2201.11838) | clinical | long context |
| [SapBERT](https://huggingface.co/cambridgeltl/SapBERT-from-PubMedBERT-fulltext) | [arXiv 2010.11784](https://arxiv.org/abs/2010.11784) | biomedical | concept mapping |
| [GTE-ModernColBERT](https://huggingface.co/lightonai/GTE-ModernColBERT-v1) | model card | general | retrieval |

Plus baselines and MedGemma ([1.5 4B](https://huggingface.co/google/medgemma-1.5-4b-it),
[27B text](https://huggingface.co/google/medgemma-27b-text-it); [arXiv 2507.05201](https://arxiv.org/abs/2507.05201)).
**Status:** all train and predict, but none has been run yet (needs the Hugging Face downloads).

## Action items

Differences from the study design and open decisions: **[docs/action_items.md](docs/action_items.md)**
(source order and five categories, plausibility tolerances, clinic definition, published
comparisons, prediction outcome, OMOP storage design).

## Drill-downs

| Topic | |
|---|---|
| Site-level data in OMOP: 32 teeth × 6 sites, derived measures, 2017 AAP/EFP **and 2012 CDC/AAP**, three storage designs on Postgres/Lakebase, concept mapping, Atlas feasibility | [site_level_omop.md](docs/site_level_omop.md) |
| Integrated phenotype (five categories, source order), patients over time, clinic prevalence, data quality, prediction | [process.md](docs/process.md#integrated-phenotype-and-validation-spec-005), [action_items.md](docs/action_items.md) |
| Dental vs medical data in OMOP: what claims and EHRs track, tooth/site gaps | [omop_dental_vs_medical.md](docs/omop_dental_vs_medical.md) |
| Data: synthetic notes, review set, public datasets | [note_realism.md](docs/note_realism.md), [data_sources.md](docs/data_sources.md) |
| Deploying: Asset Bundle with **dev, UAT, prod** targets and variables; CI | [deployment.md](docs/deployment.md) |
| Results storage; Lakebase for review queue, live labels, run ledger | [results_storage.md](docs/results_storage.md) |
| Retrieval, OMOP synonyms/ancestors/relationships, graphs: 8 test cases | [rag_and_vocabulary.md](docs/rag_and_vocabulary.md) |
| Financial trade-offs: inference vs review hours vs accuracy | [financial_tradeoffs.md](docs/financial_tradeoffs.md), [cost_effectiveness.md](docs/cost_effectiveness.md) |
| Exploratory: radiograph findings; MedGemma | [radiograph.md](docs/radiograph.md), [medgemma.md](docs/medgemma.md) |

## More

[How we work](CLAUDE.md) (Spec Kit specs, Superpowers, test-first) · [references](docs/references.md) ·
[labeling protocol](docs/labeling_protocol.md) · [learning plan](docs/plan.md) ·
[architecture review questions](docs/design_review_rsa.md) · Owners: Python / data engineering / OMOP:
John Bowyer; R / data science: _TBD_ · MIT license (OMOP CDM and OHDSI tools Apache-2.0; model licenses in `models.yaml`)
