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
algorithm and the AI model. Structured radiograph AI output is an exploratory
eighth source ([docs/radiograph.md](docs/radiograph.md)). Details:
[docs/process.md](docs/process.md).

**Ground rules**

- **Synthetic data only.** Every patient, note and code here is generated. No PHI,
  no real records, no employer or partner data, ever. Pull requests that add
  real data are closed on sight.
- **Nothing identifiable reaches Label Studio or a model.** Synthetic notes carry
  fake PHI on purpose; the de-identification step must remove all of it, and a
  leak gate blocks any note where it didn't.
- **Public until approved for internal use.** Then the code moves to the internal
  workspace and this repo stays the public reference.
- **Two languages, one contract.** Data engineering works in Python, data
  science in R. Both read the same files and produce the same numbers
  (parity-tested to 1e-16).

## OMOP in dental vs medical data

OMOP was built around medical claims and EHRs. Dental data tracks different
things and puts the facts that matter most for periodontal research where core
OMOP has no native place for them.

**What's usually tracked** (varies by payer, state and system):

- **Medical claims:** ICD-10-CM diagnoses (required), CPT/HCPCS procedures,
  pharmacy claims (NDC). Little clinical detail.
- **Medical EHR:** problem list, labs (LOINC), vitals, medications (RxNorm),
  large volumes of clinical notes, radiology reports.
- **Dental claims:** CDT procedure codes with **tooth number, surface and
  quadrant**. Diagnosis code fields exist but are **often not required or
  filled**. No measurements.
- **Dental EHR:** CDT procedures **completed and planned** (treatment plan),
  **perio chart** (probing depth, CAL, recession, bleeding, mobility,
  furcation at 6 sites per tooth), radiograph images (rarely structured),
  templated notes, health history form. Diagnoses are often **missing, free
  text, or inconsistent with the charting**.

**What that means in OMOP:**

| | Medical | Dental |
|---|---|---|
| Diagnosis | `CONDITION_OCCURRENCE` from coded ICD-10 | Often has to be **inferred** from charting and notes (this project) |
| Procedure | CPT/HCPCS, standard concepts | CDT/HCPCS D-codes can be non-standard in Athena; kept in source fields |
| Tooth / surface / site | Not needed | No native table; `SITE` / `SITE_EVENT` extension proposed by the OHDSI Dentistry Workgroup |
| Clinical measurements | `MEASUREMENT` with LOINC | Few standard concepts for per-site perio values; local concepts here |
| Linkage | Within payer or health system | Dental and medical records (diabetes, smoking: inputs to **grade**) often live apart |

Full comparison, how this repo maps each one, and sources:
[docs/omop_dental_vs_medical.md](docs/omop_dental_vs_medical.md).

## Datasets (in `data/datasets/`, regenerate with `scripts/10_build_study.py`)

