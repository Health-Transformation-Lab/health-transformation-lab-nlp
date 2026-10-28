"""Spec 017: Databricks AI Functions as phenotyping methods (no network: the SQL executor is faked)."""

import json
import subprocess
import sys

import pandas as pd
import pytest

from dental_omop_nlp import databricks_ai as dbai
from dental_omop_nlp.labels import LABELS
from dental_omop_nlp.paths import REPO_ROOT


def test_labels_cover_the_six_statuses_with_short_descriptions():
    labels = json.loads(dbai.classify_labels())
    assert set(labels) == set(LABELS)
    assert all(0 < len(d) <= 1000 for d in labels.values())          # ai_classify's limit per description


def test_statement_sends_notes_as_parameters_never_in_the_sql():
    notes = pd.DataFrame({"visit_id": [3, 7], "note_text": ["O'Brien note. BOP 40%", "Probing chart 7.5 mm UL6"]})
    sql, params = dbai.classify_statement(notes)
    assert "ai_classify(" in sql and "O'Brien" not in sql and "Probing chart 7.5 mm UL6" not in sql
    assert {p["value"] for p in params} >= {"O'Brien note. BOP 40%", "Probing chart 7.5 mm UL6", "3", "7"}
    assert all(p["type"] == "STRING" for p in params)


@pytest.mark.parametrize("value, status", [
    ('{"response": ["gingivitis"], "error_message": null}', "gingivitis"),     # v2 VARIANT, as JSON text
    ({"response": ["periodontitis_stage_2"]}, "periodontitis_stage_2"),        # v2, already parsed
    ("healthy", "healthy"),                                                    # v1 STRING
    (None, None),                                                              # could not classify
    ('{"response": null, "error_message": "content too long"}', None),
    ("periodontitis", None),                                                   # not one of the six
])
def test_parse_classify(value, status):
    assert dbai.parse_classify(value)[0] == status


def test_parse_classify_keeps_the_error_message():
    assert dbai.parse_classify('{"response": null, "error_message": "content too long"}')[1] == "content too long"


def _notes(n):
    return pd.DataFrame({"visit_id": range(n), "note_text": [f"note {i}" for i in range(n)]})


def test_run_classify_batches_and_returns_one_row_per_note():
    calls = []

    def execute(sql, params):
        calls.append(params)
        ids = [p["value"] for p in params if p["name"].startswith("i")]
        return [[i, '{"response": ["healthy"]}'] for i in ids]

    out = dbai.run_classify(_notes(23), execute=execute, batch_size=10)
    assert len(calls) == 3 and len(out) == 23
    assert list(out.columns) == ["visit_id", "pred", "error"] and set(out.pred) == {"healthy"}


def test_a_failed_batch_is_retried_once_then_no_answer():
    tries = {"n": 0}

    def execute(sql, params):
        tries["n"] += 1
        raise RuntimeError("warehouse unavailable")

    out = dbai.run_classify(_notes(4), execute=execute, batch_size=10)
    assert tries["n"] == 2 and out.pred.isna().all() and out.error.str.contains("warehouse unavailable").all()


def test_settings_are_checked_first_and_named(monkeypatch):
    for v in ("DATABRICKS_HOST", "DATABRICKS_TOKEN", "DATABRICKS_WAREHOUSE_ID"):
        monkeypatch.delenv(v, raising=False)
    with pytest.raises(RuntimeError, match="DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_WAREHOUSE_ID"):
        dbai.check_settings()


def test_estimate_counts_calls_and_tokens():
    e = dbai.estimate(_notes(25), batch_size=10)
    assert e["notes"] == 25 and e["statements"] == 3 and e["input_tokens"] > 0


# ---- US3: the reader on a Databricks Foundation Model endpoint

