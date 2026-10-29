"""The bench registry (spec 029 US2), in bench order (AGENTS.md "The benchmarks"): PerioBench, then
OralHealthBench, then AccessBench. Each bench reads its own gold schema, gold_<bench>, in one catalog.

A bench with no report yet is still listed, with its status, so the front end can say what's coming. A bench's
first report is one entry here plus a module in reports/.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .reports import perio_dq
from .reports.base import Report

STATUSES = ("live", "planned", "exploratory")


@dataclass(frozen=True)
class Bench:
    key: str
    name: str
    tagline: str
    summary: str
    status: str
    reports: list[Report] = field(default_factory=list)

    @property
    def gold_schema(self) -> str:
        return f"gold_{self.key}"

    def report(self, key: str) -> Report | None:
        return next((r for r in self.reports if r.key == key), None)


BENCHES = [
    Bench("perio_bench", "PerioBench", "Trustworthy records",
          "Measure the data quality of electronic dental records.", "live", [perio_dq.REPORT]),
    Bench("oral_health_bench", "OralHealthBench", "Accurate AI answers",
          "Score the AI that millions of people ask on the questions that matter at the seam of medical and dental "
          "care: medicines, chronic disease, emergencies.", "planned"),
    Bench("access_bench", "AccessBench", "Getting care",
          "Whether an answer helps someone actually get care.", "exploratory"),
]


def get(key: str) -> Bench | None:
    return next((b for b in BENCHES if b.key == key), None)
