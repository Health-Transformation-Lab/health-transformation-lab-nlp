"""The grader dashboards (spec 018), built as Databricks AI/BI `.lvdash.json` from Python, so widgets and their
datasets are wired in one place instead of hand-edited JSON.

    python scripts/42_build_dashboards.py           # write databricks/dashboards/<name>.lvdash.json
    python scripts/42_build_dashboards.py --check   # exit 1 if a committed dashboard is stale

The grid is 6 columns wide. Datasets read dental_omop.gold_dental_omop_perio, the same names in every target, and
keep to SQL that DuckDB also runs, so the tests can run every query on the tables grader_tables builds.
"""

from __future__ import annotations

import hashlib
import json

from .telemetry import traced

GOLD = "dental_omop.gold_dental_omop_perio"


def _lines(text: str) -> list[str]:
    return [line + "\n" for line in text.strip("\n").split("\n")]


def _dataset(name: str, sql: str) -> dict:
    return {"name": name, "displayName": name, "queryLines": _lines(sql.replace("{gold}", GOLD))}


def _at(x, y, w, h) -> dict:
    return {"x": x, "y": y, "width": w, "height": h}


def _frame(title: str, description: str = "") -> dict:
    f = {"showTitle": True, "title": title}
    if description:
        f.update(showDescription=True, description=description)
    return f


def _text(name, markdown, pos) -> dict:
    return {"widget": {"name": name, "multilineTextboxSpec": {"lines": _lines(markdown)}}, "position": _at(*pos)}


def _fields(*cols, agg=None) -> list[dict]:
    """Plain columns, plus (name, expression) pairs for aggregates."""
    out = [{"name": c, "expression": f"`{c}`"} for c in cols]
    return out + [{"name": n, "expression": e} for n, e in (agg or [])]


def _counter(name, ds, field, title, description, pos) -> dict:
    return {"widget": {"name": name, "queries": [{"name": "main_query", "query": {
        "datasetName": ds, "fields": _fields(field), "disaggregated": True}}],
        "spec": {"version": 2, "widgetType": "counter", "encodings": {
            "value": {"fieldName": field, "displayName": title}}, "frame": _frame(title, description)}},
        "position": _at(*pos)}


def _table(name, ds, columns, title, description, pos) -> dict:
    """columns: (field, display name) pairs."""
    return {"widget": {"name": name, "queries": [{"name": "main_query", "query": {
        "datasetName": ds, "fields": _fields(*[c for c, _ in columns]), "disaggregated": True}}],
        "spec": {"version": 2, "widgetType": "table", "encodings": {
            "columns": [{"fieldName": c, "displayName": d} for c, d in columns]},
            "frame": _frame(title, description)}}, "position": _at(*pos)}


def _bar(name, ds, x, y, title, description, pos, *, agg=None, x_title="", y_title="", color=None) -> dict:
    """x categorical; y a column, or (field, aggregate expression) when the dataset is row level."""
    y_field, y_expr = (y, None) if isinstance(y, str) else y
    fields = _fields(x, *([color] if color else []), *([] if y_expr else [y_field]),
                     agg=[(y_field, y_expr)] if y_expr else None)
    enc = {"x": {"fieldName": x, "scale": {"type": "categorical"}, "displayName": x_title or x},
           "y": {"fieldName": y_field, "scale": {"type": "quantitative"}, "displayName": y_title or y_field}}
    if color:
        enc["color"] = {"fieldName": color, "scale": {"type": "categorical"}, "displayName": color}
    return {"widget": {"name": name, "queries": [{"name": "main_query", "query": {
        "datasetName": ds, "fields": fields, "disaggregated": not y_expr}}],
        "spec": {"version": 3, "widgetType": "bar", "encodings": enc, "frame": _frame(title, description)}},
        "position": _at(*pos)}


