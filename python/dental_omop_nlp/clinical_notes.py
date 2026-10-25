"""Clinically styled synthetic notes, with fake PHI, for the de-id → Label Studio → test path.

`notes.py` writes short templated SOAP notes whose numbers make the task easy.
This module writes notes that look more like what a dental EHR exports:

- a header and in-body mentions with fake PHI (name, DOB, MRN, dates, phone,
  provider, practice, address), every span recorded for de-id scoring
- three body styles: SOAP, narrative, chart summary
- findings as numbers OR descriptors ("heavy BOP", "moderate horizontal bone
  loss"), tooth-level sites (#3 MB 6mm), recession as a distractor
- the clinician's diagnosis in one of four forms, or absent:
    2017 full     "Generalized periodontitis Stage III Grade B"
    2017 short    "Gen perio St III Gr B"
    pre-2017      "moderate chronic periodontitis" / "AAP Case Type III"
    none          diagnosis must be inferred from the findings
  (Patel 2020 found charting-derived and clinician-recorded diagnoses agreed
  only 47% of the time in a real EDR, and clinicians still mix schemes, so the
  annotation protocol has to say how to read each.)
- copy-forward of a previous visit's diagnosis that disagrees with today's

The chart is still the generator's truth; the annotated label is the gold.
How often the two disagree is itself a result worth reporting.
"""

from __future__ import annotations

import datetime as dt
import random

from .labels import PerioChart, Status
from .phi import Builder, Person, Provider, fmt_date
from .dx_patterns import render_dx
from .synthetic import RiskFactors

# Share of each note style. "ehr" follows published real-note patterns (spec 001)
# and is the majority; the older styles stay for variety.
STYLE_WEIGHTS = {"ehr": 0.6, "soap": 0.15, "narrative": 0.1, "chart_summary": 0.15}

_STAGE_ROMAN = {Status.P1: "I", Status.P2: "II", Status.P3: "III", Status.P4: "IV"}
_OLD_SEVERITY = {Status.P1: "slight", Status.P2: "moderate", Status.P3: "severe", Status.P4: "severe"}
_OLD_CASE_TYPE = {Status.GINGIVITIS: "I", Status.P1: "II", Status.P2: "III", Status.P3: "IV", Status.P4: "IV"}
_TEETH = list(range(1, 33))
_SURF = ["MB", "DB", "ML", "DL", "B", "L", "M", "D"]


def _sites(rng: random.Random, n: int, lo: int, hi: int) -> str:
    teeth = sorted(rng.sample([t for t in _TEETH if t not in (1, 16, 17, 32)], n))
    return ", ".join(f"#{t} {rng.choice(_SURF)} {rng.randint(lo, hi)}mm" for t in teeth)


def _pd(chart: PerioChart, rng: random.Random, numeric: bool) -> str:
    pd = round(chart.max_probing_depth_mm)
    if pd <= 3:
        return rng.choice(["PD 1-3mm WNL", "probing depths within normal limits", "shallow sulci throughout"]) \
            if numeric or rng.random() < 0.5 else "no pocketing"
    if not numeric:
        return {4: "mild pocketing", 5: "moderate pocketing posterior"}.get(pd, "deep pockets posterior sextants")
    return rng.choice([f"generalized {max(pd - 2, 3)}-{pd - 1}mm pockets, localized {_sites(rng, rng.randint(2, 4), pd - 1, pd)}",
                       f"PD up to {pd}mm ({_sites(rng, 2, pd - 1, pd)})", f"max PD {pd} mm"])


def _bop(chart: PerioChart, rng: random.Random, numeric: bool) -> str:
    b = chart.bop_pct
    if numeric:
        return rng.choice([f"BOP {b:.0f}%", f"bleeding on probing {b:.0f}% of sites"]) if b >= 10 else \
            rng.choice(["no BOP", "BOP <10%", "minimal BOP"])
    return "heavy BOP" if b >= 40 else "BOP generalized" if b >= 20 else "localized BOP" if b >= 10 else "no bleeding on probing"


