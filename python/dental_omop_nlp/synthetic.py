"""Stand-in perio charts and patient attributes until the custom Synthea perio
module exists.

Synthea's built-in dental module gives people and recall visits but no chart
numerics. Until synthea/modules/dental_periodontal_exam.json is written, this
draws a plausible chart per (person, visit) from a latent severity, nudged by
age, plus the patient factors the 2017 classification uses for grade
(smoking, diabetes) and the extent of involvement.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .labels import PerioChart

# Latent severity mix for US adults, roughly shaped on NHANES 2009-2014
# (about 4 in 10 adults 30+ with some periodontitis, most mild/moderate).
# Plausible, not a prevalence estimate.
_SEVERITY_WEIGHTS = {"healthy": 0.30, "gingivitis": 0.28, "mild": 0.18,
                     "moderate": 0.15, "severe": 0.07, "advanced": 0.02}


@dataclass(frozen=True)
class RiskFactors:
    cigarettes_per_day: int      # 0 = non-smoker
    hba1c: float | None          # None = no diabetes documented


def draw_risk(rng: random.Random) -> RiskFactors:
    smoke = rng.choices([0, rng.randint(1, 9), rng.randint(10, 30)], weights=[0.82, 0.10, 0.08])[0]
    hba1c = rng.choice([round(rng.uniform(5.8, 6.9), 1), round(rng.uniform(7.0, 10.5), 1)]) \
        if rng.random() < 0.12 else None
    return RiskFactors(smoke, hba1c)


def draw_chart(age: int, rng: random.Random) -> PerioChart:
    w = dict(_SEVERITY_WEIGHTS)
    if age >= 50:  # shift mass toward disease with age
        w["healthy"] -= 0.10
        w["moderate"] += 0.06
        w["severe"] += 0.04
    sev = rng.choices(list(w), weights=list(w.values()))[0]
    u = rng.uniform
    if sev == "healthy":
        return PerioChart(u(1, 3), u(0, 9), 0, 0)
    if sev == "gingivitis":
        return PerioChart(u(2, 4), u(10, 45), u(0, 0.9), u(0, 10))
    if sev == "mild":
        return PerioChart(u(3, 4), u(10, 40), u(1, 2), u(0, 14))   # stage I: max PD <= 4 (AAP)
    if sev == "moderate":
        return PerioChart(u(4, 5.5), u(15, 50), u(3, 4), u(15, 33))
    if sev == "severe":
        return PerioChart(u(6, 8), u(25, 70), u(5, 8), u(34, 60), rng.randint(0, 4))
    return PerioChart(u(6, 10), u(30, 80), u(5, 10), u(40, 80), rng.randint(5, 10))


def draw_pct_teeth_involved(chart: PerioChart, rng: random.Random) -> float:
    """Share of teeth with attachment loss; drives extent (localized < 30%)."""
    if chart.max_cal_mm < 1:
        return 0.0
    return round(rng.uniform(5, 29) if rng.random() < 0.5 else rng.uniform(30, 90), 0)
