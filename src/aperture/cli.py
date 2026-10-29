"""Thin shell over the engine. Nothing here is needed to use Aperture as a library."""

from __future__ import annotations

import argparse
import ipaddress
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from . import __version__, report
from .carriers import REGISTRY, select
from .config import Config, ConfigError, load
from .curl import CurlError, parse
from .engine import Aborted, Store, build_probes, build_report, execute, summarize
from .http import Blocked, redact
from .oracles import ORACLES
from .targets import build_target

DEFAULT_CONFIG = "aperture.toml"


def _run(cfg: Config, args: argparse.Namespace, config_name: str, demo: bool = False) -> int:
    if not demo and not cfg.authorized_by:
        raise ConfigError("authorized_by is required: confirm you own this target or are authorized to test it")
    target = build_target(cfg)
    try:
        carriers = select(args.carriers or cfg.carriers, cfg.disable)
        oracles = [o for o in ORACLES if o.requires in target.capabilities]
        store = Store(".aperture", target.fingerprint, args.resume)
        probes = list(build_probes(carriers, 1 if target.deterministic else cfg.trials, store.secret))
        tick = (lambda i, n: print(f"\r  probes {i}/{n}", end="", file=sys.stderr)) if sys.stderr.isatty() else None
        execute(target, probes, store, concurrency=cfg.concurrency, rate=cfg.rate, max_calls=cfg.max_calls, progress=tick)
        if tick:
            print(file=sys.stderr)
        rows, control = summarize(probes, store.done, oracles)
    finally:
        target.close()
    rep = build_report(target, config_name, rows, control)
    Path(args.json).write_text(json.dumps(rep, indent=2), "utf-8")
    if args.html:
        Path(args.html).write_text(report.html_report(rep), "utf-8")
    if args.sarif:
        Path(args.sarif).write_text(report.sarif(rep), "utf-8")
    print(report.terminal(rep))
    bad = {"exposed": ("EXPOSED",), "reaches": ("EXPOSED", "REACHES"), "never": ()}[args.fail_on]
    return int(any(r["verdict"] in bad for r in rep["rows"]))


def _cmd_run(args: argparse.Namespace) -> int:
    if args.pipeline or args.url:
        cfg = (
            Config("pipeline", file=args.pipeline)
            if args.pipeline
            else Config("openai", base_url=args.url, model=args.model or "", key_env=args.key_env or "", allow_private=True)
        )
        cfg.authorized_by = args.authorized_by or ""
        cfg.check()
        return _run(cfg, args, "(command line)")
    path = args.config or DEFAULT_CONFIG
    if not Path(path).exists():
        raise ConfigError(f"{path} not found. Run `aperture init`, or pass --url/--pipeline.")
    return _run(load(path), args, path)


def _cmd_demo(args: argparse.Namespace) -> int:
    args.fail_on, args.carriers, args.resume = "never", None, False
    f = Path(__file__).parent / "demo" / ("hardened.py" if args.hardened else "leaky.py")
    print(f"SIMULATED demo ({f.name}): a toy model stands in for a real LLM.\n")
    return _run(Config("pipeline", file=str(f), trials=1, rate=1000.0), args, f"demo/{f.name}", demo=True)


def _cmd_report(args: argparse.Namespace) -> int:
    rep = json.loads(Path(args.report).read_text("utf-8"))
    if args.html:
        Path(args.html).write_text(report.html_report(rep), "utf-8")
    if args.sarif:
        Path(args.sarif).write_text(report.sarif(rep), "utf-8")
    print(report.terminal(rep))
    return 0


def _cmd_diff(args: argparse.Namespace) -> int:
    lines, worse = report.diff(json.loads(Path(args.old).read_text("utf-8")), json.loads(Path(args.new).read_text("utf-8")))
    print("\n".join(lines) or "no changes")
    return int(worse)


def _cmd_carriers(args: argparse.Namespace) -> int:
    for c in REGISTRY.values():
        print(f"{c.name:<16} {c.family:<10} {c.lang}  {'invisible' if c.invisible else 'visible':<9} {'(control)' if c.control else ''}")
    return 0


def _is_local(url: str) -> bool:
    host = urlsplit(url).hostname or ""
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_loopback
    except ValueError:
        return host == "localhost" or host.endswith(".local")


