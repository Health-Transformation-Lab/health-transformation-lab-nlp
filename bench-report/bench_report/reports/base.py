from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass


@dataclass(frozen=True)
class Report:
    key: str
    title: str
    summary: str
    tables: tuple[str, ...]                     # every gold table its SQL reads (the snapshot copies these)
    sql: dict[str, str]                         # name -> SQL with {gold}
    shape: Callable[[dict[str, list[dict]]], dict]

    def run(self, source, gold: str) -> dict:
        """Run every query (in parallel: each is a round trip to the warehouse) and shape the payload."""
        with ThreadPoolExecutor(max_workers=min(8, len(self.sql))) as pool:
            futures = {n: pool.submit(source.query, s.replace("{gold}", gold)) for n, s in self.sql.items()}
            rows = {n: f.result() for n, f in futures.items()}
        return self.shape(rows)
