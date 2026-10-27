-- Databricks notebook source
-- MAGIC %md
-- MAGIC # LLM judge at corpus scale (ai_query)
-- MAGIC
-- MAGIC Same prompt as `python/dental_omop_nlp/judge.py` (prompt version `judge-v2`, AAP worksheet rules), run as batch SQL.
-- MAGIC
-- MAGIC * Input: `${catalog}.${schema}.judge_queue` with columns `method, visit_id, note_text, pred`.
-- MAGIC   Build it from a **stratified sample** of each method's predictions (not all million notes:
-- MAGIC   judging every note costs as much as using the LLM as the classifier).
-- MAGIC * Notes must come from the de-identified zone. Confirm the endpoint is approved for this data first.
-- MAGIC * Output: `${catalog}.${schema}.judgments` with the quote gate applied in SQL.
-- MAGIC   Export it to `data/corpus/judgments_corpus.csv` and run `scripts/16_cost_effectiveness.py`.

-- COMMAND ----------

CREATE WIDGET TEXT catalog DEFAULT 'dental_omop';
CREATE WIDGET TEXT schema DEFAULT 'gold_dental_omop_perio';
CREATE WIDGET TEXT judge_endpoint DEFAULT '<your-judge-endpoint>';  -- a Model Serving endpoint approved for this data

-- COMMAND ----------

CREATE OR REPLACE TABLE IDENTIFIER(:catalog || '.' || :schema || '.judgments') AS
WITH raw AS (
  SELECT
    method, visit_id, pred, note_text,
    ai_query(
      :judge_endpoint,
      CONCAT(
        'You are a periodontist auditing an automated classifier. Judge whether the dental chart note ',
        'supports the predicted periodontal status under the 2017 AAP/EFP classification. ',
        'Follow the AAP staging and grading worksheet. ',
        'healthy: no interdental attachment loss, BOP < 10%. gingivitis: no interdental attachment loss, BOP >= 10%. ',
        'Initial stage from interdental CAL at the worst site (I 1-2 mm, II 3-4 mm, III/IV >= 5 mm); ',
        'use radiographic bone loss only when CAL is not recorded (I < 15%, II 15-33%, III/IV beyond coronal third). ',
        'Tooth loss due to perio: 1-4 teeth -> at least stage 3; >= 5 -> stage 4. ',
        'Complexity raises, never lowers: max probing depth > 4 mm -> at least stage 2; probing depth >= 6 mm, ',
        'vertical bone loss >= 3 mm or class II/III furcation -> at least stage 3; at stage 3, mobility >= 2, ',
        '< 20 remaining teeth, masticatory dysfunction, bite collapse, drifting/flaring or severe ridge defect -> stage 4. ',
        'Measured findings outrank a written diagnosis; ignore copied-forward text; ',
        'slight=stage 1, moderate=stage 2, severe=stage 3 (4 if >= 5 teeth lost to perio).\n\n',
        'Note:\n<<<\n', note_text, '\n>>>\n\nPredicted status: ', pred,
        '\n\nIs the predicted status supported by the note?'
      ),
      responseFormat => 'STRUCT<verdict: STRING, supported_status: STRING, quote: STRING, rationale: STRING>',
      modelParameters => named_struct('temperature', 0.0, 'max_tokens', 300),
      failOnError => false
    ) AS r
  FROM IDENTIFIER(:catalog || '.' || :schema || '.judge_queue')
)
SELECT
  method, visit_id, pred,
  r.result.verdict           AS verdict,
  r.result.supported_status  AS supported_status,
  r.result.quote             AS quote,
  r.result.rationale         AS rationale,
  -- quote gate: a verdict other than not_determinable must quote the note verbatim
  (r.errorMessage IS NULL
   AND r.result.verdict IN ('correct', 'incorrect', 'not_determinable')
   AND (r.result.verdict = 'not_determinable' OR (length(r.result.quote) > 0 AND instr(note_text, r.result.quote) > 0)))
                             AS gate_ok,
  coalesce(r.errorMessage, '') AS error,
  'judge-v2'                 AS prompt_version,
  :judge_endpoint            AS judge_model
FROM raw;

-- COMMAND ----------

SELECT method, verdict, gate_ok, count(*) AS n
FROM IDENTIFIER(:catalog || '.' || :schema || '.judgments')
GROUP BY ALL ORDER BY method, verdict;