def _cal(chart: PerioChart, rng: random.Random, numeric: bool) -> str:
    c = round(chart.max_cal_mm)
    recession = f"recession {rng.randint(1, 3)}mm #{rng.choice([6, 11, 22, 27])}" if rng.random() < 0.3 else ""
    if c < 1:
        core = rng.choice(["no attachment loss", "CAL 0", ""])
    elif numeric:
        core = rng.choice([f"CAL up to {c}mm", f"attachment loss {max(c - 1, 1)}-{c} mm", f"max CAL {c}mm interproximal"])
    else:
        core = "slight attachment loss" if c <= 2 else "moderate attachment loss" if c <= 4 else "severe attachment loss"
    return "; ".join(x for x in (core, recession) if x)


def _rbl(chart: PerioChart, rng: random.Random, numeric: bool) -> str:
    r = chart.rbl_pct
    film = rng.choice(["FMX", "BWX", "PAN", "radiographs"])
    if r < 5:
        return f"{film}: crestal bone WNL" if rng.random() < 0.7 else ""
    word = "mild" if r < 15 else "moderate" if r <= 33 else "severe"
    third = "coronal third" if r < 15 else "middle third" if r <= 33 else "apical third"
    if numeric:
        return f"{film}: {word} horizontal bone loss ~{r:.0f}%" if rng.random() < 0.6 else f"{film}: bone loss to {third} (~{r:.0f}%)"
    return f"{film}: {word} horizontal bone loss" + (f", vertical defect #{rng.choice([3, 14, 19, 30])}" if r > 33 and rng.random() < 0.5 else "")


def _lost(chart: PerioChart, rng: random.Random) -> str:
    n = chart.teeth_lost_perio
    if not n:
        return ""
    teeth = sorted(rng.sample([2, 3, 14, 15, 18, 19, 30, 31, 8, 9, 24, 25], min(n, 12)))
    return rng.choice([f"missing {', '.join('#%d' % t for t in teeth)} (hx perio ext)",
                       f"{n} teeth lost to periodontal disease", f"hx extraction of {n} teeth d/t perio"])


def _history(risk: RiskFactors, rng: random.Random) -> str:
    s = (f"smoker ~{risk.cigarettes_per_day} cig/day" if risk.cigarettes_per_day else
         rng.choice(["non-smoker", "never smoker", "former smoker, quit 2015"]))
    d = (f"T2DM, last A1c {risk.hba1c}" if risk.hba1c and risk.hba1c >= 6.5 else
         f"pre-diabetic A1c {risk.hba1c}" if risk.hba1c else rng.choice(["no sig med hx", "HTN controlled", "NKDA"]))
    return f"Med hx: {d}; {s}."


def _dx(status: Status, grade: str, extent: str, scheme: str, rng: random.Random) -> str:
    if scheme == "none":
        return rng.choice(["See perio chart.", "Findings reviewed with pt.", ""])
    if status is Status.HEALTHY:
        return {"2017": "Clinical gingival health on an intact periodontium.", "short": "Perio health.",
                "old": "Periodontium WNL."}[scheme]
    if status is Status.GINGIVITIS:
        return {"2017": f"Dental biofilm-induced gingivitis, {rng.choice(['generalized', 'localized'])}.",
                "short": "Gingivitis.", "old": rng.choice(["Plaque-induced gingivitis.", "AAP Case Type I."])}[scheme]
    st = _STAGE_ROMAN[status]
    ext = {"generalized": "Generalized", "localized": "Localized"}[extent]
    if scheme == "2017":
        return f"{ext} periodontitis Stage {st} Grade {grade}."
    if scheme == "short":
        return rng.choice([f"{ext[:3]}. perio St {st} Gr {grade}", f"Perio {st}{grade}, {extent[:3]}", f"Stage {st}/Grade {grade} perio"]) + "."
    return rng.choice([f"{ext} {_OLD_SEVERITY[status]} chronic periodontitis.", f"AAP Case Type {_OLD_CASE_TYPE[status]}."])


