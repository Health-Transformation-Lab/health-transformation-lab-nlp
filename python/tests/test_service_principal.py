"""Service principal setup for the uat/prod bundle targets (scripts/32_service_principal.py).
The plan is read from databricks.yml; apply is checked against a fake workspace client."""

from types import SimpleNamespace

import pytest

from dental_omop_nlp import service_principal as sp


def _actions(steps, kind):
    return [s for s in steps if s["action"] == kind]


def test_settings_follow_the_bundle_target():
    uat, prod, dev = (sp.target_settings(t) for t in ("uat", "prod", "dev"))
    assert (uat["catalog"], uat["schema"]) == ("dental_uat", "dental")
    assert (prod["catalog"], prod["schema"]) == ("dental_prod", "dental")
    assert (dev["catalog"], dev["schema"]) == ("workspace", "dental_dev")
    assert uat["warehouse_name"] == "Serverless Starter Warehouse"
    assert uat["secret_scope"] == "dental"
    with pytest.raises(KeyError):
        sp.target_settings("staging")


def test_overrides_win_like_bundle_vars():
    s = sp.target_settings("uat", overrides={"warehouse_name": "wh", "judge_endpoint": "ep", "catalog": None})
    assert (s["warehouse_name"], s["judge_endpoint"], s["catalog"]) == ("wh", "ep", "dental_uat")


def test_plan_covers_what_the_jobs_use():
    steps = sp.plan("uat", overrides={"judge_endpoint": "my-judge"})
    assert steps[0] == {"action": "service_principal", "display_name": "dental-omop-nlp-uat",
                        "entitlements": list(sp.ENTITLEMENTS)}
    (cat,) = _actions(steps, "grant_catalog")
    assert cat["name"] == "dental_uat" and {"USE_CATALOG", "CREATE_SCHEMA"} <= set(cat["privileges"])
    (sch,) = _actions(steps, "grant_schema")
    assert sch["name"] == "dental_uat.dental" and {"CREATE_TABLE", "CREATE_VOLUME", "CREATE_MODEL"} <= set(sch["privileges"])
    assert _actions(steps, "warehouse") == [{"action": "warehouse", "name": "Serverless Starter Warehouse",
                                            "level": "CAN_USE"}]
    assert _actions(steps, "serving_endpoint") == [{"action": "serving_endpoint", "name": "my-judge",
                                                   "level": "CAN_QUERY"}]
    assert _actions(steps, "secret_scope") == [{"action": "secret_scope", "name": "dental", "level": "READ"}]
    assert not _actions(steps, "oauth_secret")


def test_no_endpoint_step_when_judge_is_none_and_secret_only_on_request():
    steps = sp.plan("prod", create_secret=True)
    assert not _actions(steps, "serving_endpoint")
    assert _actions(steps, "oauth_secret") == [{"action": "oauth_secret", "scopes": ["all-apis"]}]
    assert steps[-1]["action"] == "oauth_secret"


def test_describe_never_needs_a_workspace():
    text = sp.describe(sp.plan("uat", create_secret=True))
    assert "dental-omop-nlp-uat" in text and "dental_uat.dental" in text and "all-apis" in text


# --- apply, against a fake WorkspaceClient -------------------------------------------------

class _Fake:
    """Records calls; looks enough like databricks.sdk.WorkspaceClient for apply()."""

    def __init__(self, existing=None, schema_exists=True, scopes=("dental",)):
        self.calls = []
        rec = self._rec
        existing_sp = [SimpleNamespace(id="42", application_id="app-1", display_name=existing)] if existing else []
        self.service_principals = SimpleNamespace(
            list=lambda **kw: rec("sp.list", **kw) or iter(existing_sp),
            create=lambda **kw: rec("sp.create", **kw) or SimpleNamespace(id="7", application_id="app-new"))
        self.grants = SimpleNamespace(update=lambda *a, **kw: rec("grants.update", *a, **kw))

        def get_schema(name):
            rec("schemas.get", name)
            if not schema_exists:
                raise sp.NotFound("no schema")
        self.schemas = SimpleNamespace(get=get_schema)
        self.warehouses = SimpleNamespace(
            list=lambda: iter([SimpleNamespace(id="wh1", name="Serverless Starter Warehouse")]),
            update_permissions=lambda *a, **kw: rec("wh.perm", *a, **kw))
        self.serving_endpoints = SimpleNamespace(
            get=lambda name: SimpleNamespace(id="ep-id-" + name),
            update_permissions=lambda *a, **kw: rec("ep.perm", *a, **kw))
        self.secrets = SimpleNamespace(
            list_scopes=lambda: iter([SimpleNamespace(name=s) for s in scopes]),
            put_acl=lambda *a, **kw: rec("secrets.put_acl", *a, **kw))
        self.service_principal_secrets_proxy = SimpleNamespace(
            create=lambda *a, **kw: rec("secret.create", *a, **kw) or SimpleNamespace(id="s1", secret="shh"))

    def _rec(self, name, *a, **kw):
        self.calls.append((name, a, kw))

    def names(self):
        return [c[0] for c in self.calls]


def test_apply_creates_and_grants_without_a_secret_by_default():
    pytest.importorskip("databricks.sdk")
    w = _Fake()
    out = sp.apply(sp.plan("uat", overrides={"judge_endpoint": "my-judge"}), w)
    assert out == {"application_id": "app-new", "id": "7", "created": True, "secret": None, "skipped": []}
    assert "sp.create" in w.names() and "secret.create" not in w.names()
    grants = [c for c in w.calls if c[0] == "grants.update"]
    assert [(g[1][0], g[1][1]) for g in grants] == [("catalog", "dental_uat"), ("schema", "dental_uat.dental")]
    assert all(g[2]["changes"][0].principal == "app-new" for g in grants)
    assert ("wh.perm", ("wh1",)) == w.calls[w.names().index("wh.perm")][:2]
    assert w.calls[w.names().index("ep.perm")][1] == ("ep-id-my-judge",)
    assert w.calls[w.names().index("secrets.put_acl")][1][:2] == ("dental", "app-new")


def test_apply_is_idempotent_and_skips_what_is_missing():
    pytest.importorskip("databricks.sdk")
    w = _Fake(existing="dental-omop-nlp-uat", schema_exists=False, scopes=())
    out = sp.apply(sp.plan("uat", create_secret=True), w)
    assert out["created"] is False and out["application_id"] == "app-1"
    assert "sp.create" not in w.names()
    assert [c[1][0] for c in w.calls if c[0] == "grants.update"] == ["catalog"]  # job creates and owns the schema
    assert "secrets.put_acl" not in w.names()
    assert {s.split(":")[0] for s in out["skipped"]} == {"grant_schema", "secret_scope"}
    assert out["secret"] == "shh"
    assert w.calls[w.names().index("secret.create")][1] == ("42",)
    assert w.calls[w.names().index("secret.create")][2] == {"scopes": ["all-apis"]}
