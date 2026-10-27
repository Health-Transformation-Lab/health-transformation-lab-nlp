"""Tooth- and site-level periodontal charts and the derived measures (spec 006).

A full-mouth chart: 32 teeth (universal numbering), six sites per tooth
(mesio-buccal, buccal, disto-buccal, mesio-lingual, lingual, disto-lingual).
Interproximal sites are MB, DB, ML, DL. Per site: probing depth (PD), clinical
attachment loss (CAL), bleeding on probing. Per tooth: present or missing (and
why), furcation class, mobility degree.

`draw_mouth` generates site values from a visit's summary chart so that the
derived measures reproduce it: max interproximal CAL, max PD and teeth lost to
periodontitis exactly; the share of bleeding sites on the same side of 10%;
complexity factors (furcation II/III, mobility 2+, < 20 teeth) only where the
chart's stage already allows them.

`derive` is the missing middle layer between raw sites and a person-level
phenotype: maxima, shares, and counts of *different teeth* over thresholds.
From it: the 2017 AAP/EFP stage (`aap_from_derived`, via labels.py) and the
2012 CDC/AAP surveillance category (`cdc_aap`; Eke et al., J Periodontol 2012).

Twins: r/R/07_sites.R (R) and omop/sql/site_designs/ (SQL on Postgres / Lakebase).
"""

from __future__ import annotations

import math
import random

import pandas as pd

from .labels import PerioChart, label_chart

TEETH = list(range(1, 33))
THIRD_MOLARS = {1, 16, 17, 32}
MOLARS = {1, 2, 3, 14, 15, 16, 17, 18, 19, 30, 31, 32}
SITES = ["MB", "B", "DB", "ML", "L", "DL"]
INTERPROXIMAL = {"MB", "DB", "ML", "DL"}

DERIVED = ["n_teeth_present", "teeth_lost_perio", "max_probing_depth_mm", "max_cal_mm", "bop_pct",
           "pct_teeth_ip_cal1", "n_teeth_ip_cal3", "n_teeth_ip_cal4", "n_teeth_ip_cal6",
           "n_teeth_ip_pd4", "n_teeth_ip_pd5", "n_sites_ip_pd5", "max_furcation_class", "max_mobility_degree"]


