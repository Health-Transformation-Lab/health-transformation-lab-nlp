# dental-omop-nlp

> **Personal learning project.** Built on my own time while waiting for internal
> approvals. Not affiliated with or endorsed by any employer, institution or
> vendor, and nothing here reflects official business or research of any
> organization, including CareQuest. Synthetic data only. See [DISCLAIMER.md](DISCLAIMER.md).

How well can periodontal status be phenotyped from a dental EHR, and can a
BERT-family model reading the chart notes match clinicians? This repo runs that
kind of study end to end on **synthetic** data, as a way to learn the pipeline,
the reviewer workflow and the analysis.

![Study process](docs/img/process.png)

**Seven sources per visit:**

- Chart notes
- Exam forms
- Procedure codes, completed
- Procedure codes, planned
- Procedure diagnoses, completed
- Procedure diagnoses, planned
- Probing chart (CAL, radiographic bone loss, tooth loss from perio)

Compare methods → qualitative review → rule-based phenotyping algorithm →
several reviewers stage the same charts in Label Studio, compared against the
algorithm and the AI model. [docs/process.md](docs/process.md)

**Staging and grading** follow the AAP worksheet
([PDF](https://www.perio.org/wp-content/uploads/2019/08/Staging-and-Grading-Periodontitis.pdf)):
stage from interdental CAL (RBL only if CAL is missing), raised by tooth loss
and complexity; grade starts at B. Same rules for the synthetic truth,
reviewers and LLMs. [docs/staging_grading.md](docs/staging_grading.md)

## Ground rules

- **Synthetic data only.** No PHI, real records, or employer or partner data, ever.
  A de-identification leak gate guards Label Studio and every model.
- **Python and R, one contract:** same files, same numbers (parity-tested to 1e-9).

## How results are measured

- **Acceptance test:** an AI passes if it agrees with the reviewers at least as
  much as they agree with each other: mean kappa vs each reviewer against the
  mean reviewer-pair kappa, with a bootstrap CI and a margin fixed in advance.
  After OHDSI's case-validation work ([video](https://www.youtube.com/watch?v=scUssf863TI),
  from ~49 min; [paper](https://doi.org/10.1038/s41746-025-01433-4)).
- **Kappa** is agreement beyond chance. **95% confidence intervals** give the
  range the true value plausibly falls in, since ~240 charts are a sample;
  overlapping intervals mean two methods can't be called different. Computed by
  bootstrap (resample charts 1,000 times, keep the middle 95%).
- **Unsafe rate** (errors by clinical severity) and **results by difficulty**, after GlobalDentBench.

Details: [process](docs/process.md#validation-criterion-as-reliable-as-a-human-reviewer),
[statistics](docs/statistics.md), [GlobalDentBench methods](docs/dentbench_methods.md).

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

Plus baselines (`note_rules`, `tfidf_logreg`, `structured_baseline`,
`fusion_tfidf_rad`) and exploratory MedGemma readers
([1.5 4B](https://huggingface.co/google/medgemma-1.5-4b-it), [4B](https://huggingface.co/google/medgemma-4b-it),
[27B text](https://huggingface.co/google/medgemma-27b-text-it); [arXiv 2507.05201](https://arxiv.org/abs/2507.05201)).
**Status:** the 10 classifier and long-context models train and predict with
`scripts/11_ai_predict.py --rung <id>` but haven't been run yet (they need the
Hugging Face downloads). Results so far are baselines on simulated reviewers.

## Action items

Where the repo differs from the study design, and the decisions still open, are tracked in
**[docs/action_items.md](docs/action_items.md)**. The biggest open ones:
- confirm the source order and the five categories;
- tolerances for over-time plausibility;
- what "clinic" means in real data;
- comparable published studies;
- the outcome and horizon for the prediction model.

## Drill-downs

| Topic | |
|---|---|
| Integrated phenotype (five categories, source order), patients over time, clinic prevalence, data quality, prediction | [process.md](docs/process.md#integrated-phenotype-and-validation-spec-005), [action_items.md](docs/action_items.md) |
| Dental vs medical data in OMOP: what claims and EHRs track, tooth/site gaps | [omop_dental_vs_medical.md](docs/omop_dental_vs_medical.md) |
| Data: synthetic notes, review set, public datasets | [note_realism.md](docs/note_realism.md), [data_sources.md](docs/data_sources.md) |
| Deploying: Asset Bundle with **dev, UAT, prod** targets and variables; CI | [deployment.md](docs/deployment.md) |
| Results storage; Lakebase for review queue, live labels, run ledger | [results_storage.md](docs/results_storage.md) |
| Retrieval, OMOP synonyms/ancestors/relationships, graphs: 8 test cases | [rag_and_vocabulary.md](docs/rag_and_vocabulary.md) |
| Financial trade-offs: inference vs review hours vs accuracy | [financial_tradeoffs.md](docs/financial_tradeoffs.md), [cost_effectiveness.md](docs/cost_effectiveness.md) |
| Exploratory: radiograph findings; MedGemma | [radiograph.md](docs/radiograph.md), [medgemma.md](docs/medgemma.md) |

## Quick start

```bash
cd python && pip install -e .
python scripts/10_build_study.py && python scripts/11_ai_predict.py --rung tfidf_logreg
python scripts/12_import_review.py --simulate 4 && python scripts/13_reliability.py --simulated  # dry run
pytest -q tests && cd .. && Rscript r/tests/test_parity.R
```

## More

| | |
|---|---|
| How we work | Spec Kit specs in `specs/`, Superpowers skills, test-first. [CLAUDE.md](CLAUDE.md), [constitution](.specify/memory/constitution.md) |
| Code | `python/dental_omop_nlp/`, `r/`, `models.yaml` (12 encoders), `costs.yaml` (illustrative prices), `omop/` (dental extension) |
| Docs | [labeling protocol](docs/labeling_protocol.md), [learning plan](docs/plan.md), [architecture review questions](docs/design_review_rsa.md), [ADRs](docs/adr/), [statistics](docs/statistics.md), [dental vs medical OMOP](docs/omop_dental_vs_medical.md) |
| Background | Key papers (UTHealth/UCSF NLP, IUPUI phenotyping, OHDSI dental): [docs/references.md](docs/references.md) |
| Owners | Python / data engineering / OMOP: John Bowyer. R / data science: _TBD_ |
| License | MIT. OMOP CDM and OHDSI tools Apache-2.0; model licenses per model in `models.yaml` |
