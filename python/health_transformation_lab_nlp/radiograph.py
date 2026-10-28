"""Structured findings from a radiograph AI (spec 003).

The output shape follows what radiograph AI tools report for periodontal bone:
CEJ-to-bone-crest distance in millimetres per site (FDA-cleared bone-level
measurement tools report this), from which % radiographic bone loss (RBL) is derived;
plus detections of vertical defects, furcation involvement and calculus. Error
model (planning assumptions until real vendor output is profiled, spec 003 T012):

  bone level noise      SD 0.6 mm per tooth
  vertical defects      mostly missed (detected 30%); bitewing CNNs reported to
                        detect horizontal bone loss well but not vertical
                        (Yavuz et al., EuroPerio10 2022)
  calculus, furcation   sensitivity 0.82, false positives giving precision ~0.66
                        (same source, weighted averages)
  availability          radiographs at 85% of visits; 4% unreadable
  coverage              bitewings image posterior teeth only

Simulated device: `sim-rad-ai`, model version `sim-1.0`. Only structured output
is modeled; images and DICOM headers are out of scope.
"""

from __future__ import annotations

import json
import random

from .labels import PerioChart
from .telemetry import traced

POSTERIOR = [2, 3, 4, 5, 12, 13, 14, 15, 18, 19, 20, 21, 28, 29, 30, 31]
MOLARS = {2, 3, 14, 15, 18, 19, 30, 31}
ALL_TEETH = [t for t in range(1, 33) if t not in (1, 16, 17, 32)]   # third molars excluded
ROOT_MM = 13.0          # nominal root length for % RBL
BIOLOGIC_MM = 2.0       # CEJ to crest in health
UNKNOWN = "unknown"

FEATURES = ["rad_present", "rad_max_rbl_pct", "rad_mean_rbl_pct", "rad_share_teeth_rbl15",
            "rad_vertical_defects", "rad_furcations", "rad_calculus_teeth", "rad_missing_teeth", "rad_is_bwx"]


@traced
def simulate_radiograph(chart: PerioChart, pct_teeth_involved: float, rng: random.Random,
                        availability: float = 0.85, failure_rate: float = 0.04, image: str | None = None,
                        noise_sd_mm: float = 0.6) -> dict:
    if rng.random() >= availability:
        return {"present": False}
    image = image or rng.choices(["4BWX", "FMX", "2BWX", "PAN"], weights=[0.45, 0.3, 0.15, 0.1])[0]
    base = {"present": True, "image": image, "device": "sim-rad-ai", "model_version": "sim-1.0"}
    if rng.random() < failure_rate:
        return {**base, "quality": "failed"}

    lost = rng.sample(POSTERIOR, min(chart.teeth_lost_perio, len(POSTERIOR)))
    other_missing = rng.sample([t for t in ALL_TEETH if t not in lost], rng.choice([0, 0, 1, 2]))
    missing = sorted(lost + other_missing)
    present = [t for t in ALL_TEETH if t not in missing]
    imaged = [t for t in present if t in POSTERIOR] if "BWX" in image else present

    n_inv = round(pct_teeth_involved / 100 * len(present)) if chart.rbl_pct > 0 else 0
    involved = set(rng.sample(present, min(n_inv, len(present)))) if n_inv else set()
    worst = rng.choice(sorted(involved)) if involved else None
    teeth = []
    for t in imaged:
        if t == worst:
            true_rbl = chart.rbl_pct
        elif t in involved:
            true_rbl = chart.rbl_pct * rng.uniform(0.55, 1.0)
        else:
            true_rbl = rng.uniform(0, 5)
        mm = max(0.5, BIOLOGIC_MM + true_rbl * ROOT_MM / 100 + rng.gauss(0, noise_sd_mm))
        rbl = max(0.0, (mm - BIOLOGIC_MM) / ROOT_MM * 100)
        vert_true = true_rbl > 33 and rng.random() < 0.3
        furc_true = t in MOLARS and true_rbl > 25 and rng.random() < 0.5
        calc_true = rng.random() < (0.45 if chart.bop_pct >= 10 else 0.15)
        teeth.append({"tooth": t, "cej_bc_mm": round(mm, 1), "rbl_pct": round(rbl, 1),
                      "vertical_defect": vert_true and rng.random() < 0.3,
                      "furcation": (furc_true and rng.random() < 0.82) or (t in MOLARS and rng.random() < 0.05),
                      "calculus": (calc_true and rng.random() < 0.82) or rng.random() < 0.05})
    rbls = [x["rbl_pct"] for x in teeth] or [0.0]
    return {**base, "quality": "ok", "teeth": teeth, "missing_teeth": missing,
            "max_rbl_pct": round(max(rbls), 1), "mean_rbl_pct": round(sum(rbls) / len(rbls), 1),
            "n_teeth_rbl15": sum(r >= 15 for r in rbls)}


