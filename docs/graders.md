# The graders on Databricks (spec 019)

Two graders, each an AI/BI dashboard plus a Genie space you can ask questions in plain words. Both are light
versions of designs: the EHR DQ grader follows the React *Perio DQ Monitor*; the lab grader follows the pitch's
uplift and leaderboard slides (`docs/pitch/`). Synthetic data only; the lab grader is simulated until real runs
exist.

| Grader | Dashboard | Genie space | Tables (`dental_omop.gold_dental_omop_perio`) |
|---|---|---|---|
| **EHR DQ grader**: is the dental record fit for periodontal phenotyping? | *EHR DQ grader* | *EHR DQ grader* | `dq_checks`, `dq_completeness`, `dq_prevalence`, `dq_temporal`, `dq_transitions`, `dq_concordance`, `dq_visits`, `dq_injected_errors` |
| **Lab grader**: do AI answers on medical-dental and access-to-care questions improve with the open agent? | spec 019 US4 (next) | spec 019 US5 (next) | `grader_questions`, `grader_answers` |

## EHR DQ grader

Five domain tiles, then one section per domain:

| Domain | Framework | Measure (the dashboard and Genie use the same definition) |
|---|---|---|
| Completeness | Zozus | Visits with exam form, diagnosis codes and gum measurements all present |
| Accuracy | Zozus | Rules on the whole record, gum measurements first (`algorithm_v0`), agreeing with the truth; each source's agreement where it answers |
| Consistency | Zozus | Spread of periodontitis prevalence across the 8 clinics, in points |
| Temporal plausibility | Kahn | Later visits whose stage improved (design rules); the full stage-to-stage matrix |
| Reliability | Liaw | **Not assessed**: needs real reviewers |

`dq_visits` holds statuses only (what each evidence source says, and the truth), never note text.

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
