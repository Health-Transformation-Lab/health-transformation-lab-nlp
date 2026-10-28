# Databricks notebook source
# MAGIC %md
# MAGIC # Walkthrough: health-transformation-lab-nlp step by step
# MAGIC
# MAGIC Personal learning project; synthetic data and simulated reviewers only.
# MAGIC
# MAGIC One section per step of [`docs/code_walkthrough.md`](https://github.com/Health-Transformation-Lab/health-transformation-lab-nlp/blob/main/docs/code_walkthrough.md),
# MAGIC in run order. Each section links three levels: the **README** section (what the study does),
# MAGIC the **walkthrough** step (how the code does it), and the **code**, then shows the step's output
# MAGIC from the files in this Git folder. Rebuild the outputs with `python/scripts/make_parity_inputs.sh`.
# MAGIC
# MAGIC | # | Step |
# MAGIC |---|---|
# MAGIC | 1 | Generate the synthetic study |
# MAGIC | 2 | De-identify and gate |
# MAGIC | 3 | Read the diagnostic evidence |
# MAGIC | 4 | Compare the evidence |
# MAGIC | 5 | Rule-based phenotype |
# MAGIC | 6 | AI models read the notes |
# MAGIC | 7 | Reviewers stage charts |
# MAGIC | 8 | Reliability and the acceptance test |
# MAGIC | 9 | Five categories and evidence order |
# MAGIC | 10 | Over time: plausibility and data quality |
# MAGIC | 11 | Clinic prevalence |
# MAGIC | 12 | Predict progression |
# MAGIC | 13 | Site-level charts, both classifications |
# MAGIC | 14 | OMOP storage designs on Postgres |
# MAGIC | 15 | OMOP into Lakebase |
# MAGIC | 16 | LLM judge and cost at 1M notes |
# MAGIC | 17 | MedGemma |
# MAGIC | 18 | Deploy: dev, UAT, prod |

# COMMAND ----------

# DBTITLE 1,Setup: paths and link helper
import json
import os

import pandas as pd

REPO = os.path.abspath("../..")                      # this Git folder
GITHUB = "https://github.com/Health-Transformation-Lab/health-transformation-lab-nlp/blob/main/"
WALK = GITHUB + "docs/code_walkthrough.md"
try:
    host = "https://" + spark.conf.get("spark.databricks.workspaceUrl")  # noqa: F821
except Exception:
    host = None


def links(step, anchor, title, readme, files):
    def ws(p):
        return f"{host}/#workspace{REPO.removeprefix('/Workspace')}/{p}" if host else None
    rows = [f'<li><b>README</b> § <a href="{GITHUB}README.md#{readme}" target="_blank">{readme}</a></li>',
            f'<li><b>walkthrough</b> § <a href="{WALK}#{anchor}" target="_blank">{step}. {title}</a></li>']
    for p in files:
        w = f' <small>(<a href="{ws(p)}" target="_blank">workspace</a>)</small>' if ws(p) else ""
        rows.append(f'<li><b>code</b> <a href="{GITHUB}{p}" target="_blank">{p}</a>{w}</li>')
    html = "<ul style='font-size:15px;line-height:1.7;list-style:none;padding-left:0'>" + "".join(rows) + "</ul>"
    try:
        displayHTML(html)  # noqa: F821
    except NameError:
        print("\n".join(rows))


def show(path, cols=None, query=None, describe=False, n=20):
    p = f"{REPO}/{path}"
    if not os.path.exists(p):
        print(f"(not built yet: {path}; run python/scripts/make_parity_inputs.sh)")
        return
    d = pd.read_csv(p)
    if query:
        d = d.query(query)
    if cols:
        d = d[[c for c in cols if c in d.columns]]
    out = d.describe().T if describe else d.head(n)
    try:
        display(out)  # noqa: F821
    except NameError:
        print(out.to_string())


def show_json(path):
    p = f"{REPO}/{path}"
    print(json.dumps(json.load(open(p)), indent=1) if os.path.exists(p) else f"(not built yet: {path})")

# COMMAND ----------

# DBTITLE 1,1. Generate the synthetic study
links("1", "generate-the-synthetic-study", "Generate the synthetic study", "health-transformation-lab-nlp", ['python/health_transformation_lab_nlp/study.py', 'python/health_transformation_lab_nlp/synthetic.py', 'python/health_transformation_lab_nlp/clinical_notes.py', 'python/health_transformation_lab_nlp/labels.py'])
show_json("data/datasets/build_summary.json")

# COMMAND ----------

# DBTITLE 1,2. De-identify and gate
links("2", "de-identify-and-gate", "De-identify and gate", "ground-rules", ['python/health_transformation_lab_nlp/deid.py', 'python/health_transformation_lab_nlp/phi.py'])
show("data/datasets/deid_report.csv", describe=True)

# COMMAND ----------

# DBTITLE 1,3. Read the diagnostic evidence
links("3", "read-the-diagnostic-evidence", "Read the diagnostic evidence", "health-transformation-lab-nlp", ['python/health_transformation_lab_nlp/note_reader.py', 'python/health_transformation_lab_nlp/sources.py', 'python/health_transformation_lab_nlp/radiograph.py'])
show("data/datasets/method_coverage.csv")

# COMMAND ----------

# DBTITLE 1,4. Compare the evidence
links("4", "compare-the-evidence", "Compare the evidence", "health-transformation-lab-nlp", ['python/health_transformation_lab_nlp/phenotype.py'])
show("data/datasets/method_agreement.csv", query="level == 'status'")

# COMMAND ----------

