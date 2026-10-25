-- Design C: site columns. MEASUREMENT carries tooth_number and tooth_site
-- directly (a site-aware data table), so no extra joins or decoding.
site_rows AS (
  SELECT m.visit_occurrence_id AS visit_id, m.tooth_number AS tooth, m.tooth_site AS site,
         MAX(CASE WHEN m.measurement_concept_id = 2000000020 THEN m.value_as_number END) AS pd_mm,
         MAX(CASE WHEN m.measurement_concept_id = 2000000021 THEN m.value_as_number END) AS cal_mm,
         MAX(CASE WHEN m.measurement_concept_id = 2000000022 THEN m.value_as_number END) AS bop
  FROM {schema}.measurement m
  WHERE m.measurement_concept_id IN (2000000020, 2000000021, 2000000022)
  GROUP BY 1, 2, 3
),
tooth_rows AS (
  SELECT m.visit_occurrence_id AS visit_id, m.tooth_number AS tooth,
         MAX(CASE WHEN m.measurement_concept_id = 2000000023 THEN m.value_as_number END) AS status,
         MAX(CASE WHEN m.measurement_concept_id = 2000000024 THEN m.value_as_number END) AS furcation,
         MAX(CASE WHEN m.measurement_concept_id = 2000000025 THEN m.value_as_number END) AS mobility
  FROM {schema}.measurement m
  WHERE m.measurement_concept_id IN (2000000023, 2000000024, 2000000025)
  GROUP BY 1, 2
),