| File | What it is |
|------|------------|
| `train.csv` | ~2,400 de-identified notes from ~970 people (63% written in the published real-note style; [how](docs/note_realism.md)), labeled by the generator (chart truth and the clinician's written dx). For training the AI model. |
| `review_tasks.json` | ~240 charts (one visit per person, rare statuses oversampled), every source, de-identified. **Import into Label Studio.** |
| `answer_key/review_key.csv` | Generator truth and each method's reading for the review charts. **Reviewers must not see this.** |
| `method_agreement.csv`, `method_coverage.csv` | Pairwise agreement and kappa between the seven sources. Input to the qualitative review. |
| `deid_report.csv` | Per-note de-identification recall and over-redaction against the injected fake PHI. |

## How we work: Spec Kit + Superpowers

Changes start as a spec and are built test-first.

- **Spec Kit** (spec-driven development): `/speckit-specify` → `/speckit-plan` →
  `/speckit-tasks` → `/speckit-implement`. Specs live in `specs/NNN-feature/`;
  project principles in [`.specify/memory/constitution.md`](.specify/memory/constitution.md).
  First spec: [001 realistic dental notes](specs/001-realistic-dental-notes/spec.md).
- **Superpowers** (Claude Code skills): brainstorming, writing and executing
  plans, test-driven development, systematic debugging, verification before
  completion, code review. Enabled for this repo in `.claude/settings.json`;
  session plans go in `docs/superpowers/`.

Agent instructions and setup: [CLAUDE.md](CLAUDE.md).

## Evaluation methods borrowed from GlobalDentBench

From the GlobalDentBench dental LLM benchmark ([arXiv 2605.24636](https://arxiv.org/abs/2605.24636)):
errors graded by clinical severity (S0/S1/S2, reported as unsafe rate), results
broken down by difficulty level (L1 stated / L2 translate / L3 infer), and the LLM
judge chosen by a bake-off against human reviewers. We report kappa and
confidence intervals where they reported percent agreement, and bar a judge from
grading its own model family. [docs/dentbench_methods.md](docs/dentbench_methods.md)

## Exploratory: structured radiograph findings

A personal exploration, for learning and training, of how structured radiograph
AI output (bone level per tooth) could be added as an eighth source and as model
input. Simulated data and public information only; not affiliated with any vendor.
[docs/radiograph.md](docs/radiograph.md)

## Exploratory: MedGemma

Notes on how Google's open MedGemma models could be tried here: as a zero-shot
note reader, a fine-tuned reader, a judge candidate, a paraphraser for more
varied synthetic notes, and (much later) for dental radiographs, which it wasn't
trained on. [docs/medgemma.md](docs/medgemma.md)

## Data sources

All notes here are synthetic and generated by this repo. Public synthetic dental
notes do exist; the closest is a 20,000-note IEEE DataPort set with periodontal
and tooth-level labels (subscription, license unlisted), a good candidate for an
independent test set. Details, limitations and other sources:
[docs/data_sources.md](docs/data_sources.md)

## Cost-effectiveness at 1M+ notes

Reviewers can stage hundreds of charts, not a million. An LLM judge, calibrated
against the reviewers, estimates each method's accuracy on a sample of the full
corpus; a cost model prices running each method over every note. Result: a
frontier of accuracy vs cost with incremental cost per extra correct note.
[docs/cost_effectiveness.md](docs/cost_effectiveness.md)

```bash
python scripts/14_benchmark_cost.py && python scripts/15_judge.py --backend openai && python scripts/16_cost_effectiveness.py
```

## What's in here

| Path | What it is |
|------|------------|
| `python/dental_omop_nlp/` | `study.py` builds everything; `clinical_notes.py`, `sources.py`, `phi.py` generate; `deid.py` de-identifies; `note_reader.py` + `sources.READERS` read each source; `phenotype.py` compares methods and holds the rule-based algorithm; `rungs.py` the AI models; `labelstudio.py`, `reliability.py` the validation; `judge.py`, `cost_effectiveness.py` the LLM judge and cost analysis |
| `labelstudio/` | Labeling config and setup steps |
| `r/` | R twin: labels, scorer, reliability (`04_reliability.R`), tidymodels/`text` models, OHDSI ETL-Synthea. Local run and GPU guidance in `r/README.md` |
| `models.yaml` | 12 candidate encoders from the evaluation sheet, with roles and ladders |
| `costs.yaml` | Prices and throughput for costing each method over the full corpus (**illustrative until replaced**) |
| `omop/` | OMOP CDM 5.4 dental extension (`SITE`, `SITE_EVENT`) from the OHDSI Dentistry Workgroup |
| `databricks/` | Free Edition notebook; `02_llm_judge.sql` runs the judge with `ai_query` at scale |
| `docs/` | [process](docs/process.md), [data sources](docs/data_sources.md), [note realism](docs/note_realism.md), [MedGemma ideas](docs/medgemma.md), [GlobalDentBench methods](docs/dentbench_methods.md), [references](docs/references.md), [labeling protocol](docs/labeling_protocol.md), [learning plan](docs/plan.md), [cost-effectiveness](docs/cost_effectiveness.md), [architecture review questions](docs/design_review_rsa.md), [ADRs](docs/adr/) |

## Quick start

```bash
cd python && pip install -e .

python scripts/10_build_study.py                 # datasets above
python scripts/11_ai_predict.py --rung note_rules
python scripts/11_ai_predict.py --rung tfidf_logreg
# python scripts/11_ai_predict.py --rung distilbert-base --epochs 2   # pip install -e ".[models]"

# Reviewers stage review_tasks.json in Label Studio (labelstudio/README.md), then:
python scripts/12_import_review.py reviewer1.json reviewer2.json reviewer3.json
python scripts/13_reliability.py                 # or: Rscript r/R/04_reliability.R

# Dry run with simulated reviewers (files and output marked SIMULATED):
python scripts/12_import_review.py --simulate 4 && python scripts/13_reliability.py --simulated

pytest -q tests && cd .. && Rscript r/tests/test_parity.R
```

The earlier short-note benchmark (`scripts/01`–`03`) is still here for quick
model comparisons; see `python/README.md`.

## Background

- Chuang, Lee, Tokede, Lin, Brandon, Tran, Jiang, Walji. *Artificial Intelligence
  in Extracting Diagnostic Data from Dental Records* (UTHealth + UCSF):
  RoBERTa trained on GPT-4 synthetic notes, tested on 240 dentist-labeled notes
  per site; status, stage, grade, extent. [arXiv 2407.21050](https://arxiv.org/abs/2407.21050)
- Patel J.S. *Utilizing Electronic Dental Record Data to Track Periodontal
  Disease Change*, PhD dissertation, IUPUI 2020: charting-derived and
  clinician-recorded diagnoses agreed 47% of the time; charting present for
  ~80% of patients. [IU ScholarWorks](https://scholarworks.indianapolis.iu.edu/items/0768bd4f-e24a-465a-95fe-b8cabca06c68/full)
- Patel J.S. et al. *Developing Automated Computer Algorithms to Phenotype
  Periodontal Disease Diagnoses in Electronic Dental Records*, Methods of
  Information in Medicine 2022.
- OHDSI Dentistry Workgroup, *Mapping Dental Use Cases to the OMOP-CDM*
  (SITE / SITE_EVENT proposal). [OHDSI 2023](https://ohdsi.org/wp-content/uploads/2023/10/39-Koski-OHDSIreport-Robert-Koski.pdf)

## Owners

- Python / data engineering / OMOP: John Bowyer
- R / data science: _TBD_

## License

MIT. OMOP CDM and the OHDSI tools are Apache-2.0. Model licenses are listed per
model in `models.yaml`; check them before redistributing fine-tuned weights.