def _heatmap(name, ds, x, y, value, title, description, pos, *, x_title="", y_title="", value_title="") -> dict:
    return {"widget": {"name": name, "queries": [{"name": "main_query", "query": {
        "datasetName": ds, "fields": _fields(x, y, value), "disaggregated": True}}],
        "spec": {"version": 3, "widgetType": "heatmap", "encodings": {
            "x": {"fieldName": x, "scale": {"type": "categorical"}, "displayName": x_title or x},
            "y": {"fieldName": y, "scale": {"type": "categorical"}, "displayName": y_title or y},
            "color": {"fieldName": value, "scale": {"type": "quantitative"}, "displayName": value_title or value}},
            "frame": _frame(title, description)}}, "position": _at(*pos)}


def _filter(name, field, datasets, title, pos) -> dict:
    queries = [{"name": f"f_{name}_{ds}", "query": {"datasetName": ds, "fields": _fields(field),
                                                    "disaggregated": False}} for ds in datasets]
    return {"widget": {"name": name, "queries": queries, "spec": {
        "version": 2, "widgetType": "filter-multi-select", "encodings": {"fields": [
            {"fieldName": field, "displayName": title, "queryName": q["name"]} for q in queries]},
        "frame": _frame(title)}}, "position": _at(*pos)}


# ---------------------------------------------------------------- EHR DQ grader (spec 018 US2)

# each evidence source as the study names it, and its plain name (evidence_rules.md)
SOURCES = [("exam_form", "Exam form"), ("proc_dx_completed", "Diagnosis codes, done"),
           ("proc_dx_planned", "Diagnosis codes, planned"), ("notes", "Chart note"),
           ("probing_chart", "Gum measurements"), ("algorithm_v0", "Rules, measurements first (v0)"),
           ("algorithm_design", "Rules, exam form first (design)")]

DQ_SQL = {
    "tiles": """
SELECT
  ROUND(100 * AVG(CASE WHEN exam_form <> 'unknown' AND proc_dx_completed <> 'unknown' AND probing_chart <> 'unknown'
                       THEN 1.0 ELSE 0.0 END), 1) AS completeness_pct,
  ROUND(100 * AVG(CASE WHEN algorithm_v0 = truth_status THEN 1.0 ELSE 0.0 END), 1) AS accuracy_pct,
  ROUND(100 * AVG(CASE WHEN algorithm_design = truth_status THEN 1.0 ELSE 0.0 END), 1) AS accuracy_design_pct,
  (SELECT ROUND(100 * (MAX(periodontitis) - MIN(periodontitis)), 1) FROM {gold}.dq_prevalence
    WHERE level = 'clinic' AND method = 'algorithm_design') AS consistency_pts,
  (SELECT ROUND(100 * better, 1) FROM {gold}.dq_temporal WHERE method = 'algorithm_design') AS implausible_pct,
  COUNT(*) AS n_visits
FROM {gold}.dq_visits""",
    "missingness": """
SELECT evidence_column, ROUND(pct_missing, 1) AS pct_missing, n_missing, n_rows
FROM {gold}.dq_completeness
ORDER BY pct_missing DESC""",
    "checks": """
SELECT clinic, category, check_name, n_checked, n_fail, ROUND(100 * pass_rate, 2) AS pass_pct, status
FROM {gold}.dq_checks
ORDER BY CASE WHEN clinic = 'All' THEN 0 ELSE 1 END, clinic, category, check_name""",
    "accuracy": "\nUNION ALL\n".join(f"""
SELECT clinic, '{label}' AS evidence_source,
  CASE WHEN {col} <> 'unknown' THEN 100.0 ELSE 0.0 END AS answered_pct,
  CASE WHEN {col} = 'unknown' THEN NULL WHEN {col} = truth_status THEN 100.0 ELSE 0.0 END AS agree_pct
FROM {{gold}}.dq_visits""" for col, label in SOURCES),
    "concordance": """
SELECT method_a, method_b, ROUND(100 * pct_agree, 1) AS pct_agree, ROUND(kappa, 2) AS kappa, n
FROM {gold}.dq_concordance
WHERE level = 'status'""",
    "prevalence_clinic": """
SELECT group_name AS clinic, ROUND(100 * periodontitis, 1) AS periodontitis_pct,
  ROUND(100 * periodontitis_ci_low, 1) AS ci_low, ROUND(100 * periodontitis_ci_high, 1) AS ci_high, n
FROM {gold}.dq_prevalence
WHERE level = 'clinic' AND method = 'algorithm_design'
ORDER BY clinic""",
    "prevalence_scale": """
SELECT method, group_name AS scale, n, ROUND(100 * periodontitis, 1) AS periodontitis_pct,
  ROUND(100 * stage3_4, 1) AS stage3_4_pct
FROM {gold}.dq_prevalence
WHERE level = 'scale'
ORDER BY method, scale""",
    "transitions": """
SELECT from_status, to_status, n, ROUND(row_pct, 1) AS row_pct, direction
FROM {gold}.dq_transitions""",
    "temporal": """
SELECT method, pairs, ROUND(100 * better, 1) AS improved_pct, ROUND(100 * same, 1) AS same_pct,
  ROUND(100 * worse, 1) AS worse_pct, ROUND(100 * perio_resolved, 1) AS resolved_pct,
  ROUND(100 * stage_drop, 1) AS stage_drop_pct
FROM {gold}.dq_temporal
ORDER BY improved_pct""",
    "injected": """
SELECT injected_errors, ROUND(100 * caught_share, 1) AS caught_pct,
  ROUND(100 * flag_rate_without_error, 2) AS false_flag_pct
FROM {gold}.dq_injected_errors""",
}

