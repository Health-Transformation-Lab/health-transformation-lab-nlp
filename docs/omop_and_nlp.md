# What are OMOP and NLP?

> Plain-language background for this repo. Synthetic data only; see [DISCLAIMER](../DISCLAIMER.md).

The repo's name has both: **OMOP** is how the dental records are stored so they can be analyzed
the same way anywhere; **NLP** is how a computer reads the free-text chart notes.

## OMOP: one shape for health records

**In plain words:** every hospital and dental practice stores records differently: different
software, table layouts and code lists. OMOP is an agreed common shape for that data. Once each
site's records are converted into it, the same analysis code runs unchanged at every site, and
results can be compared or pooled without sharing the records themselves.

- **Name.** The OMOP Common Data Model (CDM), from the Observational Medical Outcomes Partnership;
  now maintained by **OHDSI** (Observational Health Data Sciences and Informatics, "Odyssey"), an open
  research community. This repo uses CDM version 5.4.
- **Two parts.**
  - *Standard tables:* one per kind of fact. `PERSON` (who), `VISIT_OCCURRENCE` (when they came
    in), `CONDITION_OCCURRENCE` (diagnoses), `PROCEDURE_OCCURRENCE` (what was done),
    `MEASUREMENT` (numbers such as probing depths), `NOTE` (free text), `NOTE_NLP` (facts a computer
    pulled out of the text).
  - *Standard vocabularies:* every code is mapped to one standard concept, so "periodontitis"
    means the same thing whether a site recorded it as an ICD-10-CM code (K05.3x), a SNOMED CT
    concept or a local term. Procedures use CDT codes (e.g. D4341, scaling and root planing).
- **Why it matters here.** A periodontal phenotype written once against OMOP could run at any
  dental site that converts its data, which is the point of multi-site studies.
- **The dental gap.** OMOP grew up around medical claims and EHRs. Dental charts put key facts
  (tooth number, surface, six probing sites per tooth) where OMOP has no native place, and few dental
  datasets have been converted. This repo adds a small dental extension and compares three ways
  to store tooth-level data: [site_level_omop.md](site_level_omop.md),
  [omop_dental_vs_medical.md](omop_dental_vs_medical.md).

**In this repo:** the synthetic patients are loaded into OMOP CDM 5.4 plus the dental extension
(Postgres or Databricks Lakebase), and the phenotype reads from there.
Code: [`code_walkthrough.md` step 1](code_walkthrough.md#1-generate-the-synthetic-study) and the
Postgres loader in `python/health_transformation_lab_nlp/db.py`.

## NLP: getting facts out of free text

**In plain words:** natural language processing (NLP) is software that reads ordinary written
text. A dentist's note such as *"Gen mod perio, 5-6 mm pockets UR/LR, BOP+, stage III grade B"*
holds the diagnosis, but in shorthand, abbreviations and sentences a database can't query. NLP
turns it into a structured answer (here: periodontal status, stage, grade, extent) that can sit
in OMOP's `NOTE_NLP` table next to the coded data.

Three generations of NLP are compared in this repo, from simplest to most capable:

| Approach | How it reads a note | In this repo |
|---|---|---|
| **Rules** | Hand-written patterns: "stage III" → stage III; "BOP+" → bleeding | `note_rules`; also the de-identification regex |
| **Statistical** | Counts which words appear and learns weights from labeled notes (TF-IDF + logistic regression) | `tfidf_logreg`, `fusion_tfidf_rad` |
| **Transformer models** | Read every word in context. **Encoders** such as BERT pick a label ([what is BERT?](bert.md)); **LLMs** such as MedGemma write an answer and can quote the evidence ([medgemma.md](medgemma.md)) | the BERT ladder; MedGemma reader |

**NLP also protects privacy.** Before any model or reviewer sees a note, NLP finds and removes
names, dates and other identifiers (de-identification): [deidentification.md](deidentification.md).

**How well it works is checked, not assumed.** Every method is scored against the known synthetic
truth and against reviewers who read the same charts: [code_walkthrough.md steps 6–7](code_walkthrough.md#6-ai-models-read-the-notes).

## Where to go next

- The study end to end: [README](../README.md#what-it-does-step-by-step)
- OMOP for dental data: [omop_dental_vs_medical.md](omop_dental_vs_medical.md),
  [site_level_omop.md](site_level_omop.md)
- NLP models: [bert.md](bert.md), [medgemma.md](medgemma.md), [deidentification.md](deidentification.md)
- OHDSI's own introduction: [The Book of OHDSI](https://ohdsi.github.io/TheBookOfOhdsi/)