def draw_mouth(chart: PerioChart, pct_teeth_involved: float, rng: random.Random) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (sites, teeth). sites: tooth, site, pd_mm, cal_mm, bop. teeth: tooth, present,
    missing_reason ('perio' / 'other' / ''), furcation_class, mobility_degree."""
    site_cols, tooth_cols = draw_mouth_columns(chart, pct_teeth_involved, rng)
    return pd.DataFrame(site_cols), pd.DataFrame(tooth_cols)


def draw_mouth_columns(chart: PerioChart, pct_teeth_involved: float, rng: random.Random) -> tuple[dict, dict]:
    """draw_mouth as column lists, for building one table over many visits (scripts/22_build_sites.py)."""
    stage = label_chart(chart).value
    stage_n = int(stage[-1]) if stage.startswith("periodontitis") else 0
    missing = {t: "other" for t in THIRD_MOLARS if rng.random() < 0.5}
    pool = [t for t in TEETH if t not in missing]
    k = min(chart.teeth_lost_perio, len(pool))
    molars = [t for t in pool if t in MOLARS]                 # periodontitis takes molars first
    lost = rng.sample(molars, min(k, len(molars)))
    lost += rng.sample([t for t in pool if t not in lost], k - len(lost))
    for t in lost:
        missing[t] = "perio"
    present = [t for t in TEETH if t not in missing]
    if stage_n < 4 and len(present) < 20:          # < 20 teeth is a stage IV complexity factor
        for t in sorted(t for t, r in missing.items() if r == "other")[: 20 - len(present)]:
            del missing[t]
        present = [t for t in TEETH if t not in missing]

    max_cal, max_pd = chart.max_cal_mm or 0.0, chart.max_probing_depth_mm
    n_inv = 0 if max_cal < 1 else max(1, round(pct_teeth_involved / 100 * len(present)))
    involved = set(rng.sample(present, min(n_inv, len(present))))
    worst_tooth = rng.choice(sorted(involved)) if involved else rng.choice(present)
    worst_cal_site = (worst_tooth, rng.choice(sorted(INTERPROXIMAL)))
    worst_pd_site = (worst_tooth, rng.choice(SITES))

    # plain lists, one DataFrame at the end: same draws in the same order, without per-cell pandas work
    cols = {"tooth": [], "site": [], "pd_mm": [], "cal_mm": [], "bop": []}
    tooth_cal: dict[int, float] = {}
    for t in present:
        for s in SITES:
            if (t, s) == worst_cal_site:
                cal = max_cal
            elif t in involved and s in INTERPROXIMAL:
                cal = round(rng.uniform(1.0, max_cal), 1)
            elif t in involved:
                cal = round(rng.uniform(0.0, max_cal), 1)
            else:
                cal = round(rng.uniform(0.0, min(0.9, max_cal)), 1) if max_cal > 0 else 0.0
            if (t, s) == worst_pd_site:
                pd_ = max_pd
            else:
                pd_ = round(min(max_pd, 1 + (max_pd - 1) * rng.betavariate(1.5, 3.0)), 1) if max_pd > 1 else max_pd
            cal = min(cal, max_cal)
            cols["tooth"].append(t)
            cols["site"].append(s)
            cols["pd_mm"].append(min(pd_, max_pd))
            cols["cal_mm"].append(cal)
            cols["bop"].append(False)
            tooth_cal[t] = max(tooth_cal.get(t, cal), cal)
    n = len(cols["tooth"])
    k = math.floor(chart.bop_pct * n / 100) if chart.bop_pct < 10 else math.ceil(chart.bop_pct * n / 100)
    k = min(k, n)
    if chart.bop_pct < 10:
        k = min(k, math.ceil(0.1 * n) - 1)
    for i in rng.sample(range(n), k):
        cols["bop"][i] = True

    furcation, mobility = [0] * len(TEETH), [0] * len(TEETH)
    for t in present:
        i = t - 1
        if stage_n >= 3 and t in MOLARS and tooth_cal[t] >= 4 and rng.random() < 0.3:
            furcation[i] = rng.choice([2, 3])
        elif t in MOLARS and tooth_cal[t] >= 3 and rng.random() < 0.2:
            furcation[i] = 1
        if stage_n >= 4 and tooth_cal[t] >= 6 and rng.random() < 0.3:
            mobility[i] = 2
        elif tooth_cal[t] >= 5 and rng.random() < 0.2:
            mobility[i] = 1
    teeth = {"tooth": list(TEETH), "present": [t not in missing for t in TEETH],
             "missing_reason": [missing.get(t, "") for t in TEETH],
             "furcation_class": furcation, "mobility_degree": mobility}
    return cols, teeth


def derive(sites: pd.DataFrame, teeth: pd.DataFrame) -> dict:
    """Person-visit measures from site and tooth rows."""
    ip = sites[sites["site"].isin(INTERPROXIMAL)]
    present = teeth[teeth["present"].astype(bool)]
    by_tooth = ip.groupby("tooth").agg(cal=("cal_mm", "max"), pd=("pd_mm", "max"))

    def n_teeth(col, thr):
        return int((by_tooth[col] >= thr).sum())

    return {
        "n_teeth_present": len(present),
        "teeth_lost_perio": int((teeth["missing_reason"] == "perio").sum()),
        "max_probing_depth_mm": float(sites["pd_mm"].max()) if len(sites) else 0.0,
        "max_cal_mm": float(ip["cal_mm"].max()) if len(ip) else 0.0,
        "bop_pct": 100.0 * float(sites["bop"].astype(bool).mean()) if len(sites) else 0.0,
        "pct_teeth_ip_cal1": 100.0 * n_teeth("cal", 1) / len(present) if len(present) else 0.0,
        "n_teeth_ip_cal3": n_teeth("cal", 3), "n_teeth_ip_cal4": n_teeth("cal", 4),
        "n_teeth_ip_cal6": n_teeth("cal", 6), "n_teeth_ip_pd4": n_teeth("pd", 4),
        "n_teeth_ip_pd5": n_teeth("pd", 5), "n_sites_ip_pd5": int((ip["pd_mm"] >= 5).sum()),
        "max_furcation_class": int(present["furcation_class"].max()) if len(present) else 0,
        "max_mobility_degree": int(present["mobility_degree"].max()) if len(present) else 0,
    }


def derive_all(sites: pd.DataFrame, teeth: pd.DataFrame, key: str = "visit_id") -> pd.DataFrame:
    """derive() for every visit at once (sites and teeth carry `key`); one row per visit, indexed by `key`."""
    ip = sites[sites["site"].isin(INTERPROXIMAL)]
    by_tooth = ip.groupby([key, "tooth"]).agg(cal=("cal_mm", "max"), pd=("pd_mm", "max"))
    counts = pd.DataFrame({f"n_teeth_ip_{c}{t}": (by_tooth[c] >= t).groupby(level=key).sum()
                           for c, t in (("cal", 1), ("cal", 3), ("cal", 4), ("cal", 6), ("pd", 4), ("pd", 5))})
    present = teeth[teeth["present"].astype(bool)]
    p = present.groupby(key)
    n_present = p.size()
    out = pd.DataFrame({
        "n_teeth_present": n_present,
        "teeth_lost_perio": (teeth["missing_reason"] == "perio").groupby(teeth[key]).sum(),
        "max_probing_depth_mm": sites.groupby(key)["pd_mm"].max().astype(float),
        "max_cal_mm": ip.groupby(key)["cal_mm"].max().astype(float),
        "bop_pct": 100.0 * sites["bop"].astype(bool).groupby(sites[key]).mean(),
        "pct_teeth_ip_cal1": 100.0 * counts["n_teeth_ip_cal1"] / n_present,
        **{c: counts[c] for c in ("n_teeth_ip_cal3", "n_teeth_ip_cal4", "n_teeth_ip_cal6",
                                  "n_teeth_ip_pd4", "n_teeth_ip_pd5")},
        "n_sites_ip_pd5": (ip["pd_mm"] >= 5).groupby(ip[key]).sum(),
        "max_furcation_class": p["furcation_class"].max(),
        "max_mobility_degree": p["mobility_degree"].max(),
    })
    ints = [c for c in DERIVED if c.startswith("n_") or c.startswith("max_f") or c.startswith("max_m")
            or c == "teeth_lost_perio"]
    out[ints] = out[ints].fillna(0).astype(int)
    floats = ["max_probing_depth_mm", "max_cal_mm", "bop_pct", "pct_teeth_ip_cal1"]
    out[floats] = out[floats].fillna(0.0)
    out.index.name = key
    return out[DERIVED]


def aap_from_derived(d: dict, rbl_pct: float | None = None) -> str:
    """2017 AAP/EFP status from derived measures (labels.py rules); RBL comes from radiographs."""
    return label_chart(PerioChart(d["max_probing_depth_mm"], d["bop_pct"], d["max_cal_mm"],
                                  rbl_pct if rbl_pct is not None else (None if d["max_cal_mm"] is not None else 0),
                                  d["teeth_lost_perio"], furcation_class=d["max_furcation_class"],
                                  mobility_degree=d["max_mobility_degree"],
                                  remaining_teeth=d["n_teeth_present"])).value


def cdc_aap(d: dict) -> str:
    """2012 CDC/AAP surveillance case definition (Eke et al.). Interproximal sites;
    'different teeth' counts teeth, not sites. Returns severe / moderate / mild / none."""
    if d["n_teeth_ip_cal6"] >= 2 and d["n_sites_ip_pd5"] >= 1:
        return "severe"
    if d["n_teeth_ip_cal4"] >= 2 or d["n_teeth_ip_pd5"] >= 2:
        return "moderate"
    if (d["n_teeth_ip_cal3"] >= 2 and d["n_teeth_ip_pd4"] >= 2) or d["n_sites_ip_pd5"] >= 1:
        return "mild"
    return "none"