# DBTITLE 1,5. Rule-based phenotype
links("5", "rule-based-phenotype", "Rule-based phenotype", "health-transformation-lab-nlp", ['python/health_transformation_lab_nlp/phenotype.py'])
show("data/datasets/answer_key/review_key.csv", cols=["visit_id", "truth_status", "algorithm_design", "algorithm_design_decided_by", "algorithm_v0", "algorithm_v0_decided_by"])

# COMMAND ----------

# DBTITLE 1,6. AI models read the notes
links("6", "ai-models-read-the-notes", "AI models read the notes", "models-evaluated-the-12-from-the-evaluation-sheet-modelsyaml", ['python/health_transformation_lab_nlp/rungs.py', 'models.yaml', 'python/health_transformation_lab_nlp/llm_reader.py', 'python/scripts/11_ai_predict.py'])
show("data/datasets/ai_predictions_tfidf_logreg.csv")

# COMMAND ----------

# DBTITLE 1,7. Reviewers stage charts
links("7", "reviewers-stage-charts", "Reviewers stage charts", "how-results-are-measured", ['labelstudio/chart_review.xml', 'docs/labeling_protocol.md', 'python/scripts/12_import_review.py'])
show("data/review/simulated_reviewer_labels.csv")

# COMMAND ----------

# DBTITLE 1,8. Reliability and the acceptance test
links("8", "reliability-and-the-acceptance-test", "Reliability and the acceptance test", "how-results-are-measured", ['python/health_transformation_lab_nlp/reliability.py', 'python/scripts/13_reliability.py', 'r/R/04_reliability.R'])
show("data/review/simulated_reliability/agreement_vs_humans.csv")

# COMMAND ----------

# DBTITLE 1,9. Five categories and evidence order
links("9", "five-categories-and-evidence-order", "Five categories and evidence order", "action-items", ['python/health_transformation_lab_nlp/phenotype.py', 'python/scripts/18_phenotype_order.py'])
show("data/review/simulated_reliability_5cat/phenotype_orders.csv", cols=["order", "is_design_order", "select_kappa", "holdout_kappa", "holdout_verdict", "selected"])

# COMMAND ----------

# DBTITLE 1,10. Over time: plausibility and data quality
links("10", "over-time-plausibility-and-data-quality", "Over time: plausibility and data quality", "action-items", ['python/health_transformation_lab_nlp/plausibility.py', 'python/health_transformation_lab_nlp/dq.py', 'python/scripts/20_data_quality.py'])
show("data/datasets/data_quality/dq_overall.csv"); show("data/datasets/data_quality/temporal_by_method.csv")

# COMMAND ----------

# DBTITLE 1,11. Clinic prevalence
links("11", "clinic-prevalence", "Clinic prevalence", "action-items", ['python/health_transformation_lab_nlp/prevalence.py', 'python/scripts/19_prevalence.py'])
show("data/datasets/prevalence/prevalence_by_clinic.csv", query="method in ['algorithm_design', 'truth_status']")

# COMMAND ----------

# DBTITLE 1,12. Predict progression
links("12", "predict-progression", "Predict progression", "action-items", ['python/health_transformation_lab_nlp/prediction.py', 'python/scripts/21_predict_progression.py'])
show("data/datasets/prediction/summary_algorithm_design.csv"); show("data/datasets/prediction/importance_algorithm_design.csv")

# COMMAND ----------

# DBTITLE 1,13. Site-level charts, both classifications
links("13", "site-level-charts-both-classifications", "Site-level charts, both classifications", "drill-downs", ['python/health_transformation_lab_nlp/sites.py', 'python/scripts/22_build_sites.py', 'r/R/07_sites.R'])
show("data/sites/aap_vs_cdc.csv")

# COMMAND ----------

# DBTITLE 1,14. OMOP storage designs on Postgres
links("14", "omop-storage-designs-on-postgres", "OMOP storage designs on Postgres", "drill-downs", ['python/health_transformation_lab_nlp/site_designs.py', 'omop/sql/site_designs/derived_tail.sql', 'python/scripts/23_site_designs.py'])
show("data/sites/site_designs.csv")

# COMMAND ----------

# DBTITLE 1,15. OMOP into Lakebase
links("15", "omop-into-lakebase", "OMOP into Lakebase", "drill-downs", ['python/health_transformation_lab_nlp/db.py', 'python/scripts/05_load_omop_db.py', 'databricks/notebooks/04_load_lakebase.py', 'omop/ddl/dental_extension.sql'])
print(open(f"{REPO}/omop/ddl/dental_extension.sql").read()[:1500])

# COMMAND ----------

# DBTITLE 1,16. LLM judge and cost at 1M notes
links("16", "llm-judge-and-cost-at-1m-notes", "LLM judge and cost at 1M notes", "drill-downs", ['python/health_transformation_lab_nlp/judge.py', 'python/health_transformation_lab_nlp/cost_effectiveness.py', 'costs.yaml'])
show("data/corpus/simulated_cost_effectiveness.csv")

# COMMAND ----------

# DBTITLE 1,17. MedGemma
links("17", "medgemma", "MedGemma", "drill-downs", ['python/health_transformation_lab_nlp/llm_reader.py', 'python/scripts/17_medgemma_lora.py', 'databricks/notebooks/03_medgemma_reader.py'])
show("data/datasets/simulated_llm_details_medgemma-1.5-4b-it.csv", cols=["visit_id", "status", "quote", "gate_ok", "fallback", "input_tokens"])

# COMMAND ----------

# DBTITLE 1,18. Deploy: dev, UAT, prod
links("18", "deploy-dev-uat-prod", "Deploy: dev, UAT, prod", "drill-downs", ['databricks.yml', 'databricks/resources/jobs.yml', '.github/workflows/deploy.yml'])
print(open(f"{REPO}/databricks.yml").read()[:2500])
