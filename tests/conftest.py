import pytest


@pytest.fixture(autouse=True)
def _in_tmp(tmp_path, monkeypatch):
    """Every test runs in a scratch dir so .aperture/ run files never pollute the repo."""
    monkeypatch.chdir(tmp_path)
