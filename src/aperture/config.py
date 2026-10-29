"""One flat, validated config. Unknown keys are errors: a typo in a security tool must fail loudly."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path


class ConfigError(ValueError):
    pass


@dataclass
class Config:
    kind: str  # curl | openai | pipeline
    authorized_by: str = ""  # who confirms they own / may test the target (required)
    steps: list[str] = field(default_factory=list)  # curl commands, in order (RAG: ingest, then ask)
    base_url: str = ""
    model: str = ""
    key_env: str = ""  # NAME of the env var holding the key; keys are never stored in config
    file: str = ""
    response_path: str = ""
    allow_private: bool = False
    trials: int = 3
    concurrency: int = 4
    rate: float = 2.0  # max requests per second
    max_calls: int = 1000
    carriers: list[str] = field(default_factory=lambda: ["*"])
    disable: list[str] = field(default_factory=list)

    def check(self) -> Config:
        need = {"curl": "steps", "openai": "base_url", "pipeline": "file"}.get(self.kind)
        if need is None:
            raise ConfigError(f"kind must be curl, openai or pipeline (got {self.kind!r})")
        if not getattr(self, need) or (self.kind == "openai" and not self.model):
            raise ConfigError(f"kind={self.kind!r} requires {need}" + (" and model" if self.kind == "openai" else ""))
        if not (1 <= self.trials <= 20 and 1 <= self.concurrency <= 32 and self.rate > 0 and self.max_calls >= 1):
            raise ConfigError("trials must be 1-20, concurrency 1-32, rate > 0, max_calls >= 1")
        return self


def load(path: str | Path) -> Config:
    try:
        raw = tomllib.loads(Path(path).read_text("utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as e:
        raise ConfigError(f"cannot read {path}: {e}") from None
    flat = {**raw.pop("target", {}), **raw.pop("run", {})}
    if raw:
        raise ConfigError(f"unknown sections: {sorted(raw)} (use [target] and [run])")
    unknown = flat.keys() - {f.name for f in fields(Config)}
    if unknown:
        raise ConfigError(f"unknown keys: {sorted(unknown)}")
    if "kind" not in flat:
        raise ConfigError("[target] needs kind = curl | openai | pipeline")
    return Config(**flat).check()
