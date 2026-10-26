"""Encoder fine-tuning resumes from its latest checkpoint (CPU runs get interrupted)."""

from dental_omop_nlp.rungs import _last_checkpoint


def test_last_checkpoint_picks_the_highest_step(tmp_path):
    assert _last_checkpoint(tmp_path) is None
    assert _last_checkpoint(tmp_path / "missing") is None
    for step in (50, 400, 100):
        (tmp_path / f"checkpoint-{step}").mkdir()
    (tmp_path / "checkpoint-tmp").mkdir()                     # not a step: ignored
    assert _last_checkpoint(tmp_path) == str(tmp_path / "checkpoint-400")
