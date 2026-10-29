"""Reporters turn the report dict (plain JSON-able data) into terminal text, HTML, SARIF or a diff.
Everything dynamic is escaped; carrier fragments are never printed raw (they are invisible by design)."""

from __future__ import annotations

import html
import json
import os
import sys
from typing import Any

from .core import VERDICTS

_ANSI = {
    "EXPOSED": "1;31",
    "REACHES": "33",
    "HELD": "36",
    "CAUGHT": "32",
    "STRIPPED": "32",
    "INCONCLUSIVE": "90",
    "kept": "33",
    "revealed": "1;31",
    "stripped": "32",
    "flagged": "32",
    "passed": "33",
}
_WORD = {"kept": "kept", "revealed": "REVEALED", "stripped": "gone", "flagged": "FLAGGED", "passed": "passed"}
_MEANING = {
    "EXPOSED": "hidden instruction reached the model, it obeyed, nothing blocked it",
    "REACHES": "hidden text survives every stage unflagged (no model signal: potential)",
    "HELD": "reached the model, model did not obey",
    "CAUGHT": "a guardrail flagged and blocked it",
    "STRIPPED": "a stage removed it",
    "INCONCLUSIVE": "no usable evidence (errors, or the model ignores even plain instructions)",
}


def terminal(rep: dict[str, Any], color: bool | None = None) -> str:
    color = (sys.stdout.isatty() and "NO_COLOR" not in os.environ) if color is None else color
    paint = (lambda s, k: f"\033[{_ANSI[k]}m{s}\033[0m") if color else (lambda s, k: s)
    cols, rows = rep["columns"], rep["rows"]
    has_model = any(r["obeyed"] is not None for r in rows)
    head = ["carrier", *cols, *(["model"] if has_model else []), "verdict"]
    body = []
    for r in rows:
        cells = [(_WORD.get(r["cells"].get(c), "-"), r["cells"].get(c)) for c in cols]
        if has_model:
            cells.append((f"{r['obeyed']}/{r['n']} obeyed" if r["obeyed"] is not None else "-", None))
        v = r["verdict"] + (f" {r['exposed']}/{r['n']}" if r["verdict"] == "EXPOSED" and r["n"] > 1 else "")
        body.append([(r["carrier"], None), *cells, (v, r["verdict"])])
    widths = [max(len(h), *(len(b[i][0]) for b in body)) for i, h in enumerate(head)]

    def line(cells: list[tuple[str, str | None]]) -> str:
        return "  ".join((paint(t.ljust(w), k) if k else t.ljust(w)) for (t, k), w in zip(cells, widths, strict=True))

    out = [f"Aperture {rep['version']}  target: {rep['target']}  control: {rep['control']}", ""]
    out += [line([(h, None) for h in head]), "  ".join("-" * w for w in widths)]
    out += [line(b) for b in body]
    counts = {v: sum(r["verdict"] == v for r in rows) for v in VERDICTS}
    out += ["", "  ".join(paint(f"{v} {n}", v) for v, n in counts.items() if n)]
    fixes = dict.fromkeys(r["fix"] for r in rows if r["verdict"] in ("EXPOSED", "REACHES") and r["fix"])
    if fixes:
        out += ["", "Fix:"] + [f"  - {f}" for f in fixes]
    if rep["control"] == "failed":
        out += ["", "The model ignored even the plain-text control, so hidden-carrier results are INCONCLUSIVE."]
    out += ["", f"Only the {len(rows)} known carriers were tested: this is a lower bound on exposure, not a clean bill of health."]
    return "\n".join(out)


_CSS = """:root{color-scheme:light dark;--bg:#fff;--fg:#1b1f24;--mut:#6b7280;--bd:#d0d7de}
@media(prefers-color-scheme:dark){:root{--bg:#0d1117;--fg:#e6edf3;--mut:#8b949e;--bd:#30363d}}
body{background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem}
table{border-collapse:collapse;width:100%}th,td{border:1px solid var(--bd);padding:.35rem .6rem;text-align:left}th{color:var(--mut)}
.EXPOSED{background:#da3633;color:#fff;font-weight:700}.REACHES{background:#d29922;color:#000}.HELD{background:#388bfd44}
.CAUGHT,.STRIPPED{background:#2ea04344}.INCONCLUSIVE{opacity:.6}.revealed{background:#da363355}.kept{background:#d2992255}
.stripped,.flagged{background:#2ea04333}.passed{background:#d2992233}.mut{color:var(--mut)}li{margin:.3rem 0}"""


