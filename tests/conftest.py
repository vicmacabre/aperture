import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _in_tmp(tmp_path, monkeypatch):
    """Every test runs in a scratch dir so .aperture/ run files never pollute
    the repo. PYTHONPATH is set so child `python -m aperture` subprocesses
    spawned by test_demo/test_e2e can find the package in a clean venv."""
    monkeypatch.chdir(tmp_path)
    src = str(Path(__file__).resolve().parent.parent / "src")
    existing = os.environ.get("PYTHONPATH", "")
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join(filter(None, [src, existing])))