def _cmd_init(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if path.exists() and not args.force:
        raise ConfigError(f"{path} already exists (use --force to overwrite)")

    def ask(q: str, default: str = "") -> str:
        return input(f"{q}{f' [{default}]' if default else ''}: ").strip() or default

    def paste(q: str) -> str:
        print(
            f"{q}\n(paste the curl command in bash format, put {{{{PROBE}}}} where the test text goes, then press Enter on an empty line)"
        )
        lines: list[str] = []
        while (line := input()).strip():
            lines.append(line)
        parse("\n".join(lines))  # validate now, not at run time
        return "\n".join(lines)

    print(
        "What do you want to test?\n  1) a model with an OpenAI-style API (OpenAI, Ollama, LM Studio, vLLM...)\n  2) any HTTP endpoint (paste a curl command)\n  3) a RAG app (a curl that adds a document + a curl that asks a question)\n  4) a Python pipeline file"
    )
    choice, url = ask("Choice", "1"), ""
    t: dict[str, Any] = {}
    if choice == "1":
        url = ask("Base URL", "http://localhost:11434/v1")
        t = {
            "kind": "openai",
            "base_url": url,
            "model": ask("Model name"),
            "key_env": ask("Name of the env var holding the API key (blank for none)"),
        }
    elif choice == "2":
        steps = [paste("Request that sends a message:")]
        t = {"kind": "curl", "steps": steps}
    elif choice == "3":
        steps = [paste("Request that ADDS a document ({{PROBE}} = document text):"), paste("Request that ASKS a question about it:")]
        t = {"kind": "curl", "steps": steps}
    elif choice == "4":
        t = {"kind": "pipeline", "file": ask("Path to your pipeline .py file")}
    else:
        raise ConfigError("choose 1-4")
    url = url or (parse(t["steps"][0]).url if t.get("steps") else "")
    if url and _is_local(url) and ask("This is a local/LAN address. Allow testing it? (y/N)", "N").lower() == "y":
        t["allow_private"] = True
    t["authorized_by"] = ask("Type your name to confirm you own this target or are authorized to test it")
    if not t["authorized_by"]:
        raise ConfigError("authorization confirmation is required")
    lines = ["[target]"] + [f"{k} = {json.dumps(v)}" for k, v in t.items() if v != ""]
    lines += ["", "[run]", "trials = 3", "concurrency = 4", "rate = 2.0", "max_calls = 300"]
    path.write_text("\n".join(lines) + "\n", "utf-8")
    print(f"\nWrote {path}. Next: aperture run")
    return 0


def main(argv: list[str] | None = None) -> int:
    out = argparse.ArgumentParser(add_help=False)
    out.add_argument("--json", default="aperture-report.json", help="where to write the machine-readable report")
    out.add_argument("--html", help="also write a shareable HTML heatmap")
    out.add_argument("--sarif", help="also write SARIF (GitHub code scanning)")
    p = argparse.ArgumentParser(prog="aperture", description="Which hidden-text carriers can actually reach your LLM?")
    p.add_argument("--version", action="version", version=f"aperture {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", parents=[out], help="test a target")
    r.add_argument("--config", help=f"config file (default {DEFAULT_CONFIG})")
    r.add_argument("--url", help="quick mode: OpenAI-compatible base URL (e.g. http://localhost:11434/v1)")
    r.add_argument("--model")
    r.add_argument("--key-env", help="NAME of the env var holding the API key")
    r.add_argument("--pipeline", help="quick mode: path to a pipeline .py file")
    r.add_argument("--authorized-by", help="quick mode: your name, confirming you may test this target")
    r.add_argument("--carriers", action="append", help="only these carriers/families (glob, repeatable)")
    r.add_argument("--resume", action="store_true", help="continue the last interrupted run of this target")
    r.add_argument("--fail-on", choices=["exposed", "reaches", "never"], default="exposed", help="exit 1 when found (CI gate)")
    r.set_defaults(fn=_cmd_run)
    d = sub.add_parser("demo", parents=[out], help="offline demo, no network, no key")
    d.add_argument("--hardened", action="store_true", help="run the fixed pipeline instead of the leaky one")
    d.set_defaults(fn=_cmd_demo)
    i = sub.add_parser("init", help="guided setup: writes aperture.toml")
    i.add_argument("--path", default=DEFAULT_CONFIG)
    i.add_argument("--force", action="store_true")
    i.set_defaults(fn=_cmd_init)
    rp = sub.add_parser("report", help="re-render a saved JSON report")
    rp.add_argument("report")
    rp.add_argument("--html")
    rp.add_argument("--sarif")
    rp.set_defaults(fn=_cmd_report)
    df = sub.add_parser("diff", help="compare two reports; exit 1 if exposure got worse")
    df.add_argument("old")
    df.add_argument("new")
    df.set_defaults(fn=_cmd_diff)
    sub.add_parser("carriers", help="list every hidden-text carrier").set_defaults(fn=_cmd_carriers)

    args = p.parse_args(argv)
    try:
        return int(args.fn(args))
    except (ConfigError, CurlError, Blocked, Aborted, ValueError, OSError, TimeoutError, RuntimeError) as e:
        print(f"aperture: error: {redact(str(e))}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\ninterrupted: progress is saved, continue with --resume", file=sys.stderr)
        return 130