def _ehr_body(b: Builder, chart: PerioChart, status: Status, stated: Status, findings: list[str], dx: str,
              hx: str, plan: str, numeric: bool, rng: random.Random) -> None:
    """A dental EHR progress note: terse, lowercase-heavy, section labels, common
    abbreviations (CC, MHx, BP, OHI, NV, 4BWX, FMX, pt). Body conventions are
    common charting practice, not from a published corpus; clinician review is
    specs/001 task T012."""
    cc = rng.choice(['pt here for perio eval', 'pt presents for recall', 'pt here for comp exam',
                     '"my gums bleed when i brush"', 'pt reports sensitivity LR', 'no c/o'])
    b.text(f"CC: {cc}\n")
    b.text(f"MHx reviewed, no changes. {hx} BP {rng.randint(108, 152)}/{rng.randint(64, 94)}.\n")
    rads = rng.choice(["4BWX taken", "FMX reviewed", "2BWX + 2PA taken", "PAN reviewed", "no rads today"])
    perio = [f for f in findings if not f.startswith(("FMX", "BWX", "PAN", "radiographs"))]
    bone = [f for f in findings if f.startswith(("FMX", "BWX", "PAN", "radiographs"))]
    b.text("perio charting done: " + ", ".join(perio) + ".\n" if perio else "perio charting done.\n")
    b.text(f"rads: {rads}" + (f"; {bone[0].split(': ', 1)[-1]}" if bone else "") + ".\n")
    if dx:
        b.text(dx.rstrip() + "\n")
    tx = plan.lower() if rng.random() < 0.5 else plan
    b.text(f"tx: {tx} OHI given{rng.choice(['', ', pt verbalized understanding', ', reviewed flossing'])}. "
           f"pt tolerated {rng.choice(['well', 'tx well', 'procedure well'])}.\n")
    nv = {Status.HEALTHY: ["recall 6 mo", "prophy 6 mo"], Status.GINGIVITIS: ["recall 6 mo", "re-eval gingiva 6 wk"],
          Status.P1: ["srp ur/lr", "re-eval 6 wk"], Status.P2: ["srp ul/ll", "srp 4 quads"],
          Status.P3: ["srp ur/lr", "perio consult"], Status.P4: ["perio consult", "ext consult"]}[stated]
    b.text(f"NV: {rng.choice(nv)}\n")


_PLAN = {
    Status.HEALTHY: ["Adult prophy. RTC 6 mo.", "Prophy, OHI. Recall 6 mo."],
    Status.GINGIVITIS: ["Prophy + OHI, re-eval gingiva next recall.", "Prophy, flossing instruction. 6 mo recall."],
    Status.P1: ["SRP UR/LR, re-eval 6 wk.", "Localized SRP, perio maint q4mo."],
    Status.P2: ["SRP 4 quads, re-eval 4-6 wk.", "4 quad SRP then perio maint q3mo."],
    Status.P3: ["FM SRP, refer to periodontist.", "SRP 4 quads; perio consult for surgical eval."],
    Status.P4: ["Referral to periodontist for comprehensive tx plan.", "Perio referral; prosthetic consult for edentulous areas."],
}


