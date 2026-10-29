"""Targets: the three modes are three tiny classes behind one interface (core.Target).
HttpTarget covers black-box apps, bare models and RAG (several steps); PipelineTarget adds a trace."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .config import Config, ConfigError
from .core import OUTPUT, TRACE, Observation, Probe
from .curl import PLACEHOLDER, SECRETS, CurlError, Request, parse
from .http import extract, fetch


class HttpTarget:
    """One or more HTTP requests per probe; the last response is the observation.
    A RAG app is just two steps: add the document, then ask a question."""

    capabilities = frozenset({OUTPUT})
    deterministic = False
    max_concurrency = 8
    columns: list[str] = []

    def __init__(self, steps: list[Request], *, allow_private: bool = False, response_path: str = "") -> None:
        if not any(s.has_placeholder for s in steps):
            raise CurlError(f"no {PLACEHOLDER} found: mark where the test text goes")
        self.steps, self.allow_private, self.response_path = steps, allow_private, response_path
        # Multi-step targets (RAG: add document, then ask) share server-side state, so probes must not interleave.
        self.max_concurrency = 8 if len(steps) == 1 else 1
        last = urlsplit(steps[-1].url)
        self.description = f"{steps[-1].method} {last.netloc}{last.path}"
        self.fingerprint = hashlib.sha256("|".join(s.method + s.url for s in steps).encode()).hexdigest()[:16]

    def send(self, probe: Probe) -> Observation:
        body = ""
        for step in self.steps:
            body = fetch(step.fill(probe.text), allow_private=self.allow_private)
        return Observation(output=extract(body, self.response_path))

    def close(self) -> None:
        pass


class PipelineTarget:
    """Runs your pipeline file in a child process (crash/hang isolation, NOT a security sandbox) and
    records the text after every stage. Protocol: one JSON line in, one JSON line out."""

    capabilities = frozenset({OUTPUT, TRACE})
    max_concurrency = 1

    def __init__(self, file: str, timeout: float = 30.0) -> None:
        self.file, self.timeout = file, timeout
        self.description = f"pipeline:{Path(file).name}"
        self.fingerprint = hashlib.sha256(Path(file).read_bytes()).hexdigest()[:16]
        self._lock = threading.Lock()
        self.proc: subprocess.Popen[str] | None = None
        self._start()

    def _start(self) -> None:
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "aperture.worker", self.file],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        self._pool = ThreadPoolExecutor(1)
        hello = self._read()
        if not hello.get("ready"):
            raise ConfigError(f"pipeline file failed to load: {hello.get('error', 'no response')}")
        self.columns = [n for n, role in hello["stages"] if role != "model"]
        self.deterministic = all(role != "model" for _, role in hello["stages"])

    def _read(self) -> dict[str, Any]:
        assert self.proc and self.proc.stdout
        try:
            line = self._pool.submit(self.proc.stdout.readline).result(self.timeout)
        except FutureTimeout:
            self.proc.kill()
            raise TimeoutError(f"pipeline did not answer within {self.timeout}s") from None
        if not line:
            raise RuntimeError("pipeline process exited unexpectedly")
        out: dict[str, Any] = json.loads(line)
        return out

    def send(self, probe: Probe) -> Observation:
        with self._lock:
            if self.proc is None or self.proc.poll() is not None:
                self._start()
            assert self.proc and self.proc.stdin
            self.proc.stdin.write(json.dumps({"text": probe.text}) + "\n")
            self.proc.stdin.flush()
            r = self._read()
        return Observation(output=r["output"], trace=tuple(r["trace"]), error=r["error"])

    def close(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.kill()


def openai_request(cfg: Config) -> Request:
    headers = {"Content-Type": "application/json"}
    if cfg.key_env:
        key = os.environ.get(cfg.key_env)
        if not key:
            raise ConfigError(f"environment variable {cfg.key_env} is not set")
        SECRETS.add(key)
        headers["Authorization"] = f"Bearer {key}"
    body = json.dumps({"model": cfg.model, "temperature": 0, "messages": [{"role": "user", "content": PLACEHOLDER}]})
    return Request("POST", cfg.base_url.rstrip("/") + "/chat/completions", headers, body)


def build_target(cfg: Config) -> HttpTarget | PipelineTarget:
    if cfg.kind == "pipeline":
        return PipelineTarget(cfg.file)
    steps = [parse(s) for s in cfg.steps] if cfg.kind == "curl" else [openai_request(cfg)]
    return HttpTarget(steps, allow_private=cfg.allow_private, response_path=cfg.response_path)
