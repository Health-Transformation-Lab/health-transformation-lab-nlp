"""Where a report's rows come from. Both sources take the same SQL, with three-part names
(health_transformation_lab.gold_perio_bench.dq_check), and return a list of dicts.

    DatabricksSource  a SQL warehouse, through the Databricks SDK's statement execution API
    FixtureSource     the committed snapshot (tests/fixtures/<schema>/<table>.csv), in DuckDB, under the same names

Keep report SQL to what both engines run: lowercase keywords, CTEs, grouping sets, no Databricks-only functions.
"""

from __future__ import annotations

import json
import time
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from .settings import Settings


class QueryError(RuntimeError):
    """A statement failed or timed out; the message says which and why."""


class Source(Protocol):
    def check(self) -> None: ...

    def query(self, sql: str) -> list[dict]: ...


# Databricks result types -> Python, from the statement manifest
def _convert(value: str | None, type_name: str):
    if value is None:
        return None
    t = type_name.upper()
    if t in ("BYTE", "SHORT", "INT", "LONG"):
        return int(value)
    if t in ("FLOAT", "DOUBLE"):
        return float(value)
    if t == "DECIMAL":
        return float(Decimal(value))
    if t == "BOOLEAN":
        return value.lower() == "true"
    return value                                   # STRING, DATE, TIMESTAMP stay ISO text for JSON


class DatabricksSource:
    """Runs SQL on one SQL warehouse. Waits up to `timeout_seconds` (a stopped serverless warehouse starts in
    seconds; a classic one can take minutes), then cancels the statement and raises."""

    def __init__(self, settings: Settings, client=None, *, timeout_seconds: float = 300, poll_seconds: float = 1.0):
        if client is None:
            from databricks.sdk import WorkspaceClient
            client = WorkspaceClient(host=settings.host)
        self.client = client
        self.warehouse_id = settings.warehouse_id
        self.timeout_seconds = timeout_seconds
        self.poll_seconds = poll_seconds

    def check(self) -> None:
        """One cheap authenticated call before serving: the warehouse exists and this identity can see it."""
        try:
            self.client.warehouses.get(self.warehouse_id)
        except Exception as e:                                       # noqa: BLE001: say what failed, not a trace
            raise QueryError(f"cannot reach SQL warehouse {self.warehouse_id} ({type(e).__name__}: {e}); check "
                             "DATABRICKS_HOST, DATABRICKS_WAREHOUSE_ID and that this identity has CAN USE on it") from e

    def query(self, sql: str) -> list[dict]:
        from databricks.sdk.service.sql import Disposition, ExecuteStatementRequestOnWaitTimeout, Format
        st = self.client.statement_execution
        r = st.execute_statement(statement=sql, warehouse_id=self.warehouse_id, wait_timeout="30s",
                                 on_wait_timeout=ExecuteStatementRequestOnWaitTimeout.CONTINUE,
                                 disposition=Disposition.INLINE, format=Format.JSON_ARRAY)
        deadline = time.monotonic() + self.timeout_seconds
        while _state(r) in ("PENDING", "RUNNING"):
            if time.monotonic() > deadline:
                st.cancel_execution(r.statement_id)
                raise QueryError(f"statement {r.statement_id} still running after {self.timeout_seconds:.0f} s; "
                                 "cancelled")
            time.sleep(self.poll_seconds)
            r = st.get_statement(r.statement_id)
        if _state(r) != "SUCCEEDED":
            err = r.status.error.message if r.status and r.status.error else "no error message"
            raise QueryError(f"statement {r.statement_id} {_state(r)}: {err}")
        cols = [(c.name, c.type_name.value if hasattr(c.type_name, "value") else str(c.type_name))
                for c in r.manifest.schema.columns]
        data, result = [], r.result
        while result is not None:
            data.extend(result.data_array or [])
            nxt = result.next_chunk_index
            result = st.get_statement_result_chunk_n(r.statement_id, nxt) if nxt else None
        return [{n: _convert(v, t) for (n, t), v in zip(cols, row)} for row in data]


def _state(r) -> str:
    s = r.status.state if r.status else None
    return s.value if hasattr(s, "value") else str(s)


# snapshot column types (Databricks names, as the manifest gives them) -> DuckDB
_DUCK = {"STRING": "VARCHAR", "LONG": "BIGINT", "INT": "INTEGER", "SHORT": "SMALLINT", "BYTE": "TINYINT",
         "DOUBLE": "DOUBLE", "FLOAT": "FLOAT", "DECIMAL": "DOUBLE", "BOOLEAN": "BOOLEAN", "DATE": "DATE",
         "TIMESTAMP": "TIMESTAMP"}


class FixtureSource:
    """The snapshot of the gold tables `scripts/snapshot_fixtures.py` wrote, loaded into an in-memory DuckDB under
    their Databricks names. Each schema folder holds one CSV per table and `_types.json` with every column's type."""

    def __init__(self, settings: Settings):
        import duckdb
        self.folder = Path(settings.fixtures_dir)
        self.con = duckdb.connect()
        self.con.execute(f"attach ':memory:' as {settings.catalog}")
        for schema_dir in sorted(p for p in self.folder.iterdir() if (p / "_types.json").is_file()):
            types = json.loads((schema_dir / "_types.json").read_text())
            self.con.execute(f"create schema {settings.catalog}.{schema_dir.name}")
            for table, cols in types.items():
                spec = ", ".join(f"'{c}': '{_DUCK[t]}'" for c, t in cols.items())
                path = str(schema_dir / f"{table}.csv").replace("'", "''")
                self.con.execute(f"create table {settings.catalog}.{schema_dir.name}.{table} as select * from "
                                 f"read_csv('{path}', header = true, columns = {{{spec}}})")

    def check(self) -> None:
        self.con.execute("select 1").fetchone()

    def query(self, sql: str) -> list[dict]:
        cur = self.con.cursor().execute(sql)          # a cursor per query: reports run their queries in parallel
        names = [d[0] for d in cur.description]
        return [{n: (float(v) if isinstance(v, Decimal) else v.isoformat() if hasattr(v, "isoformat") else v)
                 for n, v in zip(names, row)} for row in cur.fetchall()]


def make(settings: Settings) -> Source:
    return FixtureSource(settings) if settings.source == "fixtures" else DatabricksSource(settings)
