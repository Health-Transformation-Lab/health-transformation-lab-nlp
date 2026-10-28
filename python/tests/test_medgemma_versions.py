"""MedGemma versions are pinned and recorded, and the 27B option is written down (issue #93)."""

import re

import yaml

from dental_omop_nlp.paths import REPO_ROOT

REG = {m["id"]: m for m in yaml.safe_load((REPO_ROOT / "models.yaml").read_text())["models"]}


def test_every_medgemma_is_pinned_to_a_hugging_face_revision():
    for mid in ("medgemma-1.5-4b-it", "medgemma-4b-it", "medgemma-27b-text-it"):
        assert re.fullmatch(r"[0-9a-f]{40}", REG[mid].get("revision", "")), mid


def test_the_backend_loads_and_reports_the_pinned_revision():
    from dental_omop_nlp.llm_reader import make_backend
    entry = dict(REG["medgemma-4b-it"], gated=False)
    b = make_backend(entry, "hf")
    assert b.revision == entry["revision"]
    src = (REPO_ROOT / "python" / "dental_omop_nlp" / "llm_reader.py").read_text()
    assert src.count("revision=self.revision") >= 2          # processor and weights, both pinned


def test_each_run_records_the_revision_it_used():
    import pandas as pd

    from dental_omop_nlp.llm_reader import LLMReader

    class Fake:
        name, simulated, revision = "hf", False, "abc123"

        def __call__(self, messages, visit_id=None):
            return {"raw": '{"status": "healthy", "quote": "BOP 5%"}', "input_tokens": 1, "output_tokens": 1}

    r = LLMReader("medgemma-4b-it", backend=Fake())
    r.predict(pd.DataFrame({"visit_id": [1], "note_text": ["Gums fine. BOP 5%"]}))
    assert r.details["revision"].tolist() == ["abc123"]


def test_the_27b_option_is_written_down_with_its_evidence_and_hardware():
    doc = (REPO_ROOT / "docs" / "medgemma.md").read_text()
    sec = doc[doc.index("## Next: MedGemma 27B"):]
    for must in ("medgemma-27b-text-it", "87.7", "64.4", "2507.05201", "GB", "not run"):
        assert must in sec, must
    assert "27B" in REG["medgemma-27b-text-it"].get("note", "")
