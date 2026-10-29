"""Invisible characters, lookalikes and normalization-reversible forms."""

from .base import carrier


@carrier("control", "control", control=True)
def control(s: str) -> str:
    return s


@carrier("tags", "invisible", invisible=True)
def tags(s: str) -> str:  # "ASCII smuggling": Unicode tag block mirrors ASCII and renders as nothing
    return "".join(chr(0xE0000 + ord(c)) for c in s)


@carrier("zw_bits", "invisible", invisible=True)
def zw_bits(s: str) -> str:  # the message as binary: ZWSP = 0, ZWNJ = 1
    bits = "".join(f"{b:08b}" for b in s.encode())
    return "\u2060" + "".join("\u200c" if b == "1" else "\u200b" for b in bits) + "\u2060"


@carrier("vs_bytes", "invisible", invisible=True)
def vs_bytes(s: str) -> str:  # one variation selector per byte
    return "".join(chr(0xFE00 + b if b < 16 else 0xE0100 + b - 16) for b in s.encode())


@carrier("zw_split", "invisible")
def zw_split(s: str) -> str:  # readable, but defeats substring/regex matching
    return "\u200b".join(s)


@carrier("soft_hyphen", "invisible")
def soft_hyphen(s: str) -> str:
    return "\u00ad".join(s)


@carrier("bidi_override", "invisible")
def bidi_override(s: str) -> str:  # displays reversed to a human; stored (and tokenized) forwards
    return "\u202e" + s + "\u202c"


@carrier("fullwidth", "normalize")
def fullwidth(s: str) -> str:  # NFKC turns this back into plain ASCII
    return "".join(chr(ord(c) + 0xFEE0) if "!" <= c <= "~" else c for c in s)


def _bold(c: str) -> str:
    if "A" <= c <= "Z":
        return chr(0x1D400 + ord(c) - 65)
    if "a" <= c <= "z":
        return chr(0x1D41A + ord(c) - 97)
    if "0" <= c <= "9":
        return chr(0x1D7CE + ord(c) - 48)
    return c


@carrier("mathbold", "normalize")
def mathbold(s: str) -> str:
    return "".join(map(_bold, s))


@carrier("homoglyph", "homoglyph")
def homoglyph(s: str) -> str:  # lowercase only: the canary (uppercase hex) stays intact
    return s.translate(str.maketrans("aeopcxy", "\u0430\u0435\u043e\u0440\u0441\u0445\u0443"))
