import json

import pandas as pd

from health_transformation_lab_nlp.deid import deidentify, leak_check, score_deid
from health_transformation_lab_nlp.labels import Status, extent_of, grade_of
from health_transformation_lab_nlp.labelstudio import parse_export
from health_transformation_lab_nlp.note_reader import read_note, read_stated_dx
from health_transformation_lab_nlp.reliability import consensus, fleiss_kappa, weighted_kappa
from health_transformation_lab_nlp.sources import read_proc_codes, read_proc_dx
from health_transformation_lab_nlp.study import generate_visits


def test_deid_removes_every_injected_phi_value():
    df = generate_visits(150, seed=3)
    for r in df.itertuples():
        phi = json.loads(r.phi_spans)
        text, found = deidentify(r.note_raw)
        assert leak_check(text, phi) == [], (r.visit_id, leak_check(text, phi))
        s = score_deid(r.note_raw, phi, found)
        assert s["phi_chars_removed"] == s["phi_chars"]


def test_deid_keeps_dental_abbreviations():
    note = "O: #3 MB 6mm, #14 DL 5mm; BOP 30%; FMX: moderate horizontal bone loss. P: SRP UR/LR."
    text, _ = deidentify(note)
    assert text == note


def test_note_reader_schemes():
    assert read_stated_dx("Dx: Generalized periodontitis Stage III Grade B.") == "periodontitis_stage_3"
    assert read_stated_dx("A: Gen. perio St II Gr B.") == "periodontitis_stage_2"
    assert read_stated_dx("Impression: Localized moderate chronic periodontitis.") == "periodontitis_stage_2"
    assert read_stated_dx("A: AAP Case Type IV. 6 teeth lost to periodontal disease") == "periodontitis_stage_4"
    assert read_stated_dx("Dx: Dental biofilm-induced gingivitis, localized.") == "gingivitis"
    assert read_stated_dx("Dx: Clinical gingival health on an intact periodontium.") == "healthy"
    assert read_stated_dx("A: See perio chart.") is None


def test_note_reader_ignores_copy_forward():
    note = ("Dx: Generalized periodontitis Stage III Grade B.\n\n-- copied from visit [DATE] --\n"
            "Dx at that visit: Stage II periodontitis.")
    assert read_note(note) == "periodontitis_stage_3"


def test_grade_and_extent():
    assert grade_of(Status.P2, 20, 50) == "B"
    assert grade_of(Status.P2, 10, 60) == "A"
    assert grade_of(Status.P2, 10, 60, cigarettes_per_day=15) == "C"
    assert grade_of(Status.GINGIVITIS, 0, 40) == "NA"
    assert extent_of(Status.P3, 45) == "generalized" and extent_of(Status.P3, 10) == "localized"


def test_source_readers():
    assert read_proc_codes("D0180 D4341 D4260") == "periodontitis_stage_3"
    assert read_proc_codes("D0180 D1110") == "unknown"
    assert read_proc_dx("K05.323") == "periodontitis_stage_3"
    assert read_proc_dx("K05.10") == "gingivitis"


def test_reliability_metrics():
    wide = pd.DataFrame({"r1": ["a", "a", "b", "b"], "r2": ["a", "a", "b", "b"], "r3": ["a", "a", "b", "b"]})
    assert abs(fleiss_kappa(wide) - 1.0) < 1e-12
    s = pd.Series(["healthy", "gingivitis", "periodontitis_stage_1"])
    assert abs(weighted_kappa(s, s) - 1.0) < 1e-12
    tie = pd.DataFrame({"r1": ["a"], "r2": ["b"]})
    assert consensus(tie).iloc[0] == "no_consensus"


def test_parse_label_studio_export():
    export = [{"data": {"visit_id": 9}, "annotations": [{
        "completed_by": {"id": 1, "email": "a@x.org"}, "was_cancelled": False, "lead_time": 12.5,
        "result": [
            {"from_name": "status", "type": "choices", "value": {"choices": ["periodontitis_stage_2"]}},
            {"from_name": "grade", "type": "choices", "value": {"choices": ["B"]}},
            {"from_name": "confidence", "type": "rating", "value": {"rating": 4}},
            {"from_name": "evidence", "type": "labels",
             "value": {"start": 0, "end": 7, "text": "BOP 30%", "labels": ["BOP"]}}]}]}]
    labels, spans = parse_export(export)
    assert labels.iloc[0]["status"] == "periodontitis_stage_2" and labels.iloc[0]["confidence"] == 4
    assert spans.iloc[0]["label"] == "BOP"
