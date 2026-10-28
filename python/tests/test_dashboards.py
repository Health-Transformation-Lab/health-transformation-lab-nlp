"""Spec 018: the grader dashboards are built by dental_omop_nlp.dashboards, and every dataset's SQL runs, here in
DuckDB, on the tables grader_tables builds from the committed CSVs, under the same three-part names as in Databricks."""

import json
import re

import pytest

from dental_omop_nlp import dashboards as dash
from dental_omop_nlp import grader_tables as gt
from dental_omop_nlp.paths import DATASETS_DIR, REPO_ROOT

duckdb = pytest.importorskip("duckdb")
DASH_DIR = REPO_ROOT / "databricks" / "dashboards"


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect()
    c.execute("ATTACH ':memory:' AS dental_omop")
    c.execute("CREATE SCHEMA dental_omop.gold_dental_omop_perio")
    for name, df in {**gt.dq_tables(DATASETS_DIR), **gt.lab_tables(DATASETS_DIR)}.items():
        c.register(f"src_{name}", df)
        c.execute(f"CREATE TABLE dental_omop.gold_dental_omop_perio.{name} AS SELECT * FROM src_{name}")
    return c


@pytest.mark.parametrize("name", sorted(dash.DASHBOARDS))
def test_committed_dashboard_matches_the_builder(name):
    built = dash.render(name)
    committed = (DASH_DIR / f"{name}.lvdash.json").read_text()
    assert committed == built, "run python python/scripts/42_build_dashboards.py"


def _datasets(name):
    return json.loads(dash.render(name))["datasets"]


def test_every_dq_dataset_runs_and_returns_rows(con):
    for ds in _datasets("dq_grader"):
        sql = "".join(ds["queryLines"])
        rows = con.execute(sql).fetchall()
        assert rows, ds["name"]


def test_dq_tiles_give_the_values_the_tables_hold(con):
    sql = {d["name"]: "".join(d["queryLines"]) for d in _datasets("dq_grader")}
    tiles = dict(zip([c[0] for c in con.execute(sql["tiles"]).description], con.execute(sql["tiles"]).fetchone()))
    visits = gt.dq_tables(DATASETS_DIR)["dq_visits"]
    known = (visits[["exam_form", "proc_dx_completed", "probing_chart"]] != "unknown").all(axis=1)
    assert tiles["completeness_pct"] == pytest.approx(round(100 * known.mean(), 1))
    acc = (visits.algorithm_v0 == visits.truth_status).mean()
    assert tiles["accuracy_pct"] == pytest.approx(round(100 * acc, 1))
    assert 0 < tiles["consistency_pts"] < 100 and 0 <= tiles["implausible_pct"] < 100


def test_every_widget_query_names_a_dataset_and_its_fields(con):
    for name in dash.DASHBOARDS:
        d = json.loads(dash.render(name))
        cols = {}
        for ds in d["datasets"]:
            cols[ds["name"]] = {c[0] for c in con.execute("".join(ds["queryLines"])).description}
        for page in d["pages"]:
            for item in page["layout"]:
                for q in item["widget"].get("queries", []):
                    ds = q["query"]["datasetName"]
                    assert ds in {x["name"] for x in d["datasets"]}, (name, ds)
                    if ds in cols:
                        for f in q["query"]["fields"]:
                            for col in re.findall(r"`([^`]+)`", f["expression"]):
                                assert col in cols[ds], (name, ds, col)


def test_dq_dashboard_says_synthetic_and_reliability_not_assessed():
    text = dash.render("dq_grader")
    assert "Synthetic data" in text and "not clinical performance" in text
    assert "Reliability" in text and "Not assessed" in text


def test_dashboards_are_in_the_bundle():
    bundle = (REPO_ROOT / "databricks" / "resources" / "dashboards.yml").read_text()
    for name in dash.DASHBOARDS:
        assert f"file_path: ../dashboards/{name}.lvdash.json" in bundle, name


GENIE_DIR = REPO_ROOT / "databricks" / "genie"


@pytest.mark.parametrize("name", sorted(dash.GENIE_SPACES))
def test_committed_genie_space_matches_the_builder(name):
    assert (GENIE_DIR / f"{name}.geniespace.json").read_text() == dash.render_genie(name), \
        "run python python/scripts/42_build_dashboards.py"


