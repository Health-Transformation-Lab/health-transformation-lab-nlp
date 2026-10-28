"""Databricks schema names, one set per bench (spec 019).

    perio_bench        periodontal status from charts: everything built so far (landing, bronze, silver, gold)
    access_bench       does an answer help someone actually get care (bronze, silver, gold; empty for now)
    oral_health_bench  the umbrella scorecard (bronze, silver, gold; empty for now)

Every target uses the same names (AGENTS.md, Conventions); databricks/resources/unity_catalog.yml declares them.
The old perio schemas, <layer>_dental_omop_perio, move to <layer>_perio_bench:
databricks/notebooks/12_migrate_bench_schemas.py does it, with the plans below.

    schema            <layer>_<bench>
    all_schemas       every bench schema, in bundle order
    MOVES             old perio schema -> new
    migration_plan    which tables to copy, given what exists
    versions_to_copy  which perio_note_classifier versions to copy
    files_to_copy     which landing volume files to copy
"""

from __future__ import annotations

from .telemetry import traced

CATALOG = "dental_omop"
LEGACY_DOMAIN = "dental_omop_perio"
LAYERS: dict[str, tuple[str, ...]] = {
    "perio_bench": ("landing", "bronze", "silver", "gold"),
    "access_bench": ("bronze", "silver", "gold"),
    "oral_health_bench": ("bronze", "silver", "gold"),
}
MOVES = {f"{layer}_{LEGACY_DOMAIN}": f"{layer}_perio_bench" for layer in LAYERS["perio_bench"]}
COPIED_FROM_TAG = "copied_from_version"   # set on each model version the migration copies


@traced
def schema(bench: str, layer: str) -> str:
    if layer not in LAYERS[bench]:
        raise ValueError(f"{bench} has no {layer} schema (layers: {LAYERS[bench]})")
    return f"{layer}_{bench}"


@traced
def all_schemas() -> list[str]:
    return [schema(bench, layer) for bench, layers in LAYERS.items() for layer in layers]


@traced
def migration_plan(existing: dict[str, set[str]]) -> list[tuple[str, str, str, str]]:
    """(action, old schema, new schema, table) for each table in an old schema: copy it if the new schema
    lacks it, else skip. existing maps each schema that exists to its tables; an old schema that isn't
    there (a target that never had it) contributes nothing."""
    plan = []
    for old, new in MOVES.items():
        have = existing.get(new, set())
        for t in sorted(existing.get(old, ())):
            plan.append(("skip" if t in have else "copy", old, new, t))
    return plan


@traced
def versions_to_copy(old_versions: list[int], copied_from: set[int]) -> list[int]:
    """Old model versions not yet copied (copied_from: the COPIED_FROM_TAG values on the new model)."""
    return sorted(v for v in old_versions if v not in copied_from)


@traced
def files_to_copy(old_files: set[str], new_files: set[str]) -> list[str]:
    """Relative paths in the old landing volume that the new one lacks."""
    return sorted(old_files - new_files)
