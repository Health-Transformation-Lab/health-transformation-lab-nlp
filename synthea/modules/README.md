# Custom Synthea modules

Synthea ships a `Dental and Oral Examination` module (dental category) that
produces recall exams and cleanings. It does **not** produce a periodontal
chart or free-text notes, so this folder adds what the benchmark needs.

Planned modules (Synthea Generic Module Framework, JSON):

| Module | Emits | Status |
|--------|-------|--------|
| `dental_periodontal_exam.json` | Per recall visit: max probing depth (mm), % sites bleeding on probing, clinical attachment loss (mm), radiographic bone loss (%), teeth lost to perio. Progression driven by age, smoking and diabetes states from the core modules. | TODO |
| `dental_caries.json` | Caries incidence and restorations, tooth-numbered. | TODO |
| `dental_periodontal_treatment.json` | Prophylaxis vs scaling and root planing vs referral, conditional on the chart. | TODO |

Coding: conditions and procedures use SNOMED CT (Synthea's native vocab);
CDT codes are attached as a second code where one exists so the OMOP ETL
can map to either. Observations use LOINC where a code exists and a local
code otherwise (listed in `../../omop/vocab/local_concepts.csv`).

The perio chart is the **ground truth** for the label and the note generator
downstream, so the numbers here must stay internally consistent (bone loss
should not exceed what the attachment loss implies, etc.). Keep the
distributions plausible but do not try to be epidemiologically exact; this is
a benchmark, not a prevalence study.

Module authoring reference: https://github.com/synthetichealth/synthea/wiki/Generic-Module-Framework
Module builder (visual): https://synthetichealth.github.io/module-builder/