DQ_BANNER = """## EHR DQ grader: is this dental record fit for periodontal phenotyping?
**Synthetic data** from the study's generator, scored against its own truth: **not clinical performance**. The
light version of the Perio DQ Monitor design: five domains (Zozus completeness, accuracy and consistency; Kahn
temporal plausibility; Liaw reliability), then one section per domain. Ask the **EHR DQ grader** Genie space for
anything not shown."""


@traced
def dq_grader() -> dict:
    filtered = ["accuracy", "prevalence_clinic"]          # checks keep their All rows, so they show every clinic
    tiles = [("t_complete", "completeness_pct", "Completeness (%)",
              "Visits with exam form, diagnosis codes and gum measurements all present. All clinics."),
             ("t_accuracy", "accuracy_pct", "Accuracy (%)",
              "Rules on the whole record, measurements first (v0), against the truth, all visits."),
             ("t_consistency", "consistency_pts", "Consistency (points)",
              "Spread of periodontitis prevalence across the 8 clinics (design rules). Smaller is steadier."),
             ("t_temporal", "implausible_pct", "Temporal plausibility (%)",
              "Visit pairs 1–2 years apart, no treatment between, whose stage improved (design rules). Lower is better.")]
    layout = [_text("banner", DQ_BANNER, (0, 0, 6, 3)),
              _filter("f_clinic", "clinic", filtered, "Clinic", (0, 3, 2, 2)),
              _text("how", "Tiles are for all clinics; the clinic filter applies to accuracy by source and "
                           "prevalence. The checks table lists every clinic and All. Per-visit evidence is in "
                           "`dq_visits` (statuses only, never note text).",
                    (2, 3, 4, 2))]
    layout += [_counter(n, "tiles", f, t, d, (i, 5, 1, 3)) for i, (n, f, t, d) in enumerate(tiles)]
    layout += [_text("t_reliability", "**Reliability** (Liaw)\n\n**Not assessed**: needs real reviewers to label "
                                      "charts. Simulated reviewers are a dry run.", (4, 5, 1, 3)),
               _counter("t_accuracy_design", "tiles", "accuracy_design_pct", "Accuracy, exam form first (%)",
                        "Rules in the study design's order. The order changes the answer.", (5, 5, 1, 3)),
               _text("s_complete", "### Completeness", (0, 8, 6, 1)),
               _bar("b_missing", "missingness", "evidence_column", "pct_missing", "Missing by evidence column (%)",
                    "Share of visits where the column is empty. Diagnosis codes done are missing as often as planned (29.5%); the per-source share answered is under Accuracy.", (0, 9, 3, 6),
                    x_title="Evidence column", y_title="Missing (%)"),
               _table("tb_checks", "checks", [("clinic", "Clinic"), ("category", "Category"),
                                               ("check_name", "Check"), ("n_checked", "Checked"),
                                               ("n_fail", "Failed"), ("pass_pct", "Pass (%)"),
                                               ("status", "Status")],
                      "Conformance, completeness and plausibility checks",
                      "All = every clinic together. PASS: no failures allowed and none found; REPORT: a rate to "
                      "read, with no pass mark.",
                      (3, 9, 3, 6)),
               _text("s_accuracy", "### Accuracy", (0, 15, 6, 1)),
               _bar("b_answered", "accuracy", "evidence_source", ("answered", "AVG(`answered_pct`)"),
                    "Visits each source gives a status for (%)", "", (0, 16, 2, 6),
                    x_title="Evidence source", y_title="Answered (%)"),
               _bar("b_agree", "accuracy", "evidence_source", ("agree", "AVG(`agree_pct`)"),
                    "Agreement with the truth where it answers (%)",
                    "Comparison to truth, the top rung of the accuracy hierarchy.", (2, 16, 2, 6),
                    x_title="Evidence source", y_title="Agrees with truth (%)"),
               _heatmap("h_concord", "concordance", "method_a", "method_b", "pct_agree",
                        "Concordance between sources (%)", "Comparison to independent measurement, truth excluded.",
                        (4, 16, 2, 6), value_title="Agree (%)"),
               _text("s_consistency", "### Consistency", (0, 22, 6, 1)),
               _bar("b_clinic", "prevalence_clinic", "clinic", "periodontitis_pct",
                    "Periodontitis prevalence by clinic (%)", "Design rules; 95% intervals in the table.",
                    (0, 23, 3, 6), x_title="Clinic", y_title="Periodontitis (%)"),
               _table("tb_clinic", "prevalence_clinic", [("clinic", "Clinic"), ("n", "People"),
                                                         ("periodontitis_pct", "Periodontitis (%)"),
                                                         ("ci_low", "95% CI low"), ("ci_high", "95% CI high")],
                      "By clinic, with intervals", "", (3, 23, 1, 6)),
               _table("tb_scale", "prevalence_scale", [("method", "Method"), ("scale", "Scale"), ("n", "Visits"),
                                                       ("periodontitis_pct", "Periodontitis (%)"),
                                                       ("stage3_4_pct", "Stage III–IV (%)")],
                      "By scale: all visits, complete cases, reference set", "", (4, 23, 2, 6)),
               _text("s_temporal", "### Temporal plausibility", (0, 29, 6, 1)),
               _heatmap("h_trans", "transitions", "to_status", "from_status", "row_pct",
                        "Stage at one visit (rows) and the next (columns), % of the row",
                        "Cells where the next visit's stage is lower than the earlier one show improvement: a charting or rule error unless treated.",
                        (0, 30, 3, 7), x_title="Next visit", y_title="Earlier visit", value_title="% of row"),
               _table("tb_temporal", "temporal", [("method", "Method"), ("pairs", "Visit pairs"),
                                                  ("improved_pct", "Improved (%)"), ("same_pct", "Same (%)"),
                                                  ("worse_pct", "Worse (%)"), ("resolved_pct", "Resolved (%)"),
                                                  ("stage_drop_pct", "Stage dropped (%)")],
                      "Implausible change by method", "Lower improved and resolved shares are more plausible.",
                      (3, 30, 3, 4)),
               _table("tb_injected", "injected", [("injected_errors", "Errors injected"),
                                                  ("caught_pct", "Caught (%)"),
                                                  ("false_flag_pct", "Flagged without an error (%)")],
                      "Injected charting errors the temporal checks catch (synthetic only)", "", (3, 34, 3, 3))]
    return {"datasets": [_dataset(n, s) for n, s in DQ_SQL.items()],
            "pages": [{"name": "dq_grader", "displayName": "EHR DQ grader", "pageType": "PAGE_TYPE_CANVAS",
                       "layout": layout}]}


