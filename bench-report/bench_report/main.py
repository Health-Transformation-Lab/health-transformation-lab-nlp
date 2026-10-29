"""The FastAPI app: the bench registry and each report's payload under /api, and the built front end (web/dist).

    uvicorn bench_report.main:app                      # Databricks (DATABRICKS_HOST, DATABRICKS_WAREHOUSE_ID)
    BENCH_REPORT_SOURCE=fixtures uvicorn bench_report.main:app --reload   # the committed snapshot, no workspace

Settings are checked before the app serves (settings.py): a bad one stops it at start, naming the setting; then
one cheap authenticated call to the warehouse.
"""

from __future__ import annotations

import logging
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import benches, settings as settings_mod, sources

log = logging.getLogger("bench_report")
WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"


class _Cache:
    """A report's payload, reused for cache_seconds. One lock per report, so a cold warehouse is queried once
    however many people open the page at the same time."""

    def __init__(self, seconds: int):
        self.seconds = seconds
        self.items: dict[tuple[str, str], tuple[float, dict]] = {}
        self.locks: dict[tuple[str, str], threading.Lock] = {}
        self.guard = threading.Lock()

    def get(self, key, build):
        with self.guard:
            lock = self.locks.setdefault(key, threading.Lock())
        with lock:
            hit = self.items.get(key)
            if hit and time.monotonic() - hit[0] < self.seconds:
                return hit[1], True
            payload = build()
            if self.seconds:
                self.items[key] = (time.monotonic(), payload)
            return payload, False


def create_app(settings: settings_mod.Settings | None = None, source: sources.Source | None = None) -> FastAPI:
    state: dict = {}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        s = settings or settings_mod.load()               # raises SettingsError, naming the setting
        src = source or sources.make(s)
        src.check()                                       # raises QueryError before serving anything
        state.update(settings=s, source=src, cache=_Cache(s.cache_seconds))
        log.info("bench-report serving from %s, catalog %s", s.source, s.catalog)
        yield

    app = FastAPI(title="Bench report", lifespan=lifespan)

    @app.get("/api/health")
    def health():
        return {"ok": True, "source": state["settings"].source, "catalog": state["settings"].catalog}

    @app.get("/api/benches")
    def list_benches():
        return [{"key": b.key, "name": b.name, "tagline": b.tagline, "summary": b.summary, "status": b.status,
                 "gold_schema": b.gold_schema,
                 "reports": [{"key": r.key, "title": r.title, "summary": r.summary} for r in b.reports]}
                for b in benches.BENCHES]

    @app.get("/api/benches/{bench_key}/reports/{report_key}")
    def report(bench_key: str, report_key: str):
        bench = benches.get(bench_key)
        if bench is None:
            raise HTTPException(404, f"no bench {bench_key!r}")
        rep = bench.report(report_key)
        if rep is None:
            raise HTTPException(404, f"{bench.name} has no report {report_key!r}"
                                     + ("" if bench.reports else f" ({bench.name} is {bench.status}: no reports yet)"))
        s = state["settings"]
        gold = f"{s.catalog}.{bench.gold_schema}"

        def build():
            payload = rep.run(state["source"], gold)
            return {"bench": bench.key, "bench_name": bench.name, "report": rep.key, "title": rep.title,
                    "summary": rep.summary, "gold_schema": gold, "source": s.source,
                    "generated_ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), **payload}

        try:
            payload, cached = state["cache"].get((bench.key, rep.key), build)
        except sources.QueryError as e:
            log.error("report %s/%s failed: %s", bench.key, rep.key, e)
            raise HTTPException(502, f"the warehouse query failed: {e}") from e
        return {**payload, "cached": cached}

    if WEB_DIST.is_dir():
        app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            if path.startswith("api/"):
                raise HTTPException(404)
            f = WEB_DIST / path
            return FileResponse(f if path and f.is_file() and WEB_DIST in f.resolve().parents else WEB_DIST / "index.html")

    return app


app = create_app()
