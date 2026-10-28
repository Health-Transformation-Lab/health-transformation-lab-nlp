# The graders on Databricks (spec 019)

Two graders, each an AI/BI dashboard plus a Genie space you can ask questions in plain words. Both are light
versions of designs: the EHR DQ grader follows the React *Perio DQ Monitor*; the lab grader follows the pitch's
uplift and leaderboard slides (`docs/pitch/`). Synthetic data only; the lab grader is simulated until real runs
exist.

| Grader | Dashboard | Genie space | Tables (`dental_omop.gold_perio_bench`) |
|---|---|---|---|
| **EHR DQ grader**: is the dental record fit for periodontal phenotyping? | *EHR DQ grader* | *EHR DQ grader* | `dq_check`, `dq_column_missing`, `dq_prevalence`, `dq_temporal_change`, `dq_stage_transition`, `dq_source_concordance`, `fact_visit_evidence`, `dq_injected_error` |
| **Lab grader**: do AI answers on medical-dental and access-to-care questions improve with the open agent? | *Lab grader* | *Lab grader* | `dim_grader_question`, `fact_grader_answer` |

## EHR DQ grader

Five domain tiles, then one section per domain:

| Domain | Framework | Measure (the dashboard and Genie use the same definition) |
|---|---|---|
| Completeness | Zozus | Visits with exam form, diagnosis codes and gum measurements all present |
| Accuracy | Zozus | Rules on the whole record, gum measurements first (`algorithm_v0`), agreeing with the truth; each source's agreement where it answers |
| Consistency | Zozus | Spread of periodontitis prevalence across the 8 clinics, in points |
| Temporal plausibility | Kahn | Later visits whose stage improved (design rules); the full stage-to-stage matrix |
| Reliability | Liaw | **Not assessed**: needs real reviewers |

`fact_visit_evidence` holds statuses only (what each evidence source says, and the truth), never note text.

## Lab grader

**A SIMULATED sample until a real run exists: every number is made up.** `python/scripts/43_simulated_grader.py`
(seeded) writes `data/datasets/grader/simulated_grader_*.csv`: 25 questions in each of five categories, three
`sim:` models, each answering on its own and with the agent. A real run commits `grader/grader_questions.csv` and
`grader/grader_answers.csv` with the same columns, and Load results uses those instead. The *Simulated rows* tile
then reads 0.

Practices from GlobalDentBench (`docs/dentbench_methods.md`), as the pitch's uplift and leaderboard slides use them:

| On the dashboard | Measure |
|---|---|
| Uplift by category, access to care first | Score with the agent minus on its own, in points, with a 95% interval; cost per answer beside it |
| Leaderboard | Models ranked within a category, on their own and with the agent separately; never one overall rank |
| Safety | Unsafe (S1 + S2) and irreversible (S2) shares; harm graded by clinicians' rules, not by the judge |
| By reasoning level | L1 recall, L2 routine, L3 individualized, and their macro average |
| Cost against score | One point per model and answer mode |

Score = key points covered / key points (five per question). The judge comes from a family no evaluated model
shares.

## How it's built and deployed

- **Tables:** `dental_omop_nlp/grader_tables.py` builds each table from the committed CSVs. The *Load results* job
  overwrites them on every run, so a rerun leaves the same rows, and every row carries the `sha256` of its files.
- **Dashboards and spaces:** `dental_omop_nlp/dashboards.py` builds `databricks/dashboards/*.lvdash.json` and
  `databricks/genie/*.geniespace.json`. After changing it, run `cd python && python scripts/42_build_dashboards.py`.
  Never edit the JSON by hand: a test checks the committed files match the builder.
- **Tests:** every dashboard query runs in DuckDB on the same tables under the same names, so the SQL is checked
  before deploy.
- **Deploy:** the bundle deploys the dashboards (`databricks/resources/dashboards.yml`) and the Genie spaces
  (`databricks/resources/genie.yml`; Databricks CLI 1.3.0 or later, direct engine) in every target, under the
  same names.
