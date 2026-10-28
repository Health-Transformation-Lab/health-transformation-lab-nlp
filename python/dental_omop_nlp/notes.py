"""Render a synthetic dental SOAP note from a perio chart.

The chart is the ground truth; the note is what the model sees. To make the
task non-trivial the renderer varies wording, uses common dental shorthand
(PD, BOP, CAL, RBL, SRP, prophy), sometimes omits a number, and adds negated
findings ("no BOP noted"), which is where rules-based baselines break.

The Assessment line states the clinician's call in free text roughly half the
time. With leak_assessment=False it is never stated, so the model must infer
status from the Objective findings alone. Benchmark both settings.
"""

from __future__ import annotations

import random

from .labels import PerioChart, Status, label_chart
from .telemetry import traced

_SUBJECTIVE = [
    "Pt presents for {visit}. {complaint}",
    "{visit}. Pt reports {complaint_lc}",
    "Here for {visit}. {complaint}",
]
_VISITS = ["recall exam", "periodic oral eval", "6 mo recall", "perio maintenance", "new pt exam"]
_COMPLAINTS = {
    "none": ["No complaints.", "No pain or concerns.", "Denies sensitivity."],
    "bleeding": ["Gums bleed when brushing.", "Notes bleeding w/ flossing."],
    "mobility": ["Reports a loose tooth LL.", "Feels teeth shifting."],
}
_PLAN = {
    Status.HEALTHY: ["Prophy. RTC 6 mo.", "Adult prophy, OHI reviewed. Recall 6 mo."],
    Status.GINGIVITIS: ["Prophy, OHI w/ emphasis on flossing. Recall 6 mo.",
                        "Prophy + OHI. Re-eval gingiva at next recall."],
    Status.P1: ["SRP 2 quads, re-eval 6 wk.", "Localized SRP, perio maint 4 mo."],
    Status.P2: ["SRP 4 quads, re-eval 6 wk.", "4 quad SRP, then perio maint q3-4 mo."],
    Status.P3: ["SRP 4 quads, refer to periodontist.", "Full mouth SRP, perio consult."],
    Status.P4: ["Refer to periodontist for comprehensive tx plan.",
                "Perio referral; extraction of hopeless teeth to be discussed."],
}
_ASSESS = {
    Status.HEALTHY: ["Periodontium WNL.", "Healthy gingiva."],
    Status.GINGIVITIS: ["Generalized gingivitis.", "Plaque-induced gingivitis."],
    Status.P1: ["Stage I periodontitis.", "Early perio."],
    Status.P2: ["Stage II periodontitis.", "Moderate periodontitis."],
    Status.P3: ["Stage III periodontitis.", "Severe periodontitis."],
    Status.P4: ["Stage IV periodontitis.", "Advanced perio w/ tooth loss."],
}
_VAGUE_ASSESS = ["See perio chart.", "Findings as above.", "Discussed w/ pt."]


def _objective(chart: PerioChart, rng: random.Random) -> str:
    parts: list[str] = []
    pd = chart.max_probing_depth_mm
    parts.append(rng.choice([f"PD max {pd:.0f}mm", f"probing depths up to {pd:.0f} mm",
                             f"deepest pocket {pd:.0f}mm"]))
    if chart.bop_pct < 10 and rng.random() < 0.6:
        parts.append(rng.choice(["no BOP noted", "BOP neg", "no bleeding on probing"]))
    else:
        parts.append(rng.choice([f"BOP {chart.bop_pct:.0f}%", f"bleeding at {chart.bop_pct:.0f}% of sites"]))
    if chart.max_cal_mm >= 1 or rng.random() < 0.3:  # sometimes omit a zero
        parts.append(rng.choice([f"CAL {chart.max_cal_mm:.0f}mm", f"attachment loss {chart.max_cal_mm:.0f} mm"]))
    if chart.rbl_pct > 0 and rng.random() < 0.85:
        parts.append(rng.choice([f"RBL ~{chart.rbl_pct:.0f}%", f"{chart.rbl_pct:.0f}% horizontal bone loss on BWX"]))
    elif chart.rbl_pct == 0 and rng.random() < 0.5:
        parts.append("no bone loss on BWX")
    if chart.teeth_lost_perio:
        parts.append(f"{chart.teeth_lost_perio} teeth previously lost to perio")
    rng.shuffle(parts)
    return "; ".join(parts) + "."


@traced
def render_soap_note(chart: PerioChart, seed: int, leak_assessment: bool = True) -> str:
    """Deterministic for a given (chart, seed)."""
    rng = random.Random(seed)
    status = label_chart(chart)
    if chart.bop_pct >= 30:
        complaint_key = "bleeding"
    elif chart.teeth_lost_perio or status in (Status.P3, Status.P4):
        complaint_key = rng.choice(["mobility", "none"])
    else:
        complaint_key = "none"
    complaint = rng.choice(_COMPLAINTS[complaint_key])
    s = rng.choice(_SUBJECTIVE).format(visit=rng.choice(_VISITS), complaint=complaint,
                                       complaint_lc=complaint[0].lower() + complaint[1:])
    o = _objective(chart, rng)
    a = rng.choice(_ASSESS[status]) if leak_assessment and rng.random() < 0.5 else rng.choice(_VAGUE_ASSESS)
    p = rng.choice(_PLAN[status])
    return f"S: {s}\nO: {o}\nA: {a}\nP: {p}"
