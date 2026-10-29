import pytest

from aperture.carriers import FIXES, REGISTRY

CANARY = "AP-ABC123"


@pytest.mark.parametrize("c", REGISTRY.values(), ids=lambda c: c.name)
def test_carrier_contract(c):
    """Every carrier, built-in or third-party, must satisfy this to be trusted."""
    frag = c.fragment(CANARY)
    assert frag and frag == c.fragment(CANARY)  # non-empty, deterministic
    assert c.control or frag != c.plain(CANARY)  # actually hides something
    assert c.family in FIXES
    for odd in ("", "é☃😀", "\x00\n"):
        c.encode(odd)  # never crashes on odd input


def test_arabic_pack_present_and_instruction_is_arabic():
    ar = [c for c in REGISTRY.values() if c.family == "arabic"]
    assert len(ar) == 6 and all(c.lang == "ar" for c in ar)
    assert any("\u0600" <= ch <= "\u06ff" for ch in ar[0].plain(CANARY))