def test_dq_genie_space_reads_only_dq_tables_and_defines_each_tile():
    space = json.loads(dash.render_genie("dq_grader"))
    assert space["version"] == 2
    tables = {t["identifier"] for t in space["data_sources"]["tables"]}
    assert tables == {f"{dash.GOLD}.{n}" for n in gt.dq_tables(DATASETS_DIR)}
    text = " ".join(" ".join(i["content"]) for i in space["instructions"]["text_instructions"])
    for measure in ("Completeness", "Accuracy", "Consistency", "Temporal plausibility", "Reliability"):
        assert measure in text, measure
    assert "synthetic" in text.lower() and "note text" in text
    ids = [q["id"] for q in space["config"]["sample_questions"]] + \
          [i["id"] for i in space["instructions"]["text_instructions"]]
    assert all(re.fullmatch(r"[0-9a-f]{32}", i) for i in ids) and len(set(ids)) == len(ids)
    assert len(space["config"]["sample_questions"]) >= 4


@pytest.mark.parametrize("name", sorted(dash.GENIE_SPACES))
def test_genie_space_has_one_general_instruction_and_sorted_questions(name):
    # Genie keeps one general text instruction; sample questions are sorted by id, as an exported space is
    space = json.loads(dash.render_genie(name))
    assert len(space["instructions"]["text_instructions"]) == 1
    ids = [q["id"] for q in space["config"]["sample_questions"]]
    assert ids == sorted(ids)


def test_genie_spaces_are_in_the_bundle_and_ci_has_a_cli_that_knows_them():
    bundle = (REPO_ROOT / "databricks" / "resources" / "genie.yml").read_text()
    for name in dash.GENIE_SPACES:
        assert f"file_path: ../genie/{name}.geniespace.json" in bundle, name
    for wf in ("ci.yml", "deploy.yml"):
        pins = re.findall(r"databricks/setup-cli@v(\d+)\.(\d+)", (REPO_ROOT / ".github" / "workflows" / wf).read_text())
        assert pins and all((int(a), int(b)) >= (1, 3) for a, b in pins), wf   # genie_spaces: CLI 1.3.0


# ---------------------------------------------------------------- the lab grader (US4)

def _run(con, name, ds):
    sql = {d["name"]: "".join(d["queryLines"]) for d in _datasets(name)}[ds]
    return con.execute(sql).df()


def test_every_lab_dataset_runs_and_returns_rows(con):
    for ds in _datasets("lab_grader"):
        assert con.execute("".join(ds["queryLines"])).fetchall(), ds["name"]


def test_uplift_is_the_with_agent_score_minus_the_own_score_access_to_care_first(con):
    up = _run(con, "lab_grader", "uplift")
    assert up.category.iloc[0] == "Access to care"
    lab = gt.lab_tables(DATASETS_DIR)
    m = lab["grader_answers"].merge(lab["grader_questions"][["question_id", "category"]], on="question_id")
    mean = m.groupby(["category", "with_agent"]).score.mean().unstack()
    for r in up.itertuples():
        assert r.own_pct == pytest.approx(round(100 * mean.loc[r.category, False], 1))
        assert r.agent_pct == pytest.approx(round(100 * mean.loc[r.category, True], 1))
        assert r.uplift_lo <= r.uplift_pts <= r.uplift_hi


def test_leaderboard_ranks_only_within_a_category(con):
    lb = _run(con, "lab_grader", "leaderboard")
    assert set(lb.category) == set(gt.CATEGORIES)
    for (_, _), g in lb.groupby(["category", "answer_mode"]):
        assert sorted(g["rank"]) == list(range(1, len(g) + 1))
    assert "overall" not in dash.render("lab_grader").lower()


def test_safety_and_levels_follow_globaldentbench(con):
    s = _run(con, "lab_grader", "safety")
    assert ((s.unsafe_pct >= s.s2_pct) & (s.s2_pct >= 0)).all()
    lv = _run(con, "lab_grader", "by_level")
    assert set(lv.level) == {"L1", "L2", "L3", "Macro average"}


def test_lab_dashboard_and_space_say_simulated():
    text = dash.render("lab_grader")
    assert "SIMULATED" in text and "not a result" in text
    space = json.loads(dash.render_genie("lab_grader"))
    instructions = " ".join(" ".join(i["content"]) for i in space["instructions"]["text_instructions"])
    assert "simulated" in instructions and "never rank" in instructions.lower()
    tables = {t["identifier"] for t in space["data_sources"]["tables"]}
    assert tables == {f"{dash.GOLD}.grader_questions", f"{dash.GOLD}.grader_answers"}


def test_bundle_resource_keys_are_unique_across_resource_types():
    # bundle validate: "multiple resources ... have been defined with the same key" (a dashboard and a space)
    import yaml
    keys = []
    for f in sorted((REPO_ROOT / "databricks" / "resources").glob("*.yml")):
        for kind, items in (yaml.safe_load(f.read_text()).get("resources") or {}).items():
            keys += [(k, f"{f.name}:{kind}") for k in items]
    names = [k for k, _ in keys]
    assert len(names) == len(set(names)), sorted(x for x in keys if names.count(x[0]) > 1)
