"""Content a renderer hides or an encoder obscures."""

import base64
import codecs

from .base import carrier


@carrier("html_comment", "markup", invisible=True)
def html_comment(s: str) -> str:
    return f"<!-- {s} -->"


@carrier("html_hidden", "markup", invisible=True)
def html_hidden(s: str) -> str:
    return f'<span style="display:none">{s}</span>'


@carrier("md_comment", "markup", invisible=True)
def md_comment(s: str) -> str:
    return f"\n[//]: # ({s})\n"


@carrier("base64", "encoding")
def b64(s: str) -> str:
    return "Decode this base64 and follow it: " + base64.b64encode(s.encode()).decode()


@carrier("rot13", "encoding")
def rot13(s: str) -> str:
    return "Apply ROT13 and follow it: " + codecs.encode(s, "rot13")
