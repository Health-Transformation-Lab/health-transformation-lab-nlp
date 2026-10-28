"""Three ways to store site-level periodontal data in OMOP, compared on Postgres / Lakebase (spec 006).

    A  post-coordinated   MEASUREMENT row per site and measure + SITE (tooth, tooth-site) + SITE_EVENT link
                          (OHDSI Dentistry Workgroup proposal)
    B  pre-coordinated    one local concept per measure x tooth x site in MEASUREMENT; tooth/site decoded
                          from the concept code
    C  site columns       MEASUREMENT with tooth_number and tooth_site columns (site-aware data table)

Each design gets its own schema with the full CDM 5.4 + dental extension, the same
mouths are loaded, and the same derived-measure query runs on each: the
design-specific part (omop/sql/site_designs/rows_*.sql) builds site_rows and
tooth_rows, and a shared tail (derived_tail.sql) computes the derived measures and
the 2012 CDC/AAP category. Results must equal Python's sites.derive().

`write_back_derived` stores the derived measures as MEASUREMENT rows (local
concepts N_TEETH_IP_CAL6 etc.) so cohort tools like Atlas can threshold them.
"""

from __future__ import annotations

import math
import re
import statistics
import time

import pandas as pd

from .db import EHR, create_schema, local_concepts
from .paths import REPO_ROOT
from .sites import SITES
from .telemetry import traced

SQL_DIR = REPO_ROOT / "omop" / "sql" / "site_designs"
DESIGNS = {"a_post_coordinated": "rows_a_post_coordinated.sql", "b_pre_coordinated": "rows_b_pre_coordinated.sql",
           "c_site_columns": "rows_c_site_columns.sql"}
SITE_MEASURES = {"pd_mm": ("PD", 2000000020), "cal_mm": ("CAL", 2000000021), "bop": ("BOP", 2000000022)}
TOOTH_MEASURES = {"status": ("STATUS", 2000000023), "furcation_class": ("FURC", 2000000024),
                  "mobility_degree": ("MOB", 2000000025)}
MEASUREMENT_FIELD = 1147138
DERIVED_CONCEPTS = {"n_teeth_present": 2000000030, "pct_teeth_ip_cal1": 2000000031, "n_teeth_ip_cal3": 2000000032,
                    "n_teeth_ip_cal4": 2000000033, "n_teeth_ip_cal6": 2000000034, "n_teeth_ip_pd4": 2000000035,
                    "n_teeth_ip_pd5": 2000000036, "n_sites_ip_pd5": 2000000037,
                    "max_furcation_class": 2000000038, "max_mobility_degree": 2000000039,
                    "max_probing_depth_mm": 2000000001, "bop_pct": 2000000002, "max_cal_mm": 2000000003,
                    "teeth_lost_perio": 2000000005}


@traced
def derived_sql(design: str, schema: str) -> str:
    rows = (SQL_DIR / DESIGNS[design]).read_text()
    tail = (SQL_DIR / "derived_tail.sql").read_text()
    return "WITH\n" + (rows + tail).replace("{schema}", schema)


@traced
def sql_stats(design: str) -> dict:
    """Size of the design-specific SQL (the shared tail is identical for all)."""
    body = "\n".join(ln for ln in (SQL_DIR / DESIGNS[design]).read_text().splitlines()
                     if ln.strip() and not ln.strip().startswith("--"))
    return {"sql_lines": body.count("\n") + 1, "sql_chars": len(body),
            "joins": len(re.findall(r"\bJOIN\b", body, re.IGNORECASE)),
            "decode_calls": len(re.findall(r"split_part", body, re.IGNORECASE))}


@traced
def precoordinated_concepts() -> pd.DataFrame:
    rows = []
    for mi, (code, _) in enumerate([*SITE_MEASURES.values(), *TOOTH_MEASURES.values()]):
        tooth_level = code in {c for c, _ in TOOTH_MEASURES.values()}
        for t in range(1, 33):
            for si, s in enumerate(["-"] if tooth_level else SITES):
                rows.append({"concept_id": 2001000000 + mi * 100000 + t * 10 + si,
                             "concept_name": f"{code} tooth {t}" + ("" if tooth_level else f" site {s}"),
                             "domain_id": "Measurement", "vocabulary_id": "DENTAL_PRECOORD",
                             "concept_class_id": "Clinical Observation", "concept_code": f"{code}|{t}|{s}",
                             "standard_concept": None, "valid_start_date": pd.Timestamp("2026-01-01").date(),
                             "valid_end_date": pd.Timestamp("2099-12-31").date()})
    return pd.DataFrame(rows)