def render_clinical_note(chart: PerioChart, status: Status, grade: str, extent: str, risk: RiskFactors,
                         patient: Person, provider: Provider, visit_date: dt.date,
                         rng: random.Random, prev_date: dt.date | None = None,
                         stated_status: Status | None = None,
                         style: str | None = None) -> tuple[str, list[dict], dict]:
    """Returns (text, phi_spans, meta).

    `status` is what the chart supports; `stated_status` is what the clinician
    wrote (defaults to `status`). They differ in a share of visits, as in real
    EDRs, and the findings in the note always follow the chart.
    """
    stated = stated_status or status
    if stated.is_periodontitis and not status.is_periodontitis:
        grade, extent = "B", "localized"   # clinician staged something the chart doesn't support
    b = Builder()
    style = style or rng.choices(list(STYLE_WEIGHTS), weights=list(STYLE_WEIGHTS.values()))[0]
    numeric = rng.random() < 0.55
    scheme = rng.choices(["2017", "short", "old", "none"], weights=[0.35, 0.2, 0.2, 0.25])[0]

    # ---- header
    if rng.random() < 0.5:
        b.text("Patient: ").phi(f"{patient.last}, {patient.first}", "NAME").text("   DOB: ") \
         .phi(fmt_date(patient.dob, rng), "DATE").text("   MRN: ").phi(patient.mrn, "ID").text("\n")
    else:
        b.text("Pt ").phi(f"{patient.first} {patient.last}", "NAME").text(" (").phi(patient.mrn, "ID").text(")\n")
    b.text("DOS: ").phi(fmt_date(visit_date, rng), "DATE").text("  Provider: Dr. ") \
     .phi(provider.last, "NAME").text("\n\n")

    findings = [x for x in (_pd(chart, rng, numeric), _bop(chart, rng, numeric), _cal(chart, rng, numeric),
                            _rbl(chart, rng, numeric), _lost(chart, rng)) if x]
    rng.shuffle(findings)
    if style == "ehr":   # diagnosis line from the published pattern catalogue (spec 001)
        dx, dx_pattern = render_dx(stated, grade, extent, rng)
        scheme = "catalogue"
    else:
        dx = _dx(stated, grade if stated.is_periodontitis else 'NA', extent, scheme, rng)
        dx_pattern = f"legacy_{scheme}" if dx and scheme != "none" else "none"
    hx = _history(risk, rng)
    plan = rng.choice(_PLAN[stated])

    # ---- body
    if style == "ehr":
        _ehr_body(b, chart, status, stated, findings, dx, hx, plan, numeric, rng)
    elif style == "soap":
        b.text(f"S: Pt presents for {rng.choice(['perio eval', 'recall', 'comprehensive exam', 'perio maint'])}. {hx}\n")
        b.text("O: " + "; ".join(findings) + ".\n")
        b.text(f"A: {dx}\n" if dx else "A: \n")
        b.text(f"P: {plan}")
    elif style == "narrative":
        b.text(f"{rng.choice(['Pt', 'Patient'])} seen for {rng.choice(['periodontal evaluation', 'recall exam'])}. {hx} ")
        b.text("Exam: " + ", ".join(findings) + ". ")
        if dx:
            b.text(f"Impression: {dx} ")
        b.text(plan)
    else:
        b.text("PERIODONTAL CHARTING COMPLETED\n" + "\n".join(f"- {f}" for f in findings) + "\n")
        b.text(f"Dx: {dx}\n" if dx else "")
        b.text(f"{hx}\nTx plan: {plan}")

    # ---- in-body PHI and copy-forward, sometimes
    if status in (Status.P3, Status.P4) and rng.random() < 0.5:
        b.text(" Referred to Dr. ").phi(f"{provider.first} {provider.last}", "NAME").text(" at ") \
         .phi(provider.practice, "LOCATION").text(", ph ").phi(patient.phone if rng.random() < 0.3 else
                                                               f"({rng.randint(201, 989)}) 555-{rng.randint(1000, 9999)}", "PHONE").text(".")
    if rng.random() < 0.25:
        b.text(" Next appt ").phi(fmt_date(visit_date + dt.timedelta(days=rng.choice([42, 90, 120, 182])), rng), "DATE").text(".")
    if rng.random() < 0.1:
        b.text(" Pt moved; new address ").phi(f"{patient.address}, {patient.city}", "LOCATION").text(".")
    copy_forward = bool(prev_date) and status.is_periodontitis and rng.random() < 0.15
    if copy_forward:
        prior = {Status.P2: "Stage I periodontitis", Status.P3: "Stage II periodontitis",
                 Status.P4: "Stage III periodontitis"}.get(status, "gingivitis")
        b.text("\n\n-- copied from visit ").phi(fmt_date(prev_date, rng), "DATE") \
         .text(f" --\nDx at that visit: {prior}. Pt declined SRP at that time.")

    text, spans = b.build()
    return text, spans, {"style": style, "numeric": numeric, "dx_scheme": scheme, "copy_forward": copy_forward,
                         "stated_status": stated.value, "dx_pattern": dx_pattern}
