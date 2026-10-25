import random

import pytest

from dental_omop_nlp.labels import PerioChart, Status, label_chart
from dental_omop_nlp.notes import render_soap_note
from dental_omop_nlp.rungs import rules_predict
from dental_omop_nlp.synthetic import draw_chart


@pytest.mark.parametrize("chart,expected", [
    (PerioChart(2, 5, 0, 0), Status.HEALTHY),
    (PerioChart(3, 25, 0, 5), Status.GINGIVITIS),
    (PerioChart(4, 20, 2, 10), Status.P1),
    (PerioChart(5, 30, 3, 10), Status.P2),
    (PerioChart(5, 30, 2, 20), Status.P2),     # RBL is worse than CAL -> RBL decides
    (PerioChart(7, 50, 6, 40, 2), Status.P3),
    (PerioChart(4, 20, 2, 10, 1), Status.P3),  # any perio tooth loss -> >= III
    (PerioChart(8, 60, 7, 60, 6), Status.P4),
])
def test_label_chart(chart, expected):
    assert label_chart(chart) is expected


def test_chart_validation():
    with pytest.raises(ValueError):
        PerioChart(3, 120, 0, 0)


def test_note_is_deterministic():
    c = PerioChart(5, 30, 3, 20)
    assert render_soap_note(c, seed=7) == render_soap_note(c, seed=7)


def test_no_leak_never_states_status():
    from dental_omop_nlp.notes import _ASSESS
    stated = {p for phrases in _ASSESS.values() for p in phrases}
    rng = random.Random(0)
    for i in range(300):
        note = render_soap_note(draw_chart(55, rng), seed=i, leak_assessment=False)
        a_line = [ln for ln in note.splitlines() if ln.startswith("A:")][0]
        assert a_line[3:] not in stated


def test_rules_handle_negated_bop():
    note = "S: x\nO: PD max 2mm; no BOP noted; no bone loss on BWX.\nA: See perio chart.\nP: Prophy."
    assert rules_predict(note) == "healthy"


def test_rules_agree_with_chart_most_of_the_time():
    # Sanity, not a benchmark: the rules parse what the renderer writes.
    rng = random.Random(1)
    hits = 0
    for i in range(500):
        c = draw_chart(rng.randint(20, 80), rng)
        hits += rules_predict(render_soap_note(c, seed=i)) == label_chart(c).value
    assert hits / 500 > 0.7
