-- Design A: post-coordinated (OHDSI Dentistry Workgroup SITE / SITE_EVENT).
-- One MEASUREMENT row per site and measure; the row is tied to a tooth-site SITE
-- through SITE_EVENT, and the tooth-site's parent SITE is the tooth.
site_rows AS (
  SELECT m.visit_occurrence_id AS visit_id,
         CAST(tooth.site_source_value AS INT) AS tooth,
         split_part(ts.site_source_value, '-', 2) AS site,
         MAX(CASE WHEN m.measurement_concept_id = 2000000020 THEN m.value_as_number END) AS pd_mm,
         MAX(CASE WHEN m.measurement_concept_id = 2000000021 THEN m.value_as_number END) AS cal_mm,
         MAX(CASE WHEN m.measurement_concept_id = 2000000022 THEN m.value_as_number END) AS bop
  FROM {schema}.measurement m
  JOIN {schema}.site_event se ON se.event_id = m.measurement_id AND se.event_field_concept_id = 1147138
  JOIN {schema}.site ts ON ts.site_id = se.site_id
  JOIN {schema}.site tooth ON tooth.site_id = ts.parent_site_id
  WHERE m.measurement_concept_id IN (2000000020, 2000000021, 2000000022)
  GROUP BY 1, 2, 3
),
tooth_rows AS (
  SELECT m.visit_occurrence_id AS visit_id,
         CAST(tooth.site_source_value AS INT) AS tooth,
         MAX(CASE WHEN m.measurement_concept_id = 2000000023 THEN m.value_as_number END) AS status,
         MAX(CASE WHEN m.measurement_concept_id = 2000000024 THEN m.value_as_number END) AS furcation,
         MAX(CASE WHEN m.measurement_concept_id = 2000000025 THEN m.value_as_number END) AS mobility
  FROM {schema}.measurement m
  JOIN {schema}.site_event se ON se.event_id = m.measurement_id AND se.event_field_concept_id = 1147138
  JOIN {schema}.site tooth ON tooth.site_id = se.site_id
  WHERE m.measurement_concept_id IN (2000000023, 2000000024, 2000000025)
  GROUP BY 1, 2
),
