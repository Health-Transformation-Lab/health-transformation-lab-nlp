-- Design B: pre-coordinated. One local concept per measure x tooth x site
-- (concept_code 'PD|3|MB'; tooth-level 'STATUS|3|-'), so the row fits base OMOP,
-- but every query has to decode the concept code to get the tooth and site back.
site_rows AS (
  SELECT m.visit_occurrence_id AS visit_id,
         CAST(split_part(c.concept_code, '|', 2) AS INT) AS tooth,
         split_part(c.concept_code, '|', 3) AS site,
         MAX(CASE WHEN split_part(c.concept_code, '|', 1) = 'PD'  THEN m.value_as_number END) AS pd_mm,
         MAX(CASE WHEN split_part(c.concept_code, '|', 1) = 'CAL' THEN m.value_as_number END) AS cal_mm,
         MAX(CASE WHEN split_part(c.concept_code, '|', 1) = 'BOP' THEN m.value_as_number END) AS bop
  FROM {schema}.measurement m
  JOIN {schema}.concept c ON c.concept_id = m.measurement_concept_id
  WHERE c.vocabulary_id = 'DENTAL_PRECOORD' AND split_part(c.concept_code, '|', 1) IN ('PD', 'CAL', 'BOP')
  GROUP BY 1, 2, 3
),
tooth_rows AS (
  SELECT m.visit_occurrence_id AS visit_id,
         CAST(split_part(c.concept_code, '|', 2) AS INT) AS tooth,
         MAX(CASE WHEN split_part(c.concept_code, '|', 1) = 'STATUS' THEN m.value_as_number END) AS status,
         MAX(CASE WHEN split_part(c.concept_code, '|', 1) = 'FURC'   THEN m.value_as_number END) AS furcation,
         MAX(CASE WHEN split_part(c.concept_code, '|', 1) = 'MOB'    THEN m.value_as_number END) AS mobility
  FROM {schema}.measurement m
  JOIN {schema}.concept c ON c.concept_id = m.measurement_concept_id
  WHERE c.vocabulary_id = 'DENTAL_PRECOORD' AND split_part(c.concept_code, '|', 1) IN ('STATUS', 'FURC', 'MOB')
  GROUP BY 1, 2
),