def html_report(rep: dict[str, Any]) -> str:
    e, cols, rows = html.escape, rep["columns"], rep["rows"]
    has_model = any(r["obeyed"] is not None for r in rows)
    th = "".join(f"<th>{e(h)}</th>" for h in ["carrier", "invisible", *cols, *(["model"] if has_model else []), "verdict"])
    trs = []
    for r in rows:
        tds = [f"<td>{e(r['carrier'])}</td>", f"<td>{'yes' if r['invisible'] else 'no'}</td>"]
        for c in cols:
            s = r["cells"].get(c)
            tds.append(f"<td class='{s if s in _WORD else ''}'>{e(_WORD.get(s, '-'))}</td>")
        if has_model:
            tds.append(f"<td>{e(str(r['obeyed']))}/{r['n']}</td>" if r["obeyed"] is not None else "<td>-</td>")
        lo, hi = r["ci"]
        tds.append(f"<td class='{r['verdict']}' title='exposed {r['exposed']}/{r['n']}, 95% CI {lo:.2f}-{hi:.2f}'>{e(r['verdict'])}</td>")
        trs.append("<tr>" + "".join(tds) + "</tr>")
    fixes = "".join(
        f"<li>{e(f)}</li>" for f in dict.fromkeys(r["fix"] for r in rows if r["verdict"] in ("EXPOSED", "REACHES") and r["fix"])
    )
    legend = "".join(f"<li><span class='{v}'>&nbsp;{v}&nbsp;</span> {e(m)}</li>" for v, m in _MEANING.items())
    return (
        f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Aperture report</title>"
        f"<style>{_CSS}</style><h1>Aperture exposure report</h1>"
        f"<p class=mut>target: {e(rep['target'])} &middot; control: {e(rep['control'])} &middot; {e(rep['created'])} &middot; v{e(rep['version'])}</p>"
        f"<table><tr>{th}</tr>{''.join(trs)}</table>"
        f"{'<h2>Fix</h2><ul>' + fixes + '</ul>' if fixes else ''}<h2>Legend</h2><ul>{legend}</ul>"
        f"<p class=mut>Only known carriers were tested: a lower bound on exposure, not proof of safety.</p>"
    )


def sarif(rep: dict[str, Any]) -> str:
    level = {"EXPOSED": "error", "REACHES": "warning"}
    results = [
        {
            "ruleId": r["carrier"],
            "level": level[r["verdict"]],
            "message": {"text": f"{r['verdict']}: carrier '{r['carrier']}' ({r['exposed']}/{r['n']} trials). {r['fix']}"},
            "locations": [{"physicalLocation": {"artifactLocation": {"uri": rep["config"] or "aperture.toml"}}}],
        }
        for r in rep["rows"]
        if r["verdict"] in level
    ]
    rules = [{"id": r["carrier"], "shortDescription": {"text": f"hidden-text carrier: {r['carrier']}"}} for r in rep["rows"]]
    driver = {"name": "aperture", "version": rep["version"], "rules": rules}
    return json.dumps(
        {
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "version": "2.1.0",
            "runs": [{"tool": {"driver": driver}, "results": results}],
        },
        indent=2,
    )


def diff(old: dict[str, Any], new: dict[str, Any]) -> tuple[list[str], bool]:
    """Compare two reports. Returns (changes, got_worse): the CI gate for exposure drift."""
    before = {r["carrier"]: r["verdict"] for r in old["rows"]}
    lines, worse = [], False
    for r in new["rows"]:
        a, b = before.get(r["carrier"]), r["verdict"]
        if a != b:
            lines.append(f"{r['carrier']}: {a or 'new'} -> {b}")
            worse = worse or (VERDICTS.index(b) < VERDICTS.index(a) if a else b in ("EXPOSED", "REACHES"))
    return lines, worse
