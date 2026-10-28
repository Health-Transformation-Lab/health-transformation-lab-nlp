# Gold tables: `dental_omop.gold_dental_omop_perio`

> Personal learning project; synthetic data only. See [DISCLAIMER](../DISCLAIMER.md).

The gold schema holds the study's results: every model's answers on the 240 synthetic review charts, the
LLM reader's per-note details, and the judge scorecard behind the **Scorecard** AI/BI dashboard. The names
are the same in every target, because each environment is its own workspace.

| Diagram | Shows |
|---|---|
| [logical architecture](../diagrams/gold/gold_logical_architecture.png) ([.drawio](../diagrams/gold/source/gold_logical_architecture.drawio)) | How results reach gold, on the Databricks reference architecture |
| [physical architecture](../diagrams/gold/gold_physical_architecture.png) ([.drawio](../diagrams/gold/source/gold_physical_architecture.drawio)) | The same, with the deployed jobs, notebooks, schemas and tables |
| [data model, entity](../diagrams/gold/gold_data_model_entity.png) ([.drawio](../diagrams/gold/source/gold_data_model_entity.drawio)) | The 9 tables and how they relate |
| [data model, full](../diagrams/gold/gold_data_model_full.png) ([.drawio](../diagrams/gold/source/gold_data_model_full.drawio)) | Every column, type, logical key and description |

Every column is listed in [diagrams/gold/data_model.md](../diagrams/gold/data_model.md), generated with the ERDs from
[`diagrams/_build/gold_model.py`](../diagrams/_build/gold_model.py). A test (`python/tests/test_gold_model.py`) fails if
the declaration and the tables' columns drift apart. This page covers who writes what, how, and what to watch.

![Gold physical architecture](../diagrams/gold/gold_physical_architecture.png)

## The nine tables

| Table | Grain (one row per) | Logical key | Written by | Write mode |
|---|---|---|---|---|
| `result_files` | committed result file version | `sha256` | Load results (`10_load_results.py`) | delete-then-append by `sha256`, written last |
| `ai_predictions` | method × chart × file version (or reader run) | `sha256, visit_id`; reader rows: `source, run_id, method, visit_id` | Load results; MedGemma reader (`03`) | delete-then-append by `sha256`; reader: `replace_batch` on `(source, run_id, method)` |
| `llm_reader_runs` | LLM reader call on one chart | as `ai_predictions` | Load results; MedGemma reader | as `ai_predictions` |
| `chart_answers` | system × review chart | `visit_id, system` | Judge scorecard (`07`) | overwrite |
| `judgments` | judge call | `visit_id, kind, answer` | Judge scorecard; LLM judge SQL (`02`, see the caution below) | `07`: overwrite, keeping and resuming earlier calls; `02`: `CREATE OR REPLACE` |
| `judge_metrics` | system × metric | `system, metric` | Judge scorecard | overwrite |
| `judge_agreement` | slice of the judge vs truth comparison | `group, value` | Judge scorecard | overwrite |
| `judge_run` | call type (`status`, `verdict`, `all`) | `kind` | Judge scorecard | overwrite |
| `deid_scores` | de-identification engine × test tier | `method, tier` | Judge scorecard (from `data/deid/scores.csv`) | overwrite |

Delta doesn't enforce keys. "Logical key" means the columns that identify a row, and that a rerun must not
duplicate (AGENTS.md, "Failures, retries and reruns"). `visit_id` is the shared key across all of them: a
review chart in `data/datasets/answer_key/review_key.csv`, which is a file, not a gold table.

Jobs that haven't run in the workspace yet write more tables to gold: `study_benchmark`
(`01_run_benchmark.py`) writes `person`, `visit_occurrence`, `measurement`, `note`, `labeled_notes` and
`benchmark_results`, and `encoder_gpu` writes `encoder_gpu_predictions`. They aren't in the data model yet.

Also in the schema, though not tables: the Unity Catalog model `perio_note_classifier`
(`databricks/resources/mlops.yml`). The one function the Catalog Explorer lists isn't created by this
repo's code. The chart review agent's Unity Catalog functions are planned
(`databricks/agents/chart_review/AGENTS.md`) and will live here too.

## Results from anywhere (spec 016)

MedGemma and the GPU encoders run wherever a GPU is free (a Databricks job, Kaggle or a laptop). Every
committed result reaches these three tables. How the loading works: [results_storage.md](results_storage.md).

### `result_files`

