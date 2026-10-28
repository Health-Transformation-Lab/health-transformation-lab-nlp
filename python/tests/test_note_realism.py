"""Spec 001: realistic diagnosis lines from published patterns.

Sentences below are paraphrased from the patterns reported for real UTHealth
dental notes (arXiv 2311.10809 Table I; arXiv 2407.21050 Discussion), not copied.
"""

import random
from collections import Counter

import pytest

from health_transformation_lab_nlp.labels import PerioChart, Status
from health_transformation_lab_nlp.note_reader import read_extent, read_grade, read_stated_dx

CASES = [
    # text, status, grade, extent
    ("d: generalized stage iii grade c periodontitis.", "periodontitis_stage_3", "C", "generalized"),
    ("d- localized periodontitis, stage 2 grade b.", "periodontitis_stage_2", "B", "localized"),
    ("d: tentative diagnosis is stage 3 grade a generalized", "periodontitis_stage_3", "A", "generalized"),
    ("d- stage iv grade c periodontitis.", "periodontitis_stage_4", "C", None),
    ("d : generalized plaque induced gingivitis", "gingivitis", "NA", "NA"),
    ("Diagnosis: Localized Periodontitis Stage I Grade A with Generalized Recession.",
     "periodontitis_stage_1", "A", "localized"),
    ("Generalized Stage 3 Grade B", "periodontitis_stage_3", "B", "generalized"),
    ("d: stage ii grade ii periodontitis, localzied", "periodontitis_stage_2", "B", "localized"),
    ("dx: generalzied periodontitis stage 2 grade b.", "periodontitis_stage_2", "B", "generalized"),
    ("d: periodontal health on intact periodontium", "healthy", "NA", "NA"),
    ("D: gingival health, reduced periodontium not present", "healthy", "NA", "NA"),
]


@pytest.mark.parametrize("text,status,grade,extent", CASES)
def test_reader_handles_published_forms(text, status, grade, extent):
    assert read_stated_dx(text) == status
    assert read_grade(text) == grade
    if extent is not None:
        assert read_extent(text) == extent


def _ehr_notes(n=1000, seed=3):
    import datetime as dt

    from health_transformation_lab_nlp.clinical_notes import render_clinical_note
    from health_transformation_lab_nlp.labels import extent_of, grade_of, label_chart
    from health_transformation_lab_nlp.phi import fake_person, fake_provider
    from health_transformation_lab_nlp.synthetic import draw_chart, draw_pct_teeth_involved, draw_risk
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        chart = draw_chart(rng.randint(25, 80), rng)
        status = label_chart(chart)
        grade = grade_of(status, chart.rbl_pct, 50)
        extent = extent_of(status, draw_pct_teeth_involved(chart, rng))
        text, _, meta = render_clinical_note(chart, status, grade, extent, draw_risk(rng),
                                             fake_person(rng, dt.date(1970, 1, 1)), fake_provider(rng),
                                             dt.date(2026, 3, 1), rng, style="ehr")
        out.append((text, meta, status, grade, extent))
    return out


def test_every_catalogue_pattern_appears():
    from health_transformation_lab_nlp.dx_patterns import PATTERNS
    seen = Counter(m["dx_pattern"] for _, m, *_ in _ehr_notes())
    missing = [p.id for p in PATTERNS if seen[p.id] == 0]
    assert not missing, missing


def test_diagnosis_presence_rate():
    notes = _ehr_notes(2000)
    none = sum(m["dx_pattern"] == "none" for _, m, *_ in notes) / len(notes)
    assert 0.005 <= none <= 0.03


def test_reader_recovers_stated_status_on_ehr_notes():
    notes = [(t, m) for t, m, *_ in _ehr_notes() if m["dx_pattern"] != "none"]
    hits = sum(read_stated_dx(t) == m["stated_status"] for t, m in notes)
    assert hits / len(notes) >= 0.99


def test_extent_trap_reads_localized():
    notes = [(t, m) for t, m, *_ in _ehr_notes(3000) if m["dx_pattern"] == "extent_then_trap"]
    assert notes, "trap pattern never generated"
    assert all(read_extent(t) == "localized" for t, _ in notes)


def test_unused_chart_is_valid():
    PerioChart(2, 5, 0, 0)
    assert Status.HEALTHY.value == "healthy"
