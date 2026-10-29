"""The only module that touches the network. stdlib only, so it can be audited in one sitting.

Hardening: TLS verification always on, redirects refused, link-local/metadata/reserved addresses always
blocked, private/loopback blocked unless the config opts in, responses size-capped, secrets redacted."""

from __future__ import annotations

import ipaddress
import json
import random
import socket
import time
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlsplit

from .curl import SECRETS, Request


class Blocked(Exception):
    pass


def redact(s: str) -> str:
    for secret in sorted(SECRETS, key=len, reverse=True):
        if len(secret) >= 4:
            s = s.replace(secret, "***")
    return s


def check_host(url: str, allow_private: bool) -> None:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise Blocked("only http(s) URLs are allowed")
    for info in socket.getaddrinfo(parts.hostname, parts.port or 443):
        ip = ipaddress.ip_address(str(info[4][0]).split("%")[0])
        if ip.is_link_local or ip.is_multicast or ip.is_unspecified or ip.is_reserved:
            raise Blocked(f"{parts.hostname} resolves to a blocked address ({ip})")
        if (ip.is_private or ip.is_loopback) and not allow_private:
            raise Blocked(f"{parts.hostname} is a private/local address: set allow_private = true to test local or LAN targets")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a: Any, **k: Any) -> None:
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def fetch(req: Request, *, allow_private: bool, timeout: float = 60.0, max_bytes: int = 1_000_000, tries: int = 3) -> str:
    check_host(req.url, allow_private)
    headers = {"User-Agent": "aperture/0.1", **req.headers}
    r = urllib.request.Request(req.url, req.body.encode() if req.body is not None else None, headers, method=req.method)
    err = ""
    for attempt in range(tries):
        try:
            with _OPENER.open(r, timeout=timeout) as resp:
                return str(resp.read(max_bytes).decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            err = f"HTTP {e.code}: {e.read(300).decode('utf-8', 'replace')}"
            if e.code != 429 and e.code < 500:
                raise RuntimeError(redact(err)) from None
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            err = f"{type(e).__name__}: {e}"
        if attempt < tries - 1:
            time.sleep(min(30.0, 2.0**attempt + random.random()))
    raise RuntimeError(redact(f"failed after {tries} tries: {err}"))


_PATHS = (
    "choices.0.message.content",
    "choices.0.text",
    "content.0.text",
    "message.content",
    "response",
    "candidates.0.content.parts.0.text",
    "output_text",
    "text",
    "answer",
    "result",
    "output",
)


def _dig(obj: Any, path: str) -> Any:
    for part in path.split("."):
        obj = obj[int(part)] if isinstance(obj, list) else obj[part]
    return obj


def extract(body: str, path: str = "") -> str:
    """Pull the model's text out of a response: known API shapes first, else the raw body."""
    try:
        data = json.loads(body)
    except ValueError:
        return body
    for p in [path] if path else _PATHS:
        try:
            v = _dig(data, p)
        except (KeyError, IndexError, ValueError, TypeError):
            continue
        if isinstance(v, str):
            return v
    if path:
        raise ValueError(f"response_path {path!r} not found in the response")
    return body
