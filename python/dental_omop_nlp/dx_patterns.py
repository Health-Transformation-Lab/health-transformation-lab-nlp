"""Catalogue of how clinicians write the periodontal diagnosis line (spec 001).

Each pattern re-composes a form reported for real dental notes. Nothing is
copied from a paper; the parts (prefix, stage numeral, grade, extent, hedge)
are recombined per note. Sources:

  [UTH-RE]  Chuang et al., "Extracting periodontitis diagnosis in clinical notes
            with RoBERTa and regular expression", arXiv 2311.10809 (UTHealth
            Houston, 8,125 notes, 2021). Table I forms; 98.7% of records carry a
            diagnosis section; typo variants of generalized/localized.
  [UTH-AI]  Chuang et al., "Artificial Intelligence in Extracting Diagnostic
            Data from Dental Records", arXiv 2407.21050. Extent placed before
            stage/grade and a second extent word for a different finding
            ("... with generalized recession") caused extent errors; diagnosis
            starting a sentence with no "D"/"Diagnosis" prefix.
  [AAP17]   2017 AAP/EFP classification wording for health and gingivitis.
  [AAP99]   1999 AAP classification terms (chronic periodontitis, slight/moderate/
            severe) still used in older or copied-forward notes.
  [COMMON]  common charting abbreviations; not from a published corpus.

Weights are a starting guess. Profile a real de-identified sample and retune
(specs/001 task T016).
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass

from .labels import Status
from .telemetry import traced

ROMAN = {1: "i", 2: "ii", 3: "iii", 4: "iv"}
GRADE_ROMAN = {"A": "i", "B": "ii", "C": "iii"}
MISSPELL = {"generalized": ["generalzied", "generlized", "generalised"],
            "localized": ["localzied", "locallized", "localised"]}
NONE_RATE = 0.015   # [UTH-RE]: 98.7% of records had a diagnosis section


@dataclass(frozen=True)
class Ctx:
    status: Status
    stage: int            # 0 for health / gingivitis
    grade: str            # A/B/C or NA
    extent: str           # localized / generalized / NA


@dataclass(frozen=True)
class Pattern:
    id: str
    source: str
    weight: float
    applies: Callable[[Ctx], bool]
    render: Callable[[Ctx, random.Random], str]


def _stage(n: int, rng: random.Random, upper: bool = False) -> str:
    s = ROMAN[n] if rng.random() < 0.6 else str(n)
    return s.upper() if upper else s


def _grade(g: str, rng: random.Random, upper: bool = False) -> str:
    s = g if upper else g.lower()
    return s + ("." if rng.random() < 0.3 else "")


def _perio(c: Ctx) -> bool:
    return c.status.is_periodontitis


def _perio_ext(c: Ctx) -> bool:
    return c.status.is_periodontitis and c.extent in ("localized", "generalized")


def _prefix(rng: random.Random) -> str:
    return rng.choice(["d: ", "d- ", "d : ", "d:", "diagnosis: "])


PATTERNS: list[Pattern] = [
    # ---- periodontitis, published forms [UTH-RE] Table I
    Pattern("d_ext_stage_grade_label", "UTH-RE", 3.0, _perio_ext,
            lambda c, r: f"{_prefix(r)}{c.extent} stage {_stage(c.stage, r)} grade {_grade(c.grade, r)} periodontitis."),
    Pattern("d_ext_label_stage_grade", "UTH-RE", 2.5, _perio_ext,
            lambda c, r: f"{_prefix(r)}{c.extent} periodontitis, stage {_stage(c.stage, r)} grade {_grade(c.grade, r)}"),
    Pattern("d_hedge_stage_grade_ext", "UTH-RE", 1.0, _perio_ext,
            lambda c, r: f"{_prefix(r)}tentative diagnosis is stage {_stage(c.stage, r)} grade {c.grade.lower()} {c.extent}"),
    Pattern("d_stage_grade_label", "UTH-RE", 1.5, _perio,
            lambda c, r: f"{_prefix(r)}stage {_stage(c.stage, r)} grade {_grade(c.grade, r)} periodontitis."),
    Pattern("misspelled_extent", "UTH-RE", 0.8, _perio_ext,
            lambda c, r: f"{_prefix(r)}{r.choice(MISSPELL[c.extent])} periodontitis stage {_stage(c.stage, r)} grade {_grade(c.grade, r)}"),
    Pattern("grade_roman", "UTH-RE", 0.6, _perio,
            lambda c, r: f"{_prefix(r)}stage {_stage(c.stage, r)} grade {GRADE_ROMAN[c.grade]} periodontitis"
                         + (f", {c.extent}" if c.extent in ("localized", "generalized") else "")),
    # ---- periodontitis, published forms [UTH-AI]
    Pattern("title_case_diagnosis", "UTH-AI", 1.5, _perio_ext,
            lambda c, r: f"Diagnosis: {c.extent.title()} Periodontitis Stage {_stage(c.stage, r, True)} Grade {c.grade}"),
    Pattern("extent_then_trap", "UTH-AI", 0.8, lambda c: _perio(c) and c.extent == "localized",
            lambda c, r: f"Diagnosis: Localized Periodontitis Stage {_stage(c.stage, r, True)} Grade {c.grade} "
                         f"with Generalized {r.choice(['Recession', 'Gingival Inflammation', 'Plaque'])}."),
    Pattern("bare_sentence_start", "UTH-AI", 0.8, _perio_ext,
            lambda c, r: f"{c.extent.title()} Stage {_stage(c.stage, r, True)} Grade {c.grade}"),
    # ---- older / abbreviated
    Pattern("pre2017_severity", "AAP99", 0.6, _perio_ext,
            lambda c, r: f"{_prefix(r)}{c.extent} {['', 'slight', 'moderate', 'severe', 'severe'][c.stage]} chronic periodontitis"
                         + (f"; {r.randint(5, 9)} teeth lost to periodontal disease" if c.stage == 4 else "")),
    Pattern("dx_abbreviated", "COMMON", 0.6, _perio_ext,
            lambda c, r: f"Dx: {c.extent[:3].title()}. perio St {_stage(c.stage, r, True)} Gr {c.grade}"),
    # ---- gingivitis [UTH-RE] Table I #5, [AAP17]
    Pattern("gingivitis_plaque_induced", "UTH-RE", 2.0, lambda c: c.status is Status.GINGIVITIS,
            lambda c, r: f"{_prefix(r)}{r.choice(['generalized', 'localized'])} plaque induced gingivitis"),
    Pattern("gingivitis_2017", "AAP17", 1.0, lambda c: c.status is Status.GINGIVITIS,
            lambda c, r: "Diagnosis: Dental biofilm-induced gingivitis on an intact periodontium"),
    # ---- health [AAP17]
    Pattern("health_lower", "AAP17", 2.0, lambda c: c.status is Status.HEALTHY,
            lambda c, r: f"{_prefix(r)}{r.choice(['periodontal health', 'clinical gingival health'])} on intact periodontium"),
    Pattern("health_title", "AAP17", 1.0, lambda c: c.status is Status.HEALTHY,
            lambda c, r: "Diagnosis: Clinical Gingival Health on an Intact Periodontium"),
]

BY_ID = {p.id: p for p in PATTERNS}


@traced
def render_dx(status: Status, grade: str, extent: str, rng: random.Random,
              none_rate: float = NONE_RATE) -> tuple[str, str]:
    """Returns (diagnosis line, pattern id). Pattern 'none' = no diagnosis line."""
    if rng.random() < none_rate:
        return "", "none"
    stage = int(status.value[-1]) if status.is_periodontitis else 0
    ctx = Ctx(status, stage, grade if status.is_periodontitis else "NA",
              extent if status.is_periodontitis else "NA")
    pool = [p for p in PATTERNS if p.applies(ctx)]
    p = rng.choices(pool, weights=[p.weight for p in pool])[0]
    line = p.render(ctx, rng)
    if p.source == "UTH-RE" and rng.random() < 0.15:   # some sites write in caps
        line = line.upper()
    return line, p.id
