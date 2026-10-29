"""Real HTTP, no mocks of our own code: a tiny local 'LLM' that can read Unicode tag characters."""

import json
import re
import threading
import unicodedata
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from aperture.cli import main
from aperture.config import load

DOCS: list[str] = []


def read_hidden(text: str) -> str:
    t = "".join(chr(ord(c) - 0xE0000) if 0xE0020 <= ord(c) < 0xE0080 else c for c in text)
    m = re.search(r"the code (AP-[0-9A-F]{6})", unicodedata.normalize("NFKC", t))
    return m.group(1) if m else "A short summary."


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/v1/chat/completions":
            out = {"choices": [{"message": {"content": read_hidden(body["messages"][0]["content"])}}]}
        elif self.path == "/ingest":
            DOCS.append(body["doc"])
            out = {"ok": True}
        else:  # /ask: answers from the last ingested document
            out = {"answer": read_hidden(DOCS[-1])}
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


@pytest.fixture()
def server():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def verdicts():
    return {r["carrier"]: r["verdict"] for r in json.loads(Path("r.json").read_text())["rows"]}


def test_openai_compatible_model_mode(server):
    rc = main(
        [
            "run",
            "--url",
            f"{server}/v1",
            "--model",
            "m",
            "--authorized-by",
            "tester",
            "--json",
            "r.json",
            "--carriers",
            "tags",
            "--carriers",
            "base64",
        ]
    )
    v = verdicts()
    assert rc == 1 and v["tags"] == "EXPOSED" and v["base64"] == "HELD"


def test_rag_two_step_via_curl(server):
    Path("aperture.toml").write_text(
        f"""[target]
kind = "curl"
authorized_by = "tester"
allow_private = true
steps = ['''curl {server}/ingest -H 'Content-Type: application/json' -d '{{"doc": "{{{{PROBE}}}}"}}' ''',
         '''curl {server}/ask -H 'Content-Type: application/json' -d '{{}}' ''']
[run]
trials = 2
rate = 1000.0
"""
    )
    assert load("aperture.toml").kind == "curl"
    rc = main(["run", "--json", "r.json", "--carriers", "tags", "--carriers", "fullwidth", "--carriers", "rot13"])
    v = verdicts()
    assert rc == 1 and v["tags"] == "EXPOSED" and v["fullwidth"] == "EXPOSED" and v["rot13"] == "HELD"


def test_private_target_blocked_without_opt_in(server, capsys):
    Path("aperture.toml").write_text(f'[target]\nkind="openai"\nbase_url="{server}/v1"\nmodel="m"\nauthorized_by="t"\n')
    assert main(["run", "--json", "r.json"]) == 2
    assert "allow_private" in capsys.readouterr().err


def test_wizard_writes_a_loadable_config(monkeypatch):
    answers = iter(["1", "http://localhost:11434/v1", "llama3", "", "y", "Victor"])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))
    assert main(["init"]) == 0
    cfg = load("aperture.toml")
    assert (cfg.kind, cfg.model, cfg.allow_private, cfg.authorized_by) == ("openai", "llama3", True, "Victor")
    assert main(["init"]) == 2  # refuses to overwrite


def test_config_typos_fail_loudly():
    Path("bad.toml").write_text('[target]\nkind="openai"\nbase_url="http://x"\nmodle="m"\n')
    assert main(["run", "--config", "bad.toml"]) == 2
