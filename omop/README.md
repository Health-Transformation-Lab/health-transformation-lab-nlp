# OMOP layer

Base model: OMOP CDM **v5.4**. We do not vendor the full DDL; both pipelines
load it from the OHDSI package of their language:

- Python: `omop/ddl/postgresql/` holds the OHDSI CommonDataModel **v5.4.2 Postgres DDL**
  (https://github.com/OHDSI/CommonDataModel, Apache-2.0), used by
  `dental_omop_nlp/db.py` to create the CDM in Postgres / **Lakebase**
  (`scripts/05_load_omop_db.py`). Primary keys and indices are applied;
  foreign keys need the Athena vocabulary first.
- R: `r/R/01_etl_synthea.R` loads the full CDM with ETL-Synthea into Postgres /
  Lakebase (default) or Databricks SQL (`DENTAL_DBMS`).

**Which database:** Lakebase (Postgres) for dev/test CDMs and operational
tables; Delta tables via Databricks SQL for the large analytical CDM. The dental
DDL and the `perio_chart` view are tested on Postgres 16 in CI
(`python/tests/test_db_postgres.py`).

What this folder owns:

| File | Purpose |
|------|---------|
| `ddl/dental_extension.sql` | `SITE`, `SITE_EVENT` tables and the `perio_chart` view. Tooth-level modeling per the OHDSI Dentistry Workgroup proposal. |
| `vocab/local_concepts.csv` | Local (2-billion-range) concepts for perio chart measurements and the status labels, vocabulary `DENTAL_LOCAL`. Loaded into `CONCEPT` alongside the Athena vocabularies. |

## Tables the benchmark touches

| Table | Written by | Read by |
|-------|-----------|---------|
| `person`, `visit_occurrence`, `condition_occurrence`, `procedure_occurrence` | Synthea ETL | labels, notes, structured baseline |
| `measurement` (perio chart numerics) | Synthea ETL from the custom perio module | `perio_chart` view → labels |
| `site`, `site_event` | Synthea ETL (tooth-numbered events) | note generator (tooth-level detail in the Objective line) |
| `note` | note generator | every model rung |
| `note_nlp` | scorer / inference | downstream review; **never** `condition_occurrence` |

The model's output lands in `NOTE_NLP` as a term with a probability and a
`note_nlp_source_concept_id` pointing at the model + version. It is a flag
for review. Promoting it to a `CONDITION_OCCURRENCE` is a clinical decision
that this repo does not make.

## Vocabularies

Standard vocabularies (SNOMED, LOINC, CDT) come from Athena
(https://athena.ohdsi.org) and are not checked in; see each pipeline's
README for where to drop the download. `DENTAL_LOCAL` concepts live here
and are loaded after Athena.

How dental data differs from medical data in OMOP: [../docs/omop_dental_vs_medical.md](../docs/omop_dental_vs_medical.md).
