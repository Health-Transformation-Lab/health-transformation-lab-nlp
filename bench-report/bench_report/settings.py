"""Every setting the app reads, declared once (AGENTS.md "Configuration and secrets"). Same names in every
environment; no per-environment defaults in code.

    BENCH_REPORT_SOURCE         databricks (default) or fixtures
    DATABRICKS_HOST             workspace URL, https://...            required for databricks
    DATABRICKS_WAREHOUSE_ID     SQL warehouse id (16 hex characters)  required for databricks
    BENCH_REPORT_CATALOG        Unity Catalog catalog, default health_transformation_lab
    BENCH_REPORT_CACHE_SECONDS  how long a report's rows are reused, default 300; 0 = every request queries
    BENCH_REPORT_FIXTURES_DIR   snapshot folder for fixtures, default tests/fixtures

Authentication is the Databricks SDK's own: a Databricks App's service principal (DATABRICKS_CLIENT_ID and
DATABRICKS_CLIENT_SECRET, set by the platform), OAuth M2M, or DATABRICKS_TOKEN for a local run. The app never
reads or logs a credential's value.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SOURCES = ("databricks", "fixtures")
_WAREHOUSE = re.compile(r"^[0-9a-f]{16}$")
_IDENT = re.compile(r"^[a-z][a-z0-9_]*$")


class SettingsError(ValueError):
    """A required setting is missing or malformed; the message names it."""


@dataclass(frozen=True)
class Settings:
    source: str
    catalog: str
    cache_seconds: int
    host: str | None = None
    warehouse_id: str | None = None
    fixtures_dir: Path | None = None


def load(env: dict[str, str] | None = None) -> Settings:
    """Read and check every setting; raise SettingsError naming the first bad one."""
    env = os.environ if env is None else env
    source = env.get("BENCH_REPORT_SOURCE", "databricks").strip().lower()
    if source not in SOURCES:
        raise SettingsError(f"BENCH_REPORT_SOURCE must be one of {', '.join(SOURCES)}, not {source!r}")
    catalog = env.get("BENCH_REPORT_CATALOG", "health_transformation_lab").strip()
    if not _IDENT.match(catalog):
        raise SettingsError(f"BENCH_REPORT_CATALOG must be a lowercase snake_case name, not {catalog!r}")
    raw = env.get("BENCH_REPORT_CACHE_SECONDS", "300").strip()
    if not raw.isdigit():
        raise SettingsError(f"BENCH_REPORT_CACHE_SECONDS must be a whole number of seconds, not {raw!r}")
    if source == "fixtures":
        folder = Path(env.get("BENCH_REPORT_FIXTURES_DIR") or HERE / "tests" / "fixtures")
        if not folder.is_dir():
            raise SettingsError(f"BENCH_REPORT_FIXTURES_DIR is not a folder: {folder}")
        return Settings(source, catalog, int(raw), fixtures_dir=folder)
    host = env.get("DATABRICKS_HOST", "").strip().rstrip("/")
    if not host:
        raise SettingsError("DATABRICKS_HOST is required (the workspace URL, https://...)")
    if not host.startswith("https://"):
        host = "https://" + host if "://" not in host else host
    if not host.startswith("https://"):
        raise SettingsError(f"DATABRICKS_HOST must be an https:// URL, not {host!r}")
    warehouse = env.get("DATABRICKS_WAREHOUSE_ID", "").strip()
    if not warehouse:
        raise SettingsError("DATABRICKS_WAREHOUSE_ID is required (SQL warehouses -> the warehouse -> Overview -> ID)")
    if not _WAREHOUSE.match(warehouse):
        raise SettingsError("DATABRICKS_WAREHOUSE_ID must be 16 lowercase hex characters (the id, not the name or "
                            "the HTTP path)")
    return Settings(source, catalog, int(raw), host=host, warehouse_id=warehouse)