DASHBOARDS = {"dq_grader": dq_grader}


# ---------------------------------------------------------------- Genie spaces (spec 018 US5)

def _id(text: str) -> str:
    """A stable 32-hex id, so rebuilding the space changes nothing unless its text does."""
    return hashlib.md5(text.encode()).hexdigest()


def _space(tables: list[str], instructions: list[str], questions: list[str]) -> dict:
    general = "\n\n".join(instructions)       # Genie keeps one general text instruction
    return {"version": 2,
            "config": {"sample_questions": sorted(({"id": _id(q), "question": [q]} for q in questions),
                                                  key=lambda q: q["id"])},
            "data_sources": {"tables": [{"identifier": f"{GOLD}.{t}"} for t in sorted(tables)]},
            "instructions": {"text_instructions": [{"id": _id(general), "content": [general]}]}}


DQ_TABLES = ["dq_checks", "dq_completeness", "dq_prevalence", "dq_temporal", "dq_transitions", "dq_concordance",
             "dq_visits", "dq_injected_errors"]

DQ_INSTRUCTIONS = [
    ("Every table holds synthetic data from the study's generator, scored against its own truth. Start every "
     "answer that gives a number with 'On synthetic data:' and never call a figure clinical performance."),
    ("dq_visits has one row per visit: clinic, visit date, each evidence source's status and truth_status. The "
     "evidence columns hold statuses (healthy, gingivitis, periodontitis_stage_1 to 4, or unknown when the source "
     "is missing), never note text. The column notes is the status read from the chart note."),
    ("Completeness: share of visits where exam_form, proc_dx_completed and probing_chart are all not 'unknown', "
     "from dq_visits. Missingness by column is dq_completeness.pct_missing."),
    ("Accuracy: share of visits where a source equals truth_status, from dq_visits. The headline uses algorithm_v0 "
     "(rules, gum measurements first). For a single evidence source, report both the share of visits it answers "
     "(not 'unknown') and its agreement with truth where it answers."),
    ("Consistency: the spread of periodontitis prevalence across clinics, MAX minus MIN of dq_prevalence."
     "periodontitis where level = 'clinic' and method = 'algorithm_design', in percentage points."),
    ("Temporal plausibility: dq_temporal.better for method 'algorithm_design', the share of visit pairs 1 to 2 "
     "years apart with no treatment between (dq_temporal.pairs) whose stage improved, which is implausible; lower "
     "is better. Use pairs as the denominator, not n_later_visits. dq_transitions has the full matrix: row_pct is "
     "the share of the earlier stage's visit pairs that moved to each stage."),
    ("Reliability (Liaw): not assessed. It needs real reviewers to label charts; the study's reviewers are "
     "simulated, so never report a reliability figure."),
    ("dq_checks holds each check per clinic; clinic = 'All' is every clinic together. Do not add the clinic rows to "
     "the 'All' rows."),
]

DQ_QUESTIONS = [
    "Which evidence source is missing most often?",
    "Which clinic has the highest periodontitis prevalence, and what is its 95% interval?",
    "How often does the exam form agree with the truth when it is filled in?",
    "Which data quality checks failed at clinic 3?",
    "What share of later visits show the stage improving, by method?",
    "How well do the chart note and the exam form agree with each other?",
]


@traced
def dq_genie() -> dict:
    return _space(DQ_TABLES, DQ_INSTRUCTIONS, DQ_QUESTIONS)


GENIE_SPACES = {"dq_grader": dq_genie}


@traced
def render(name: str) -> str:
    """The dashboard's .lvdash.json text, as committed."""
    return json.dumps(DASHBOARDS[name](), indent=2, ensure_ascii=False) + "\n"


@traced
def render_genie(name: str) -> str:
    """The Genie space's .geniespace.json text, as committed."""
    return json.dumps(GENIE_SPACES[name](), indent=2, ensure_ascii=False) + "\n"