def test_openai_backend_defaults_to_the_databricks_workspace(monkeypatch):
    from dental_omop_nlp.llm_reader import OpenAIChat
    monkeypatch.delenv("READER_BASE_URL", raising=False)
    monkeypatch.delenv("READER_API_KEY", raising=False)
    monkeypatch.setenv("DATABRICKS_HOST", "adb-1.azuredatabricks.net")
    monkeypatch.setenv("DATABRICKS_TOKEN", "x")
    b = OpenAIChat(model="databricks-meta-llama-3-3-70b-instruct")
    assert b.base_url == "https://adb-1.azuredatabricks.net/serving-endpoints" and b.api_key == "x"


def test_llama_reader_is_in_the_registry_with_its_endpoint():
    import yaml
    m = next(m for m in yaml.safe_load((REPO_ROOT / "models.yaml").read_text())["models"]
             if m["id"] == "llama-3.3-70b-instruct")
    assert m["role"] == "llm" and m["endpoint"] == "databricks-meta-llama-3-3-70b-instruct"
    assert "Llama 3.3" in m["license"]


# ---- names in the results

def test_new_methods_have_plain_names_and_an_llm_group():
    from dental_omop_nlp import readme_results as rr
    assert rr.plain_system("dbai-classify") == "Databricks AI classify"
    assert rr.plain_system("llama-3.3-70b-instruct") == "Llama 3.3 70B"
    for m in ("dbai-classify", "llama-3.3-70b-instruct"):
        assert rr.phenotype_group(m) == rr.PHENOTYPE_GROUPS[6]
        assert "zero-shot LLM" in rr._model_method(m)


# ---- the script

def _script(*args, env=None):
    import os
    e = {k: v for k, v in os.environ.items() if not k.startswith("DATABRICKS_")}
    e.update(env or {})
    return subprocess.run([sys.executable, str(REPO_ROOT / "python" / "scripts" / "41_databricks_ai_methods.py"),
                           *args], capture_output=True, text=True, env=e, check=False)


def test_script_simulate_writes_only_simulated_files(tmp_path):
    r = _script("--simulate", "--out", str(tmp_path), "--limit", "12")
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "simulated_ai_predictions_dbai-classify.csv").exists()
    assert not (tmp_path / "ai_predictions_dbai-classify.csv").exists()
    assert "statements" in r.stdout                                   # the estimate is printed first


def test_script_without_settings_stops_and_names_them(tmp_path):
    r = _script("--out", str(tmp_path), "--limit", "2")
    assert r.returncode != 0 and "DATABRICKS_WAREHOUSE_ID" in (r.stdout + r.stderr)


# ---- waiting for a statement (ai_mask failed when one was still PENDING after 50 s)

def test_wait_polls_until_the_statement_finishes():
    states = iter([{"status": {"state": "RUNNING"}, "statement_id": "s"},
                   {"status": {"state": "SUCCEEDED"}, "result": {"data_array": [["x"]]}}])
    first = {"status": {"state": "PENDING"}, "statement_id": "s"}
    assert dbai.wait_for(first, get=lambda sid: next(states), sleep=lambda s: None) == [["x"]]


def test_wait_raises_on_failure_with_the_message():
    failed = {"status": {"state": "FAILED", "error": {"message": "quota exceeded"}}}
    with pytest.raises(RuntimeError, match="quota exceeded"):
        dbai.wait_for(failed, get=lambda sid: failed, sleep=lambda s: None)


def test_ai_mask_uses_the_waiting_executor():
    src = (REPO_ROOT / "python" / "dental_omop_nlp" / "deid.py").read_text()
    body = src[src.index("def _ai_mask_sql"):src.index("def detect_ai_mask")]
    assert "sql_execute(" in body and "urlopen" not in body


def test_ai_mask_has_a_plain_name_and_counts_as_an_ai_tool():
    from dental_omop_nlp import readme_results as rr
    assert rr.plain_tool("ai_mask+regex_v2+guard") == "Databricks AI mask + patterns + dental-word guard"
    assert rr.deid_group("ai_mask") == rr.DEID_GROUPS[1]
