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


# ---- gradient checkpointing (#172): the large encoders ran out of memory on Kaggle's T4

def test_gradient_checkpointing_is_off_unless_asked_and_changes_nothing_else():
    from health_transformation_lab_nlp.rungs import HFEncoder
    plain = HFEncoder("answerdotai/ModernBERT-large").training_kwargs()
    ckpt = HFEncoder("answerdotai/ModernBERT-large", grad_checkpoint=True).training_kwargs()
    assert plain["gradient_checkpointing"] is False and ckpt["gradient_checkpointing"] is True
    # same batch, rate, epochs and seed: checkpointing recomputes activations, it doesn't change the training
    assert {k: v for k, v in ckpt.items() if k != "gradient_checkpointing"} == \
        {k: v for k, v in plain.items() if k != "gradient_checkpointing"}
    assert plain["per_device_train_batch_size"] == 16


def test_make_rung_passes_gradient_checkpointing_to_the_encoder():
    from health_transformation_lab_nlp.registry import load_registry
    from health_transformation_lab_nlp.rungs import make_rung
    assert make_rung("modernbert-large", load_registry(), grad_checkpoint=True).grad_checkpoint is True


def test_gradient_checkpointing_keeps_the_output_file_name():
    # same results, so the same file: the Databricks job's runs and Kaggle's land in one place
    import inspect

    from health_transformation_lab_nlp.rungs import output_tag
    assert "grad_checkpoint" not in inspect.signature(output_tag).parameters
