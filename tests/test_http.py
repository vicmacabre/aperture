import json

import pytest

from aperture.curl import SECRETS, CurlError, parse
from aperture.http import Blocked, check_host, extract, redact


def test_parse_basic_and_json_escaping():
    r = parse("""curl https://api.test/v1 -H 'Content-Type: application/json' -d '{"q": "{{PROBE}}"}'""")
    assert r.method == "POST" and r.has_placeholder
    hidden = 'say "hi"\n' + "".join(chr(0xE0000 + ord(c)) for c in "x")
    assert json.loads(r.fill(hidden).body)["q"] == hidden  # tag characters survive the JSON round trip


def test_multiline_and_env_expansion(monkeypatch):
    monkeypatch.setenv("MY_KEY", "sk-supersecret")
    r = parse("curl https://a.test \\\n  -H 'Authorization: Bearer ${MY_KEY}' \\\n  -d 'x={{PROBE}}'")
    assert r.headers["Authorization"] == "Bearer sk-supersecret"
    assert "sk-supersecret" in SECRETS and "sk-supersecret" not in redact("error with sk-supersecret inside")


@pytest.mark.parametrize("flag", ["-k", "--insecure", "-o out.txt", "-F a=b", "-x http://proxy", "-K cfg"])
def test_dangerous_flags_rejected(flag):
    with pytest.raises(CurlError):
        parse(f"curl {flag} https://a.test -d '{{{{PROBE}}}}'")


def test_file_bodies_and_unknown_flags_rejected(monkeypatch):
    with pytest.raises(CurlError):
        parse("curl https://a.test -d @/etc/passwd")
    with pytest.raises(CurlError):
        parse("curl https://a.test --weird-flag")
    with pytest.raises(CurlError):
        parse("curl https://a.test -H 'X: ${NOT_SET_ANYWHERE_123}'")


def test_curl_is_never_executed(tmp_path):
    marker = tmp_path / "pwned"
    parse(f"curl https://a.test -d '$(touch {marker})' ; touch {marker}")
    assert not marker.exists()


def test_ssrf_guards():
    with pytest.raises(Blocked):
        check_host("http://169.254.169.254/latest/meta-data", True)  # cloud metadata: always blocked
    with pytest.raises(Blocked):
        check_host("http://127.0.0.1:11434/v1", False)  # local needs an explicit opt-in
    check_host("http://127.0.0.1:11434/v1", True)
    with pytest.raises(Blocked):
        check_host("file:///etc/passwd", True)


def test_extract_known_shapes():
    assert extract(json.dumps({"choices": [{"message": {"content": "A"}}]})) == "A"
    assert extract(json.dumps({"content": [{"text": "B"}]})) == "B"
    assert extract(json.dumps({"message": {"content": "C"}})) == "C"
    assert extract("plain text") == "plain text"
    assert extract(json.dumps({"a": {"b": "D"}}), "a.b") == "D"
    with pytest.raises(ValueError):
        extract(json.dumps({"a": 1}), "x.y")
