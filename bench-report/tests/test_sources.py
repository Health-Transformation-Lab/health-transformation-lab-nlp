"""Spec 029: the Databricks source waits for a statement, reads every chunk, converts types, and fails clearly.
A fake client stands in for the SDK's."""

from types import SimpleNamespace as NS

import pytest

from bench_report import settings, sources

S = settings.load({"DATABRICKS_HOST": "https://x.net", "DATABRICKS_WAREHOUSE_ID": "20e58799ac61f0da"})
COLS = NS(columns=[NS(name="n", type_name=NS(value="LONG")), NS(name="pct", type_name=NS(value="DECIMAL")),
                   NS(name="ok", type_name=NS(value="BOOLEAN")), NS(name="name", type_name=NS(value="STRING"))])


def _resp(state, data=None, nxt=None, error=None):
    return NS(statement_id="01", status=NS(state=NS(value=state), error=NS(message=error) if error else None),
              manifest=NS(schema=COLS), result=NS(data_array=data, next_chunk_index=nxt) if data else None)


class FakeStatements:
    def __init__(self, responses, chunks=None):
        self.responses, self.chunks, self.cancelled = list(responses), chunks or {}, False

    def execute_statement(self, **kw):
        assert kw["warehouse_id"] == "20e58799ac61f0da"
        return self.responses.pop(0)

    def get_statement(self, sid):
        return self.responses.pop(0)

    def get_statement_result_chunk_n(self, sid, n):
        return self.chunks[n]

    def cancel_execution(self, sid):
        self.cancelled = True


def _source(st, **kw):
    return sources.DatabricksSource(S, NS(statement_execution=st, warehouses=NS(get=lambda wid: None)),
                                    poll_seconds=0, **kw)


def test_waits_for_a_running_statement_and_reads_every_chunk():
    st = FakeStatements([_resp("PENDING"), _resp("RUNNING"),
                         _resp("SUCCEEDED", [["1", "12.50", "true", "a"]], nxt=1)],
                        {1: NS(data_array=[["2", None, "false", None]], next_chunk_index=None)})
    assert _source(st).query("select 1") == [{"n": 1, "pct": 12.5, "ok": True, "name": "a"},
                                             {"n": 2, "pct": None, "ok": False, "name": None}]


def test_a_failed_statement_raises_with_its_error():
    with pytest.raises(sources.QueryError, match="FAILED: TABLE_OR_VIEW_NOT_FOUND"):
        _source(FakeStatements([_resp("FAILED", error="TABLE_OR_VIEW_NOT_FOUND")])).query("select 1")


def test_a_statement_past_its_timeout_is_cancelled():
    st = FakeStatements([_resp("RUNNING")] * 5)
    with pytest.raises(sources.QueryError, match="cancelled"):
        _source(st, timeout_seconds=0).query("select 1")
    assert st.cancelled


def test_the_start_check_names_the_settings_to_look_at():
    def refuse(wid):
        raise PermissionError("403")
    src = sources.DatabricksSource(S, NS(warehouses=NS(get=refuse)))
    with pytest.raises(sources.QueryError, match="DATABRICKS_WAREHOUSE_ID"):
        src.check()
