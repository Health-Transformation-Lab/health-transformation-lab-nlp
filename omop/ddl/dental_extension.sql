-- Dental extension to OMOP CDM v5.4
--
-- The CDM records events against a PERSON. Dentists record events against a
-- TOOTH (and a surface of a tooth). The OHDSI Dentistry Workgroup's mapping
-- report (Koski, OHDSI 2023) proposed SITE and SITE_EVENT tables so an
-- observation can be tied to an anatomic site below the person level, the
-- same way EPISODE groups events above the visit level. This file adopts
-- that proposal. It is additive: no base CDM table changes.
--
-- Base CDM DDL: https://github.com/OHDSI/CommonDataModel (v5.4, Apache-2.0)
-- Dialect: ANSI-ish; works on Databricks SQL, DuckDB and Postgres with at most
-- the type names changing.

-- One row per anatomic site per person. For dentistry a site is a tooth
-- (universal numbering 1-32, primary A-T) or a tooth surface.
CREATE TABLE IF NOT EXISTS site (
  site_id                 BIGINT       NOT NULL,
  person_id               BIGINT       NOT NULL,
  site_concept_id         INT          NOT NULL,  -- SNOMED tooth / surface concept
  site_source_value       VARCHAR(50),            -- '3', '19', '19-MOD', 'A'
  parent_site_id          BIGINT,                 -- a surface points at its tooth
  site_start_date         DATE,                   -- eruption, or first seen
  site_end_date           DATE,                   -- extraction / exfoliation
  site_type_concept_id    INT          NOT NULL,  -- how we know (EHR, claim, synthetic)
  PRIMARY KEY (site_id)
);

-- Links a CDM event to a site. An event may touch several sites (a bridge
-- spans abutments); a site accumulates many events over time.
CREATE TABLE IF NOT EXISTS site_event (
  site_event_id           BIGINT       NOT NULL,
  site_id                 BIGINT       NOT NULL,
  event_id                BIGINT       NOT NULL,  -- *_occurrence_id / measurement_id
  event_field_concept_id  INT          NOT NULL,  -- which table: 1147127 condition_occurrence,
                                                  -- 1147082 procedure_occurrence, 1147138 measurement,
                                                  -- 1147165 observation
  site_event_type_concept_id INT       NOT NULL,
  PRIMARY KEY (site_event_id)
);

-- Convenience view: the periodontal chart as one row per person per exam.
-- This is what labels.py reads. Measurement concept ids are placeholders
-- resolved from omop/vocab/local_concepts.csv at ETL time.
CREATE OR REPLACE VIEW perio_chart AS
SELECT
  m.person_id,
  m.visit_occurrence_id,
  m.measurement_date                                        AS exam_date,
  MAX(CASE WHEN c.concept_code = 'PERIO_MAX_PD'  THEN m.value_as_number END) AS max_probing_depth_mm,
  MAX(CASE WHEN c.concept_code = 'PERIO_BOP_PCT' THEN m.value_as_number END) AS bop_pct,
  MAX(CASE WHEN c.concept_code = 'PERIO_MAX_CAL' THEN m.value_as_number END) AS max_cal_mm,
  MAX(CASE WHEN c.concept_code = 'PERIO_RBL_PCT' THEN m.value_as_number END) AS rbl_pct,
  MAX(CASE WHEN c.concept_code = 'PERIO_TEETH_LOST' THEN m.value_as_number END) AS teeth_lost_perio
FROM measurement m
JOIN concept c ON c.concept_id = m.measurement_concept_id
WHERE c.vocabulary_id = 'DENTAL_LOCAL'
GROUP BY m.person_id, m.visit_occurrence_id, m.measurement_date;
