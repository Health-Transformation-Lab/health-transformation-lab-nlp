# MLflow and MLOps on Databricks

> Personal learning project; synthetic data. Practices from Databricks' public
> [MLOps workflows](https://docs.databricks.com/aws/machine-learning/mlops/mlops-workflow) guide and MLflow docs.

## What the repo does, against the guidance

| Databricks MLOps practice | In this repo | Where |
|---|---|---|
| Separate **dev, staging, prod** environments with clear transitions | dev / uat / prod bundle targets, each with its own catalog/schema, Lakebase instance, MLflow experiment and UC model | [`databricks.yml`](../databricks.yml), [deployment.md](deployment.md) |
| **Deploy code, not models**; production models trained by production code | The bundle deploys notebooks and jobs; models are trained and registered by those jobs in each environment | `databricks/resources/` |
| CI: unit tests on PR, integration in staging, release to prod | GitHub Actions: Python tests, R parity, Postgres tests, `bundle validate`; push to main deploys uat; prod on demand behind approval | [`.github/workflows/`](../.github/workflows/) |
| **Track every run** | MLflow runs for steps 11, 13, 15, 16, 18, 21, tagged with step, git commit, dataset fingerprint and `simulated` | [`tracking.py`](../python/dental_omop_nlp/tracking.py) |
| **Models in Unity Catalog** with signature and input example | Any rung (rules, TF-IDF, fusion, fine-tuned encoder) as one MLflow pyfunc, `catalog.schema.perio_note_classifier` | [`model_registry.py`](../python/dental_omop_nlp/model_registry.py), `11_ai_predict.py --register` |
| **Challenger → Champion** aliases; validate before promotion; record the outcome as tags | New version = challenger. Champion only if the **acceptance test** is non-inferior to the reviewers **and** it's at least as close to the human bar as the current champion. Verdict and difference stored as version tags. Refuses simulated reviewers unless asked | `promote_if_accepted`, [`24_promote_model.py`](../python/scripts/24_promote_model.py) |
| Inference loads the **champion alias**, so promotion needs no redeploy | `load_alias(name, "champion")`; batch scoring via `mlflow.pyfunc.spark_udf` on `models:/<name>@champion` | `model_registry.load_alias` |
| **LLM-as-judge with MLflow** | The judge is an MLflow GenAI judge (`make_judge`, same AAP criteria) with the quote gate; `mlflow.genai.evaluate` logs one trace per chart with the judge's assessment next to agreement with reviewer consensus; `15_judge.py --backend mlflow --judges databricks:/<endpoint>=<family>` | [`mlflow_judge.py`](../python/dental_omop_nlp/mlflow_judge.py) |
| **Databricks built-in judges** | `aap_guidelines`: the built-in Guidelines judge with five plain-language AAP rules, next to the custom judge; `no_phi_in_note`: a deterministic de-identification scan on the note the model read (no LLM) | `mlflow_judge.make_guidelines_judge`, `no_phi_in_note`; [`25_judge_monitoring.py`](../python/scripts/25_judge_monitoring.py) `eval` |
| Align the judge to human labels | `align_to_reviewers`: reviewer consensus logged as HUMAN feedback under the judge's name, then `judge.align()` (MLflow ≥ 3.14). Calibration (sensitivity, specificity, bake-off, Rogan-Gladen) stays in `cost_effectiveness.py` | `mlflow_judge.align_to_reviewers` |
| **Monitoring**: judges on live traffic, inference tables, data profiling, alerts | **Production monitoring of judges**: the custom judge and Guidelines judge score a sample of live traces (`judge_sample_rate`, default 10%), the PHI scan scores all; `judge_monitoring` job in uat/prod only. Also data quality per clinic and over time (`20_data_quality.py`). Not yet: inference tables, data profiling of predictions, alerts | `start_monitoring`, [`05_judge_monitoring.py`](../databricks/notebooks/05_judge_monitoring.py); action item G3 |
| **Retraining**: scheduled, then triggered | Not yet | action item G4 |
| Access: data scientists read-only in prod | Bundle gives `users` CAN_VIEW in uat/prod; jobs run as a service principal | `databricks.yml` permissions |

## Runs and artifacts

```bash
pip install -e ".[track]"                        # MLflow >= 3.4
python scripts/11_ai_predict.py --rung tfidf_logreg --register dental_dev.dental.perio_note_classifier
python scripts/13_reliability.py                  # acceptance test; logged to MLflow
python scripts/24_promote_model.py --model dental_dev.dental.perio_note_classifier --version 1 --rater ai:tfidf_logreg
mlflow ui --backend-store-uri sqlite:///mlruns/mlflow.db   # locally
```

On Databricks: `MLFLOW_TRACKING_URI=databricks`, the registry is Unity Catalog
(`databricks-uc`), and the experiment comes from the bundle
(`resources.experiments.dental_experiment`). Set `DENTAL_MLFLOW=0` to turn tracking off.

## Every judge, offline and live

```bash
python scripts/25_judge_monitoring.py eval --simulated                      # dry run, no LLM
python scripts/25_judge_monitoring.py eval --judge-model databricks:/<endpoint>
python scripts/25_judge_monitoring.py start --judge-model databricks:/<endpoint> --experiment-id <id> --sample-rate 0.1
python scripts/25_judge_monitoring.py stop --experiment-id <id>
```

| Scorer | Kind | Offline (`eval`) | Live (`start`) |
|---|---|---|---|
| `perio_status_supported` | custom judge (`make_judge`), AAP criteria and verbatim quote | every reviewed chart | sample of traces |
| `aap_guidelines` | built-in Guidelines judge | every reviewed chart | sample of traces |
| `no_phi_in_note` | deterministic PHI scan | every chart | every trace |
| `agrees_with_reviewers` | deterministic, vs reviewer consensus | every chart | (no reviewers on live traffic) |

Live monitoring needs the model served behind an endpoint with MLflow tracing on, so there are
traces to score; it runs only in uat and prod, where there is live traffic.

## The judge, two ways

| | `judge.py` + `ai_query` | `mlflow_judge.py` |
|---|---|---|
| Call | OpenAI-compatible endpoint, or `ai_query` in SQL at corpus scale | MLflow `make_judge` on any provider URI (`databricks:/<endpoint>`) |
| Output | verdict, supported status, verbatim quote | verdict and rationale starting with `QUOTE: "..."`, same quote gate |
| Logged | CSV | MLflow evaluation run: traces, assessments, `agrees_with_reviewers` |
| Best for | million-note batches (SQL) | review sets, judge bake-offs, alignment to reviewers |

Both share `judge.CRITERIA` and both feed the same calibration and cost-effectiveness code.

## Tested here, and not

- Tested locally on a sqlite MLflow store: tracking tags and metrics, pyfunc logging
  and loading, registry aliases and promotion rules, `mlflow.genai.evaluate` with a
  simulated judge scorer, judge definition and quote gate.
- Also tested locally: the Guidelines judge definition, the PHI scorer, the monitoring plan
  (sample rates), and the uat/prod-only monitoring job in the bundle.
- Not tested: a live judge model, Unity Catalog registry, judge alignment, starting
  monitoring (needs a workspace, an LLM endpoint and traced traffic).
