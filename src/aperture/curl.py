"""A strict curl-command parser. It tokenizes; it never runs a shell, never executes anything, and
rejects every flag that could touch files, proxies or TLS settings."""

from __future__ import annotations

import base64
import json
import os
import re
import shlex
from dataclasses import dataclass
from urllib.parse import quote

PLACEHOLDER = "{{PROBE}}"
SECRETS: set[str] = set()  # every credential seen; redacted from all output


class CurlError(ValueError):
    pass


_SKIP = {
    "-s",
    "--silent",
    "-S",
    "--show-error",
    "-L",
    "--location",
    "--compressed",
    "-i",
    "--include",
    "-v",
    "--verbose",
    "-g",
    "--globoff",
    "--http1.1",
    "--http2",
}
_REJECT = {
    "-k",
    "--insecure",
    "-o",
    "--output",
    "-O",
    "--remote-name",
    "-T",
    "--upload-file",
    "-F",
    "--form",
    "-x",
    "--proxy",
    "-K",
    "--config",
    "--cacert",
    "--cert",
}
_DATA = {"-d", "--data", "--data-raw", "--data-binary", "--data-ascii"}
_VALUE = _DATA | {
    "-X",
    "--request",
    "-H",
    "--header",
    "--url",
    "-u",
    "--user",
    "-A",
    "--user-agent",
    "-b",
    "--cookie",
    "-m",
    "--max-time",
    "--connect-timeout",
    "--retry",
}
_SENSITIVE = {"authorization", "proxy-authorization", "x-api-key", "api-key", "cookie"}


@dataclass(frozen=True)
class Request:
    method: str
    url: str
    headers: dict[str, str]
    body: str | None = None

    def fill(self, text: str) -> Request:
        """Substitute the probe, escaping for the context (JSON body / URL / header)."""
        ctype = next((v for k, v in self.headers.items() if k.lower() == "content-type"), "")
        in_body = json.dumps(text)[1:-1] if "json" in ctype.lower() else text
        return Request(
            self.method,
            self.url.replace(PLACEHOLDER, quote(text, safe="")),
            {k: v.replace(PLACEHOLDER, text) for k, v in self.headers.items()},
            self.body.replace(PLACEHOLDER, in_body) if self.body is not None else None,
        )

    @property
    def has_placeholder(self) -> bool:
        return PLACEHOLDER in self.url + (self.body or "") + "".join(self.headers.values())


def _expand(s: str) -> str:
    def sub(m: re.Match[str]) -> str:
        v = os.environ.get(m[1])
        if v is None:
            raise CurlError(f"environment variable {m[1]} is not set")
        SECRETS.add(v)
        return v

    return re.sub(r"\$\{(\w+)\}", sub, s)


def parse(cmd: str) -> Request:
    try:
        toks = shlex.split(re.sub(r"\\\r?\n", " ", cmd))
    except ValueError as e:
        raise CurlError(f"cannot parse curl command: {e}") from None
    if not toks or toks[0] != "curl":
        raise CurlError("the command must start with 'curl' (copy it in bash format)")
    method = url = None
    headers: dict[str, str] = {}
    data: list[str] = []
    i = 1
    while i < len(toks):
        t, i = toks[i], i + 1
        flag, eq, val = t.partition("=") if t.startswith("--") else (t, "", "")
        if flag in _SKIP:
            continue
        if flag in _REJECT:
            raise CurlError(f"{flag} is not allowed (it could touch files, proxies or TLS settings)")
        if flag in _VALUE:
            if not eq:
                if i >= len(toks):
                    raise CurlError(f"{flag} needs a value")
                val, i = toks[i], i + 1
            val = _expand(val)
            if flag in ("-X", "--request"):
                method = val.upper()
            elif flag in ("-H", "--header"):
                k, _, v = val.partition(":")
                headers[k.strip()] = v.strip()
            elif flag in _DATA:
                if val.startswith("@"):
                    raise CurlError("reading request bodies from files (@file) is not allowed")
                data.append(val)
            elif flag == "--url":
                url = val
            elif flag in ("-u", "--user"):
                SECRETS.add(val)
                headers["Authorization"] = "Basic " + base64.b64encode(val.encode()).decode()
            elif flag in ("-A", "--user-agent"):
                headers["User-Agent"] = val
            elif flag in ("-b", "--cookie"):
                headers["Cookie"] = val
        elif t.startswith("-"):
            raise CurlError(f"unsupported curl flag {t!r}: remove it from the command")
        else:
            url = _expand(t)
    if not url:
        raise CurlError("no URL found in the curl command")
    for k, v in headers.items():
        if k.lower() in _SENSITIVE:
            SECRETS.update({v, v.split()[-1]})
    return Request(method or ("POST" if data else "GET"), url, headers, "&".join(data) if data else None)
