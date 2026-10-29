"""PerioBench's EHR data-quality report: the React Perio Data Quality (DQ) Monitor design (2026-10-27) on the gold
tables Load results writes (spec 019 US1). Five domain tiles, then one section per domain:

    completeness           Zozus  visits with exam form, diagnosis codes and gum measurements all present
    accuracy               Zozus  rules on the whole record, measurements first (v0), agreeing with the truth
    consistency            Zozus  spread of periodontitis prevalence across clinics, in points (design rules)
    temporal plausibility  Kahn   visit pairs whose stage improved without treatment (design rules)
    reliability            Liaw   not assessed: needs real reviewers

The measures are the EHR DQ grader dashboard's (health_transformation_lab_nlp/dashboards.py, DQ_SQL), so the two
read the same numbers. Synthetic data, scored against the generator's truth: not clinical performance.
"""

from __future__ import annotations

from datetime import datetime

from .base import Report

# each evidence source as the study names it in fact_visit_evidence, and its plain name
VISIT_SOURCES = [("exam_form_status_code", "exam_form"), ("dx_completed_status_code", "proc_dx_completed"),
                 ("dx_planned_status_code", "proc_dx_planned"), ("note_status_code", "notes"),
                 ("probing_chart_status_code", "probing_chart"), ("rules_v0_status_code", "algorithm_v0"),
                 ("rules_design_status_code", "algorithm_design")]
SOURCE_LABELS = {"exam_form": "Exam form", "proc_dx_completed": "Diagnosis codes, done",
                 "proc_dx_planned": "Diagnosis codes, planned", "proc_codes_completed": "Procedure codes, done",
                 "proc_codes_planned": "Procedure codes, planned", "notes": "Chart note",
                 "probing_chart": "Gum measurements", "algorithm_v0": "Rules, measurements first (v0)",
                 "algorithm_design": "Rules, exam form first (design)", "radiograph_ai": "Radiograph AI"}
STATUS_LABELS = {"healthy_gingivitis": "Healthy / gingivitis", "periodontitis_stage_1": "Stage I",
                 "periodontitis_stage_2": "Stage II", "periodontitis_stage_3": "Stage III",
                 "periodontitis_stage_4": "Stage IV"}
SCALE_LABELS = {"all_visits": "All visits", "complete_cases": "Complete cases", "reference_set": "Reference set"}

# Display thresholds for the tile pills: starting points, as the design's footer says, not targets anyone agreed.
# (good at or past the first, watch at or past the second, else needs attention)
THRESHOLDS = {"completeness": ("higher", 90.0, 70.0), "accuracy": ("higher", 90.0, 75.0),
              "consistency": ("lower", 8.0, 15.0), "temporal": ("lower", 5.0, 10.0)}

SQL = {
    "provenance": """
select max(loaded_ts) as loaded_ts, max(git_commit_sha) as git_commit_sha, count(*) as visit_count,
  count(distinct clinic_code) as clinic_count
from {gold}.fact_visit_evidence""",
    # counts, not averages: Databricks averages decimals and DuckDB floats, so a share computed in SQL can round
    # differently in the last digit; shape() divides
    "by_clinic": """
select coalesce(clinic_code, 'All') as clinic, count(*) as visit_count,
  sum(case when exam_form_status_code <> 'unknown' and dx_completed_status_code <> 'unknown'
           and probing_chart_status_code <> 'unknown' then 1 else 0 end) as complete_count,
  sum(case when rules_v0_status_code = truth_status_code then 1 else 0 end) as agree_count,
  sum(case when rules_design_status_code = truth_status_code then 1 else 0 end) as agree_design_count
from {gold}.fact_visit_evidence
group by grouping sets ((clinic_code), ())""",
    "accuracy": "\nunion all\n".join(f"""
select coalesce(clinic_code, 'All') as clinic, '{name}' as source_name, count(*) as visit_count,
  sum(case when {col} <> 'unknown' then 1 else 0 end) as answered_count,
  sum(case when {col} <> 'unknown' and {col} = truth_status_code then 1 else 0 end) as agree_count
from {{gold}}.fact_visit_evidence
group by grouping sets ((clinic_code), ())""" for col, name in VISIT_SOURCES),
    "missingness": """
select evidence_column_name as column_name, missing_pct, missing_count, row_count
from {gold}.dq_column_missing
order by missing_pct desc, evidence_column_name""",
    "checks": """
select clinic_code as clinic, check_category_code as category, check_name, checked_count, failed_count,
  100 * pass_ratio as pass_pct, check_status_code as status
from {gold}.dq_check
order by check_category_code, check_name""",
    "scales": """
select method_name, group_name as scale_name, subject_count as visit_count,
  100 * periodontitis_ratio as periodontitis_pct, 100 * stage3_4_ratio as stage3_4_pct
from {gold}.dq_prevalence
where level_code = 'scale'
order by method_name, subject_count desc""",
    "concordance": """
select method_a_name, method_b_name, 100 * agreement_ratio as agree_pct, kappa_coef, visit_count
from {gold}.dq_source_concordance
where level_code = 'status'""",
    "prevalence_clinic": """
select group_name as clinic, subject_count as person_count, 100 * periodontitis_ratio as periodontitis_pct,
  100 * periodontitis_ci_low_ratio as ci_low_pct, 100 * periodontitis_ci_high_ratio as ci_high_pct
from {gold}.dq_prevalence
where level_code = 'clinic' and method_name = 'algorithm_design'
order by group_name""",
    "transitions": """
select from_status_code, to_status_code, visit_pair_count, row_pct, direction_code
from {gold}.dq_stage_transition""",
    "temporal": """
select method_name, visit_pair_count, 100 * better_ratio as improved_pct, 100 * same_ratio as same_pct,
  100 * worse_ratio as worse_pct, 100 * perio_resolved_ratio as resolved_pct,
  100 * stage_drop_ratio as stage_drop_pct
from {gold}.dq_temporal_change
order by better_ratio""",
    "injected": """
select injected_error_count, 100 * caught_ratio as caught_pct, 100 * false_flag_ratio as false_flag_pct
from {gold}.dq_injected_error""",
}