@traced
def ok(r: dict) -> bool:
    return bool(r.get("present")) and r.get("quality") == "ok"


@traced
def features(r: dict) -> dict:
    if not ok(r):
        return {f: 0.0 for f in FEATURES}
    teeth = r["teeth"]
    n = max(len(teeth), 1)
    return {"rad_present": 1.0, "rad_max_rbl_pct": r["max_rbl_pct"], "rad_mean_rbl_pct": r["mean_rbl_pct"],
            "rad_share_teeth_rbl15": sum(t["rbl_pct"] >= 15 for t in teeth) / n,
            "rad_vertical_defects": float(sum(t["vertical_defect"] for t in teeth)),
            "rad_furcations": float(sum(t["furcation"] for t in teeth)),
            "rad_calculus_teeth": float(sum(t["calculus"] for t in teeth)),
            "rad_missing_teeth": float(len(r["missing_teeth"])),
            "rad_is_bwx": 1.0 if "BWX" in r["image"] else 0.0}


@traced
def read_radiograph(r: dict) -> str:
    """Stage from % RBL alone, as a LOWER BOUND: the stage is set by the worst of
    CAL, RBL and tooth loss, so bone loss on the image says "at least this stage".

    - Stage II or III only. Stage I bone loss (< 15%) is within measurement noise
      (0.6 mm is ~5% of a 13 mm root), and stage IV needs the cause of tooth loss,
      which the image doesn't show.
    - Needs >= 15% at two or more teeth, so one noisy tooth can't call disease.
    - No bone loss -> unknown: health and gingivitis look the same on an image.
    """
    if not ok(r):
        return UNKNOWN
    if r["max_rbl_pct"] < 15 or r.get("n_teeth_rbl15", 2) < 2:
        return UNKNOWN
    return "periodontitis_stage_2" if r["max_rbl_pct"] <= 33 else "periodontitis_stage_3"


@traced
def summary(r: dict) -> str:
    """One line for reviewers (Label Studio)."""
    if not r.get("present"):
        return "No radiograph at this visit"
    if r.get("quality") != "ok":
        return f"Radiograph AI ({r['image']}): image could not be read"
    worst = max(r["teeth"], key=lambda t: t["rbl_pct"]) if r["teeth"] else None
    f = features(r)
    parts = [f"Radiograph AI ({r['image']}, {r['device']} {r['model_version']}): "
             f"max bone loss {r['max_rbl_pct']:.0f}%" + (f" (#{worst['tooth']}, CEJ-crest {worst['cej_bc_mm']} mm)" if worst else ""),
             f"teeth with >=15% bone loss {int(f['rad_share_teeth_rbl15'] * len(r['teeth']))}/{len(r['teeth'])} imaged"]
    if f["rad_vertical_defects"]:
        parts.append(f"vertical defects {int(f['rad_vertical_defects'])}")
    if f["rad_furcations"]:
        parts.append(f"furcation {int(f['rad_furcations'])}")
    if f["rad_calculus_teeth"]:
        parts.append(f"calculus {int(f['rad_calculus_teeth'])} teeth")
    if r["missing_teeth"]:
        parts.append(f"missing teeth {len(r['missing_teeth'])}")
    return "; ".join(parts)


@traced
def to_json(r: dict) -> str:
    return json.dumps(r, separators=(",", ":"))
