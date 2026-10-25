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

- **Synthetic data only.** No PHI, no real records, no employer or partner data, ever.
- **Nothing identifiable reaches Label Studio or a model.** Synthetic notes carry
  fake PHI on purpose; de-identification must remove it and a leak gate blocks
  any note where it didn't.
- **Two languages, one contract.** Python (data engineering) and R (data
  science) read the same files and produce the same numbers (parity-tested to 1e-9).
- **Public until approved for internal use.**

## Dental vs medical data in OMOP

OMOP was built around medical claims and EHRs. Medical claims carry required
ICD-10 diagnoses; dental claims carry CDT procedures by **tooth and surface**
and often no diagnosis. Dental EHRs hold the **perio chart** (per-site numbers)
and **treatment plans**, but diagnoses are often missing or don't match the
charting, so they have to be inferred. Core OMOP has no tooth/site table
(the OHDSI Dentistry Workgroup proposes `SITE` / `SITE_EVENT`), and the medical
risk factors that set the grade (diabetes, smoking) often live in a separate
record. [docs/omop_dental_vs_medical.md](docs/omop_dental_vs_medical.md)

## How results are measured

- **Acceptance test:** does the AI agree with the reviewers at least as much as
  they agree with each other? Each method's mean kappa vs each reviewer, compared
  with the mean reviewer-pair kappa, with a bootstrap CI and a margin fixed in
  advance. Replicates OHDSI's case-validation approach
  ([video](https://www.youtube.com/watch?v=scUssf863TI) from ~49 min;
  [paper](https://doi.org/10.1038/s41746-025-01433-4)). [docs/process.md](docs/process.md#validation-criterion-as-reliable-as-a-human-reviewer)
- **Kappa:** agreement beyond chance (Cohen's for two raters, Fleiss' for many
  reviewers, weighted for ordered stages).
- **95% confidence intervals:** the range the true value plausibly falls in,
  given that ~240 reviewed charts are a sample, not every chart. Overlapping
  intervals mean two methods can't be called different. Computed by bootstrap
  (resample the charts 1,000 times, recompute, keep the middle 95%), because
  kappa has no simple formula.
- **Unsafe rate:** errors graded by clinical severity, and results by difficulty
  level, after GlobalDentBench ([docs/dentbench_methods.md](docs/dentbench_methods.md)).

Plain-language explanation: [docs/statistics.md](docs/statistics.md)

## Models evaluated

The 12 models from the evaluation sheet are registered in `models.yaml` and
scored with the same split, reviewers and acceptance test as the baselines.

| Model | Hugging Face id | Domain | Role |
|---|---|---|---|
| BERT base | `google-bert/bert-base-uncased` | general | classifier |
| DistilBERT | `distilbert/distilbert-base-uncased` | general | classifier |
| ModernBERT base | `answerdotai/ModernBERT-base` | general | classifier, long context |
| ModernBERT large | `answerdotai/ModernBERT-large` | general | classifier, long context |
| Longformer | `allenai/longformer-base-4096` | general | long context |
| SciBERT | `allenai/scibert_scivocab_uncased` | scientific | classifier |
| BiomedBERT | `microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext` | biomedical | classifier |
| SapBERT | `cambridgeltl/SapBERT-from-PubMedBERT-fulltext` | biomedical | concept mapping (not a classifier) |
| BioClinical ModernBERT base | `thomas-sounack/BioClinical-ModernBERT-base` | clinical | classifier, long context |
| BioClinical ModernBERT large | `thomas-sounack/BioClinical-ModernBERT-large` | clinical | classifier, long context |
| Clinical-Longformer | `yikuan8/Clinical-Longformer` | clinical | long context |
| GTE-ModernColBERT | `lightonai/GTE-ModernColBERT-v1` | general | retrieval (not a classifier) |

Also on the ladder: baselines (`note_rules`, `rules_baseline`,
`structured_baseline`, `tfidf_logreg`, `fusion_tfidf_rad`) and exploratory
MedGemma readers ([docs/medgemma.md](docs/medgemma.md)).

**Status:** the 10 classifier and long-context models fine-tune and predict with
`scripts/11_ai_predict.py --rung <id>`, but none has been run yet. That needs
the Hugging Face downloads (laptop, Databricks, or Free Edition serverless GPU
for the large ones). Results so far are the baselines on simulated reviewers.

## Datasets (`data/datasets/`, rebuilt by `scripts/10_build_study.py`)

| File | What it is |
|------|------------|
| `train.csv` | ~2,400 de-identified synthetic notes, labeled by the generator. Model training. |
| `review_tasks.json` | ~240 charts with every source. **Import into Label Studio.** |
| `answer_key/review_key.csv` | Generator truth and each method's reading. **Reviewers must not see this.** |
| `method_agreement.csv` | Agreement and kappa between the seven sources. |
| `deid_report.csv` | De-identification recall and over-redaction. |

How the notes were made realistic: [docs/note_realism.md](docs/note_realism.md).
Public synthetic dental datasets: [docs/data_sources.md](docs/data_sources.md).

## Scaling to 1M+ notes

Reviewers can stage hundreds of charts, not a million. An LLM judge, calibrated
against them, estimates each method's accuracy on a corpus sample; a cost model
prices each method over every note, giving an accuracy-vs-cost frontier.
[docs/cost_effectiveness.md](docs/cost_effectiveness.md)

## Exploratory

- **Structured radiograph findings** as an eighth source and model input
  (simulated data, public information only). [docs/radiograph.md](docs/radiograph.md)
- **MedGemma** as a note reader, fine-tuned reader, judge candidate or
  paraphraser. [docs/medgemma.md](docs/medgemma.md)

## Quick start

```bash
cd python && pip install -e .
python scripts/10_build_study.py                  # datasets
python scripts/11_ai_predict.py --rung tfidf_logreg
# Dry run with simulated reviewers (marked SIMULATED):
python scripts/12_import_review.py --simulate 4 && python scripts/13_reliability.py --simulated
pytest -q tests && cd .. && Rscript r/tests/test_parity.R
```

Real reviewer exports, encoder models, Databricks and the R pipeline:
[python/README.md](python/README.md), [r/README.md](r/README.md),
[labelstudio/README.md](labelstudio/README.md), [databricks/](databricks/).

## More

| | |
|---|---|
| How we work | Spec Kit specs in `specs/`, Superpowers skills, test-first. [CLAUDE.md](CLAUDE.md), [constitution](.specify/memory/constitution.md) |
| Code | `python/dental_omop_nlp/`, `r/`, `models.yaml` (12 encoders), `costs.yaml` (illustrative prices), `omop/` (dental extension) |
| Docs | [labeling protocol](docs/labeling_protocol.md), [learning plan](docs/plan.md), [architecture review questions](docs/design_review_rsa.md), [ADRs](docs/adr/), [statistics](docs/statistics.md), [dental vs medical OMOP](docs/omop_dental_vs_medical.md) |
| Background | Key papers (UTHealth/UCSF NLP, IUPUI phenotyping, OHDSI dental): [docs/references.md](docs/references.md) |
| Owners | Python / data engineering / OMOP: John Bowyer. R / data science: _TBD_ |
| License | MIT. OMOP CDM and OHDSI tools Apache-2.0; model licenses per model in `models.yaml` |
