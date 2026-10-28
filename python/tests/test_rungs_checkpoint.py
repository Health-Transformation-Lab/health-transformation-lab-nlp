"""Encoder fine-tuning resumes an interrupted run from its latest checkpoint, and only that."""

from health_transformation_lab_nlp.rungs import _clear_checkpoints, _last_checkpoint


def _ckpt(root, step, complete=True):
    d = root / f"checkpoint-{step}"
    d.mkdir()
    if complete:
        (d / "trainer_state.json").write_text("{}")
    return d


def test_last_checkpoint_picks_the_highest_complete_step(tmp_path):
    assert _last_checkpoint(tmp_path) is None
    assert _last_checkpoint(tmp_path / "missing") is None
    for step in (50, 400, 100):
        _ckpt(tmp_path, step)
    _ckpt(tmp_path, 450, complete=False)                      # killed mid-save: no trainer_state.json
    (tmp_path / "checkpoint-tmp").mkdir()                     # not a step: ignored
    assert _last_checkpoint(tmp_path) == str(tmp_path / "checkpoint-400")


def test_a_finished_run_leaves_nothing_to_resume(tmp_path):
    """The Trainer saves a final checkpoint; left in place, the next fit of the same model would
    'resume' it, train zero steps and predict with the old run's weights."""
    _ckpt(tmp_path, 654)
    (tmp_path / "keep.txt").write_text("x")                   # anything else in the folder stays
    _clear_checkpoints(tmp_path)
    assert _last_checkpoint(tmp_path) is None
    assert (tmp_path / "keep.txt").exists()
    _clear_checkpoints(tmp_path / "missing")                  # no folder: no error