One row per version of each `ai_predictions_<method>.csv` and `llm_details_<method>.csv` under
`data/datasets/` (`simulated_*` files are never loaded). Load results writes it last, so a load that fails
partway is redone on the next run.

### `ai_predictions`

The status each method gave each review chart. Class probabilities (`p_*`) stay in the committed CSV.

A changed file is a new version, and the old version's rows stay. For one answer per method, take the
latest `sha256` per `(source, method)`, or one `run_id`. The reader job's own rows (`source = databricks`)
carry the `sha256` of their scratch CSV but have no `result_files` row, so pick those by `run_id`; two runs
with the same answers even share a `sha256`. This query covers the `repo` and `kaggle` rows:

```sql
select p.method, p.visit_id, p.pred
from dental_omop.gold_dental_omop_perio.ai_predictions p
join (select sha256, row_number() over (partition by source, method order by loaded_at desc) as n
      from dental_omop.gold_dental_omop_perio.result_files where kind = 'predictions') f
  on f.sha256 = p.sha256 and f.n = 1;
```

### `llm_reader_runs`

One row per LLM reader call: the columns of `llm_details_<method>.csv` plus provenance. It matches
`ai_predictions` one to one on `method, visit_id, source` within one file version or one `run_id`. Across
versions there are several rows per key on both sides, and the two files have different `sha256` values, so
pair the latest version of each (by `loaded_at`) or one run.

New columns in a file are added to the table (`mergeSchema`). A column that is empty in a whole file
takes the type the table already has.

## Judge scorecard (spec 012)

![Gold data model](../diagrams/gold/gold_data_model_entity.png)

The `judge_scorecard` job writes these six tables, and the Scorecard dashboard reads them. Every metric is
computed in code (`python/dental_omop_nlp/judge_scorecard.py`), never by the LLM. Each table has a CSV
twin under `data/datasets/judge/` (`simulated_*` for dry runs). Full spec: `specs/012-judge-scorecard/data-model.md`.

### `chart_answers` and `judgments`

`chart_answers` holds every README system's answer on every chart. `judgments` holds one judge call per
chart (`kind = 'status'`, no answer shown) and one per distinct answer on a chart (`kind = 'verdict'`), so
one verdict serves every system that gave that answer. How the dashboard's chart drill-down joins them:

```sql
select a.system, a.visit_id, a.answer, a.truth, s.judge_status, v.verdict
from dental_omop.gold_dental_omop_perio.chart_answers a
left join dental_omop.gold_dental_omop_perio.judgments s on s.visit_id = a.visit_id and s.kind = 'status'
left join dental_omop.gold_dental_omop_perio.judgments v on v.visit_id = a.visit_id and v.kind = 'verdict' and v.answer = a.answer;
```

### `judge_metrics`

One row per system and metric, for every README phenotyping metric.

### `judge_agreement`

The judge's own status against the truth, overall (`all`), per `truth_status` and per `difficulty`.

### `judge_run`

Cost and speed per call type (`status`, `verdict`, `all`). With no judge run (`judge_endpoint = none`) it holds a single `all` row with no calls.

### `deid_scores`

The de-identification benchmark (`data/deid/scores.csv`) for the dashboard's de-identification page. It
doesn't join to the other tables.

## Cautions

- **`judgments` has two writers with different columns.** `07_judge_scorecard.py` writes the columns above.
  `02_llm_judge.sql` (the `llm_judge` job, corpus scale with `ai_query`) runs `CREATE OR REPLACE` with
  `method, visit_id, pred, verdict, supported_status, quote, rationale, gate_ok, error, prompt_version,
  judge_model`. Whichever ran last owns the table, and the dashboard and the scorecard's resume step expect
  `07`'s: if `02` ran last, the scorecard's resume step fails (`judge_scorecard.reusable` reads `endpoint`,
  which `02`'s table doesn't have). Run the corpus judge into another table name until that's settled.
- The scorecard keeps an earlier judge call only for the same endpoint and the current prompt version
  (`judge_scorecard.reusable`); a new endpoint asks, and pays for, every call again.
- `encoder_gpu_predictions` (the `encoder_gpu` job) is written by plain append with no batch key
  (`08_encoder_gpu.py`), so a rerun adds the same predictions again: against AGENTS.md, "Failures, retries
  and reruns". It isn't in the data model yet.
- `simulated_*` files are never loaded. `judgments.simulated = true` marks a simulated judge's rows: label
  anything built from them as simulated wherever it's shown.
