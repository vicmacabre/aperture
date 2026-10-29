import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from aperture.cli import main
from aperture.targets import PipelineTarget


def verdicts(*flags):
    assert main(["demo", "--json", "r.json", *flags]) == 0
    return {r["carrier"]: r["verdict"] for r in json.loads(Path("r.json").read_text())["rows"]}


def test_leaky_pipeline_leaks_and_hardened_does_not():
    leaky, hard = verdicts(), verdicts("--hardened")
    assert {"fullwidth", "homoglyph", "ar_tatweel", "ar_presentation", "soft_hyphen"} <= {c for c, v in leaky.items() if v == "EXPOSED"}
    assert "EXPOSED" not in hard.values() and "REACHES" not in hard.values()
    assert leaky["tags"] == "CAUGHT"


def test_diff_flags_regressions(capsys):
    verdicts()
    Path("leaky.json").write_text(Path("r.json").read_text())
    verdicts("--hardened")
    assert main(["diff", "r.json", "leaky.json"]) == 1  # hardened -> leaky is worse
    assert main(["diff", "leaky.json", "r.json"]) == 0


def test_html_and_sarif_outputs():
    assert main(["demo", "--json", "r.json", "--html", "r.html", "--sarif", "r.sarif"]) == 0
    sarif = json.loads(Path("r.sarif").read_text())
    assert sarif["version"] == "2.1.0" and sarif["runs"][0]["results"]
    assert "<script" not in Path("r.html").read_text().lower()


def test_report_escapes_hostile_content():
    from aperture import report

    rep = {
        "tool": "aperture",
        "version": "x",
        "target": "<script>alert(1)</script>",
        "config": "",
        "created": "now",
        "control": "ok",
        "columns": ["<img src=x onerror=1>"],
        "rows": [
            {
                "carrier": "<b>",
                "family": "f",
                "invisible": True,
                "verdict": "EXPOSED",
                "exposed": 1,
                "obeyed": 1,
                "n": 1,
                "ci": [0, 1],
                "cells": {"<img src=x onerror=1>": "kept"},
                "fix": "<script>x</script>",
            }
        ],
    }
    out = report.html_report(rep)
    assert "<script>" not in out and "<img src=x" not in out


def test_pipeline_timeout_kills_hung_stage(tmp_path):
    f = tmp_path / "hang.py"
    f.write_text("import time\nSTAGES = [('slow', lambda t: time.sleep(30) or t)]\n")
    t = PipelineTarget(str(f), timeout=1.0)
    from aperture.core import Probe

    start = time.time()
    with pytest.raises(TimeoutError):
        t.send(Probe("x#0", "x", 0, "AP-1", "f", "text"))
    assert time.time() - start < 10
    t.close()


def test_broken_pipeline_file_fails_with_a_clear_error(tmp_path):
    f = tmp_path / "bad.py"
    f.write_text("STAGES = 1 / 0\n")
    from aperture.config import ConfigError

    with pytest.raises(ConfigError, match="failed to load"):
        PipelineTarget(str(f))


def test_cli_refuses_without_authorization(tmp_path):
    (tmp_path / "p.py").write_text("STAGES = [('x', lambda t: t)]\n")
    assert main(["run", "--pipeline", str(tmp_path / "p.py")]) == 2
    assert subprocess.run([sys.executable, "-m", "aperture", "--version"], capture_output=True).returncode == 0
