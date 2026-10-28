"""Running a pipeline script from a notebook so its output survives a crash (runlog.py)."""

import sys

import pytest

from dental_omop_nlp import runlog


def test_output_is_shown_as_it_comes_and_kept_in_a_log_file(tmp_path, capsys):
    log = tmp_path / "logs" / "run.log"
    code = runlog.run([sys.executable, "-c", "import sys; print('step 1'); print('oops', file=sys.stderr); print('step 2')"],
                      log_path=log)
    assert code == 0
    out = capsys.readouterr().out
    assert "step 1" in out and "oops" in out and "step 2" in out          # stderr too, in the notebook
    kept = log.read_text()
    assert "step 1" in kept and "step 2" in kept and "exit code 0" in kept


def test_a_killed_script_says_so_and_raises_when_asked(tmp_path, capsys):
    log = tmp_path / "run.log"
    cmd = [sys.executable, "-c", "import os, signal; print('loading model', flush=True); os.kill(os.getpid(), signal.SIGKILL)"]
    assert runlog.run(cmd, log_path=log) == -9
    out = capsys.readouterr().out
    assert "loading model" in out and "killed by signal 9" in out and "out of memory" in out
    assert "killed by signal 9" in log.read_text()                         # the log survives the crash
    with pytest.raises(RuntimeError, match="signal 9"):
        runlog.run(cmd, log_path=log, check=True)


def test_a_failing_script_reports_its_exit_code(tmp_path):
    with pytest.raises(RuntimeError, match="exit code 3"):
        runlog.run([sys.executable, "-c", "raise SystemExit(3)"], log_path=tmp_path / "r.log", check=True)


def test_gpu_notebooks_run_their_scripts_through_runlog():
    from dental_omop_nlp.paths import REPO_ROOT
    for nb in ("03_medgemma_reader.py", "08_encoder_gpu.py"):
        text = (REPO_ROOT / "databricks" / "notebooks" / nb).read_text()
        assert "capture_output" not in text, nb                            # output lost if Python dies
        assert "runlog.run(" in text, nb


def test_an_existing_log_is_never_appended_to(tmp_path, capsys):
    # Unity Catalog volumes can't append to a file ("OSError: [Errno 29] Illegal seek" on the second
    # MedGemma run): a run whose log already exists writes a new file next to it and says where
    log = tmp_path / "medgemma.log"
    runlog.run([sys.executable, "-c", "print('first run')"], log_path=log)
    first = log.read_text()
    runlog.run([sys.executable, "-c", "print('second run')"], log_path=log)
    runlog.run([sys.executable, "-c", "print('third run')"], log_path=log)
    assert log.read_text() == first                                     # untouched
    others = sorted(p for p in tmp_path.glob("medgemma_*.log"))
    assert len(others) == 2
    assert "second run" in others[0].read_text() + others[1].read_text()
    assert "third run" in others[0].read_text() + others[1].read_text()
    out = capsys.readouterr().out
    assert f"log: {others[0]}" in out or f"log: {others[1]}" in out


def test_scripts_dont_attach_to_the_notebooks_spark_gateway(monkeypatch, capsys):
    # MedGemma reader, 2026-10-28: the script inherited the notebook's Py4J gateway, MLflow attached to it
    # ("Connection to spark using Py4J from PID ..."), and when the script exited the notebook's next cell
    # failed with "Py4JException: Error while obtaining a new communication channel". Scripts don't use Spark.
    monkeypatch.setenv("PYSPARK_GATEWAY_PORT", "37723")
    monkeypatch.setenv("PYSPARK_GATEWAY_SECRET", "x")
    monkeypatch.setenv("DATABRICKS_HOST", "https://example")       # the login for MLflow still goes through
    code = "import os; print(sorted(k for k in ('PYSPARK_GATEWAY_PORT', 'PYSPARK_GATEWAY_SECRET', 'DATABRICKS_HOST') if k in os.environ))"
    assert runlog.run([sys.executable, "-c", code]) == 0
    assert "['DATABRICKS_HOST']" in capsys.readouterr().out
    import os
    assert os.environ["PYSPARK_GATEWAY_PORT"] == "37723"            # the notebook keeps its own