def _long(sites: pd.DataFrame, teeth: pd.DataFrame, visits: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Long site and tooth measurement rows shared by all designs."""
    dates = visits.set_index("visit_id")["visit_date"]
    s = sites.melt(id_vars=["visit_id", "person_id", "tooth", "site"], value_vars=list(SITE_MEASURES),
                   var_name="measure", value_name="value")
    s["value"] = s["value"].astype(float)
    t = teeth.assign(status=lambda d: d["missing_reason"].map({"": 0, "other": 1, "perio": 2}).fillna(0)) \
        .melt(id_vars=["visit_id", "person_id", "tooth"], value_vars=list(TOOTH_MEASURES),
              var_name="measure", value_name="value")
    t["value"] = t["value"].astype(float)
    for d in (s, t):
        d["measurement_date"] = pd.to_datetime(dates.reindex(d["visit_id"]).to_numpy()).date
    return s, t


def _py(x):
    """Plain Python value for COPY: missing -> None, numpy scalar -> Python scalar."""
    if x is None or x is pd.NA or (isinstance(x, float) and math.isnan(x)):
        return None
    return x.item() if hasattr(x, "item") else x


def _copy(engine, schema: str, table: str, df: pd.DataFrame) -> None:
    cols = list(df.columns)
    raw = engine.raw_connection()
    try:
        with raw.cursor() as cur, cur.copy(f"COPY {schema}.{table} ({', '.join(cols)}) FROM STDIN") as cp:
            for row in df.itertuples(index=False):
                cp.write_row([_py(x) for x in row])
        raw.commit()
    finally:
        raw.close()


def _measurement(df: pd.DataFrame, concept_ids, start_id: int, source: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({"measurement_id": range(start_id, start_id + len(df)), "person_id": df["person_id"].to_numpy(),
                         "measurement_concept_id": concept_ids, "measurement_date": df["measurement_date"].to_numpy(),
                         "measurement_type_concept_id": EHR, "value_as_number": df["value"].to_numpy(),
                         "visit_occurrence_id": df["visit_id"].to_numpy(),
                         "measurement_source_value": source.to_numpy()})


@traced
def load_design(engine, design: str, schema: str, sites, teeth, visits) -> dict:
    from sqlalchemy import text
    create_schema(engine, schema)
    s, t = _long(sites, teeth, visits)
    concepts = local_concepts()
    if design == "b_pre_coordinated":
        pre = precoordinated_concepts()
        concepts = pd.concat([concepts, pre], ignore_index=True)
        code_to_id = dict(zip(pre["concept_code"], pre["concept_id"]))
        s_ids = [code_to_id[f"{SITE_MEASURES[m][0]}|{tt}|{ss}"] for m, tt, ss in zip(s.measure, s.tooth, s.site)]
        t_ids = [code_to_id[f"{TOOTH_MEASURES[m][0]}|{tt}|-"] for m, tt in zip(t.measure, t.tooth)]
    else:
        s_ids = s["measure"].map({k: v[1] for k, v in SITE_MEASURES.items()}).to_numpy()
        t_ids = t["measure"].map({k: v[1] for k, v in TOOTH_MEASURES.items()}).to_numpy()
    _copy(engine, schema, "concept", concepts)
    ms = _measurement(s, s_ids, 1, s["measure"] + "|" + s["tooth"].astype(str) + "|" + s["site"])
    mt = _measurement(t, t_ids, len(ms) + 1, t["measure"] + "|" + t["tooth"].astype(str))
    if design == "c_site_columns":
        with engine.begin() as c:
            c.execute(text(f"ALTER TABLE {schema}.measurement ADD COLUMN tooth_number INT, "
                           f"ADD COLUMN tooth_site VARCHAR(4)"))
        ms = ms.assign(tooth_number=s["tooth"].to_numpy(), tooth_site=s["site"].to_numpy())
        mt = mt.assign(tooth_number=t["tooth"].to_numpy(), tooth_site=None)
    _copy(engine, schema, "measurement", pd.concat([ms, mt], ignore_index=True))
    extra = {}
    if design == "a_post_coordinated":
        people = sorted(set(s["person_id"]) | set(t["person_id"]))
        site_rows, key = [], {}
        sid = 1
        for p in people:
            for tooth in range(1, 33):
                key[(p, tooth, None)] = sid
                site_rows.append((sid, p, 2000100000 + tooth, str(tooth), None))
                sid += 1
                for si, ss in enumerate(SITES, start=1):
                    key[(p, tooth, ss)] = sid
                    site_rows.append((sid, p, 2000110000 + tooth * 10 + si, f"{tooth}-{ss}", key[(p, tooth, None)]))
                    sid += 1
        site_df = pd.DataFrame(site_rows, columns=["site_id", "person_id", "site_concept_id", "site_source_value",
                                                   "parent_site_id"]).assign(site_type_concept_id=EHR)
        site_df["parent_site_id"] = site_df["parent_site_id"].astype("Int64")
        _copy(engine, schema, "site", site_df)
        ev = pd.DataFrame({"site_id": [key[(p, tt, ss)] for p, tt, ss in zip(s.person_id, s.tooth, s.site)]
                           + [key[(p, tt, None)] for p, tt in zip(t.person_id, t.tooth)],
                           "event_id": list(ms["measurement_id"]) + list(mt["measurement_id"])})
        ev.insert(0, "site_event_id", range(1, len(ev) + 1))
        ev["event_field_concept_id"] = MEASUREMENT_FIELD
        ev["site_event_type_concept_id"] = EHR
        _copy(engine, schema, "site_event", ev)
        with engine.begin() as c:   # indexes the link tables need for these joins
            c.execute(text(f"CREATE INDEX ON {schema}.site_event (event_id)"))
            c.execute(text(f"CREATE INDEX ON {schema}.site (parent_site_id)"))
        extra = {"site_rows": len(site_df), "site_event_rows": len(ev)}
    if design == "c_site_columns":
        with engine.begin() as c:
            c.execute(text(f"CREATE INDEX ON {schema}.measurement (visit_occurrence_id, tooth_number)"))
    with engine.begin() as c:
        c.execute(text(f"ANALYZE {schema}.measurement"))
    return {"measurement_rows": len(ms) + len(mt), "concept_rows": len(concepts), **extra}


@traced
def storage_bytes(engine, schema: str) -> int:
    q = ("SELECT COALESCE(SUM(pg_total_relation_size(quote_ident(schemaname) || '.' || quote_ident(tablename))), 0) "
         f"FROM pg_tables WHERE schemaname = '{schema}' AND tablename IN ('measurement', 'site', 'site_event', 'concept')")
    return int(pd.read_sql(q, engine).iloc[0, 0])


@traced
def run_derived(engine, design: str, schema: str, repeats: int = 3) -> tuple[pd.DataFrame, float]:
    sql = derived_sql(design, schema)
    times, out = [], None
    for _ in range(repeats):
        t0 = time.perf_counter()
        out = pd.read_sql(sql, engine)
        times.append(time.perf_counter() - t0)
    return out, statistics.median(times)


@traced
def write_back_derived(engine, schema: str, derived: pd.DataFrame, visits: pd.DataFrame, start_id: int) -> int:
    """Store derived measures as MEASUREMENT rows (local concepts), so cohort tools can use them."""
    d = derived.merge(visits[["visit_id", "person_id", "visit_date"]], on="visit_id")
    long = d.melt(id_vars=["visit_id", "person_id", "visit_date"], value_vars=list(DERIVED_CONCEPTS),
                  var_name="measure", value_name="value")
    df = pd.DataFrame({"measurement_id": range(start_id, start_id + len(long)),
                       "person_id": long["person_id"].to_numpy(),
                       "measurement_concept_id": long["measure"].map(DERIVED_CONCEPTS).to_numpy(),
                       "measurement_date": pd.to_datetime(long["visit_date"]).dt.date.to_numpy(),
                       "measurement_type_concept_id": EHR,     # derived rows are marked in measurement_source_value
                       "value_as_number": long["value"].astype(float).to_numpy(),
                       "visit_occurrence_id": long["visit_id"].to_numpy(),
                       "measurement_source_value": ("derived:" + long["measure"]).to_numpy()})
    _copy(engine, schema, "measurement", df)
    return len(df)
