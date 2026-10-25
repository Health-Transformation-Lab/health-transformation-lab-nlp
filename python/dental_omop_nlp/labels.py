"""Periodontal status from a perio chart.

Simplified from the 2017 AAP/EFP classification (Tonetti, Greenwell & Kornman
2018). Staging uses the severity axis only: interdental clinical attachment
loss (CAL), radiographic bone loss (RBL) and teeth lost to periodontitis.
Grade (rate of progression) and extent are not modeled.

    healthy          BOP < 10% of sites, no attachment loss
    gingivitis       BOP >= 10%, CAL < 1 mm (no attachment loss)
    stage I          CAL 1-2 mm,  RBL < 15%,  no perio tooth loss
    stage II         CAL 3-4 mm,  RBL 15-33%, no perio tooth loss
    stage III        CAL >= 5 mm, RBL > 33%,  <= 4 teeth lost
    stage IV         as III and >= 5 teeth lost to periodontitis

Where the three severity signals disagree the worst one decides, which is
also how the classification reads clinically ("the stage is determined by
the most severe site").

This is the GROUND TRUTH for the synthetic data: the chart produces both the
label (here) and the note (notes.py), so the benchmark asks whether a model
can recover from the text what the chart already knew. A clinician-labeled
protocol replaces this file when real notes arrive.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Status(str, Enum):
    HEALTHY = "healthy"
    GINGIVITIS = "gingivitis"
    P1 = "periodontitis_stage_1"
    P2 = "periodontitis_stage_2"
    P3 = "periodontitis_stage_3"
    P4 = "periodontitis_stage_4"

    @property
    def is_periodontitis(self) -> bool:
        return self.value.startswith("periodontitis")


LABELS: list[str] = [s.value for s in Status]


@dataclass(frozen=True)
class PerioChart:
    max_probing_depth_mm: float
    bop_pct: float
    max_cal_mm: float
    rbl_pct: float
    teeth_lost_perio: int = 0

    def __post_init__(self) -> None:
        if not 0 <= self.bop_pct <= 100:
            raise ValueError(f"bop_pct out of range: {self.bop_pct}")
        if not 0 <= self.rbl_pct <= 100:
            raise ValueError(f"rbl_pct out of range: {self.rbl_pct}")
        if self.max_cal_mm < 0 or self.max_probing_depth_mm < 0 or self.teeth_lost_perio < 0:
            raise ValueError("negative chart value")


def label_chart(chart: PerioChart) -> Status:
    """Map one perio chart to a status. Pure function; see module docstring."""
    cal, rbl, lost = chart.max_cal_mm, chart.rbl_pct, chart.teeth_lost_perio

    if cal < 1.0 and rbl < 15.0 and lost == 0:
        return Status.GINGIVITIS if chart.bop_pct >= 10.0 else Status.HEALTHY

    # Periodontitis. Severity by the worst of the three signals.
    stage_by_cal = 1 if cal <= 2.0 else 2 if cal <= 4.0 else 3
    stage_by_rbl = 1 if rbl < 15.0 else 2 if rbl <= 33.0 else 3
    stage = max(stage_by_cal, stage_by_rbl)
    if lost >= 5:
        stage = 4
    elif lost > 0 and stage < 3:
        # Any perio tooth loss implies stage III or worse.
        stage = 3
    return {1: Status.P1, 2: Status.P2, 3: Status.P3, 4: Status.P4}[stage]


def grade_of(status: Status, rbl_pct: float, age: int, cigarettes_per_day: int = 0,
             hba1c: float | None = None) -> str:
    """2017 grade from indirect evidence (% bone loss / age) with risk-factor
    modifiers. 'NA' when not periodontitis.

        A  %RBL/age < 0.25, non-smoker, no diabetes
        B  0.25-1.0, or smoker < 10 cig/day, or HbA1c < 7.0 with diabetes
        C  > 1.0, or smoker >= 10 cig/day, or HbA1c >= 7.0
    """
    if not status.is_periodontitis:
        return "NA"
    ratio = rbl_pct / max(age, 1)
    grade = "A" if ratio < 0.25 else "B" if ratio <= 1.0 else "C"
    if cigarettes_per_day >= 10 or (hba1c is not None and hba1c >= 7.0):
        return "C"
    if (cigarettes_per_day > 0 or hba1c is not None) and grade == "A":
        return "B"
    return grade


def extent_of(status: Status, pct_teeth_involved: float) -> str:
    """Localized < 30% of teeth involved, generalized >= 30%. 'NA' when not periodontitis."""
    if not status.is_periodontitis:
        return "NA"
    return "generalized" if pct_teeth_involved >= 30 else "localized"


def label_row(row) -> str:
    """pandas apply helper: row with the perio_chart view's column names."""
    chart = PerioChart(
        max_probing_depth_mm=float(row["max_probing_depth_mm"]),
        bop_pct=float(row["bop_pct"]),
        max_cal_mm=float(row["max_cal_mm"]),
        rbl_pct=float(row["rbl_pct"]),
        teeth_lost_perio=int(row.get("teeth_lost_perio", 0) or 0),
    )
    return label_chart(chart).value