TABLES = ("fact_visit_evidence", "dq_column_missing", "dq_check", "dq_prevalence", "dq_source_concordance",
          "dq_stage_transition", "dq_temporal_change", "dq_injected_error")


def status(domain: str, value: float | None) -> str:
    if value is None:
        return "none"
    way, good, watch = THRESHOLDS[domain]
    if way == "higher":
        return "good" if value >= good else "warn" if value >= watch else "crit"
    return "good" if value <= good else "warn" if value <= watch else "crit"


def _r(v, d=1):
    return None if v is None else round(float(v), d)


def _pct(part, whole, d=1):
    return None if not whole else round(100 * part / whole, d)


def _clinic_sort(c: str):
    return (0, 0, c) if c == "All" else (1, int(c), c) if str(c).isdigit() else (1, 0, c)


def _source_sort(name: str):
    order = list(SOURCE_LABELS)
    return (order.index(name), name) if name in order else (len(order), name)


def _utc(ts: str | None) -> str | None:
    """One timestamp format whichever engine answered: Databricks gives ...172Z, DuckDB ...172000 (UTC, naive)."""
    if not ts:
        return ts
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None).isoformat(timespec="seconds") + "Z"


def shape(rows: dict[str, list[dict]]) -> dict:
    by_clinic = {r["clinic"]: r for r in rows["by_clinic"]}
    clinics = sorted(by_clinic, key=_clinic_sort)
    prev = rows["prevalence_clinic"]
    consistency = (_r(max(p["periodontitis_pct"] for p in prev) - min(p["periodontitis_pct"] for p in prev))
                   if prev else None)
    design = next((t for t in rows["temporal"] if t["method_name"] == "algorithm_design"), None)
    temporal = _r(design["improved_pct"]) if design else None
    overall = by_clinic.get("All", {})
    prov = rows["provenance"][0] if rows["provenance"] else {}

    def tiles_for(clinic: str) -> dict:
        c = by_clinic[clinic]
        comp, acc = _pct(c["complete_count"], c["visit_count"]), _pct(c["agree_count"], c["visit_count"])
        return {
            "completeness": {"value": comp, "unit": "% complete", "status": status("completeness", comp),
                             "scope": clinic},
            "accuracy": {"value": acc, "unit": "% vs truth", "status": status("accuracy", acc), "scope": clinic,
                         "design_value": _pct(c["agree_design_count"], c["visit_count"])},
            "consistency": {"value": consistency, "unit": "pt spread", "status": status("consistency", consistency),
                            "scope": "All"},
            "temporal": {"value": temporal, "unit": "% improved", "status": status("temporal", temporal),
                         "scope": "All"},
            "reliability": {"value": None, "unit": "", "status": "none", "scope": "All"},
        }

    trans = rows["transitions"]
    stages = [s for s in STATUS_LABELS if any(t["from_status_code"] == s for t in trans)]
    cell = {(t["from_status_code"], t["to_status_code"]): t for t in trans}
    conc = rows["concordance"]
    methods = sorted({c["method_a_name"] for c in conc} | {c["method_b_name"] for c in conc}, key=_source_sort)
    pair = {}
    for c in conc:
        pair[(c["method_a_name"], c["method_b_name"])] = pair[(c["method_b_name"], c["method_a_name"])] = c

    return {
        "synthetic": True,
        "provenance": {"loaded_ts": _utc(prov.get("loaded_ts")), "git_commit_sha": prov.get("git_commit_sha"),
                       "visit_count": prov.get("visit_count"), "clinic_count": prov.get("clinic_count")},
        "clinics": clinics,
        "thresholds": {k: {"direction": w, "good": g, "watch": m} for k, (w, g, m) in THRESHOLDS.items()},
        "tiles": {c: tiles_for(c) for c in clinics},
        "missingness": [{"column": r["column_name"], "missing_pct": _r(r["missing_pct"]),
                         "missing_count": r["missing_count"], "row_count": r["row_count"]}
                        for r in rows["missingness"]],
        "checks": [{"clinic": r["clinic"], "category": r["category"], "check": r["check_name"],
                    "checked_count": r["checked_count"], "failed_count": r["failed_count"],
                    "pass_pct": _r(r["pass_pct"], 2), "status": r["status"]}
                   for r in sorted(rows["checks"], key=lambda r: (_clinic_sort(r["clinic"]), r["category"],
                                                                   r["check_name"]))],
        "scales": [{"method": r["method_name"], "method_label": SOURCE_LABELS.get(r["method_name"], r["method_name"]),
                    "scale": r["scale_name"], "scale_label": SCALE_LABELS.get(r["scale_name"], r["scale_name"]),
                    "visit_count": r["visit_count"], "periodontitis_pct": _r(r["periodontitis_pct"]),
                    "stage3_4_pct": _r(r["stage3_4_pct"])} for r in rows["scales"]],
        "accuracy": [{"clinic": r["clinic"], "source": r["source_name"],
                      "source_label": SOURCE_LABELS.get(r["source_name"], r["source_name"]),
                      "visit_count": r["visit_count"], "answered_count": r["answered_count"],
                      "answered_pct": _pct(r["answered_count"], r["visit_count"]),
                      "agree_pct": _pct(r["agree_count"], r["answered_count"])}
                     for r in sorted(rows["accuracy"], key=lambda r: (_clinic_sort(r["clinic"]),
                                                                       _source_sort(r["source_name"])))],
        "concordance": {"methods": methods, "labels": [SOURCE_LABELS.get(m, m) for m in methods],
                        "agree_pct": [[None if a == b else _r(pair[(a, b)]["agree_pct"]) if (a, b) in pair else None
                                       for b in methods] for a in methods],
                        "kappa": [[None if a == b else _r(pair[(a, b)]["kappa_coef"], 2) if (a, b) in pair else None
                                   for b in methods] for a in methods]},
        "prevalence": {"overall_pct": _r(next((s["periodontitis_pct"] for s in rows["scales"]
                                               if s["method_name"] == "algorithm_design"
                                               and s["scale_name"] == "all_visits"), None)),
                       "clinics": [{"clinic": p["clinic"], "person_count": p["person_count"],
                                    "periodontitis_pct": _r(p["periodontitis_pct"]), "ci_low_pct": _r(p["ci_low_pct"]),
                                    "ci_high_pct": _r(p["ci_high_pct"])}
                                   for p in sorted(prev, key=lambda p: _clinic_sort(p["clinic"]))]},
        "transitions": {"stages": stages, "labels": [STATUS_LABELS[s] for s in stages],
                        "row_pct": [[_r(cell[(a, b)]["row_pct"]) if (a, b) in cell else 0.0 for b in stages]
                                    for a in stages],
                        "count": [[cell[(a, b)]["visit_pair_count"] if (a, b) in cell else 0 for b in stages]
                                  for a in stages],
                        "direction": [[cell[(a, b)]["direction_code"] if (a, b) in cell else None for b in stages]
                                      for a in stages]},
        "temporal": [{"method": t["method_name"], "method_label": SOURCE_LABELS.get(t["method_name"], t["method_name"]),
                      "pair_count": t["visit_pair_count"], "improved_pct": _r(t["improved_pct"]),
                      "same_pct": _r(t["same_pct"]), "worse_pct": _r(t["worse_pct"]),
                      "resolved_pct": _r(t["resolved_pct"]), "stage_drop_pct": _r(t["stage_drop_pct"])}
                     for t in rows["temporal"]],
        "injected": ({"injected_count": rows["injected"][0]["injected_error_count"],
                      "caught_pct": _r(rows["injected"][0]["caught_pct"]),
                      "false_flag_pct": _r(rows["injected"][0]["false_flag_pct"], 2)} if rows["injected"] else None),
        "overall_visit_count": overall.get("visit_count"),
    }


REPORT = Report(
    key="dq", title="Perio Data Quality (DQ) Monitor",
    summary="Is this dental record fit for finding gum disease (periodontal phenotyping)? Five data-quality "
            "domains: Zozus completeness, accuracy and consistency; Kahn temporal plausibility; Liaw reliability.",
    tables=TABLES, sql=SQL, shape=shape)
