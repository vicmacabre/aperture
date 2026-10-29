"""Ready-made pipeline stages, usable in your own STAGES list and in the demos."""

import re
import unicodedata

_INVISIBLE = re.compile(
    "[\u00ad\u061c\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff\ufe00-\ufe0f\U000e0000-\U000e007f\U000e0100-\U000e01ef]"
)
_ARABIC_MARKS = re.compile("[\u0640\u064b-\u065f\u0670]")  # tatweel + tashkeel
_YEH_KAF = {0x6A9: 0x643, 0x6CC: 0x64A}
_CONFUSABLES = str.maketrans("\u0430\u0435\u043e\u0440\u0441\u0445\u0443", "aeopcxy")  # demo-grade; use UTS #39 in production


def nfkc(t: str) -> str:
    return unicodedata.normalize("NFKC", t)


def strip_invisible(t: str) -> str:
    """Aggressive: also removes ZWNJ/ZWJ, which are legitimate in Persian/Arabic and emoji text."""
    return _INVISIBLE.sub("", t)


def arabic_fold(t: str) -> str:
    return _ARABIC_MARKS.sub("", t).translate(_YEH_KAF)


def fold_confusables(t: str) -> str:
    return t.translate(_CONFUSABLES)


def strip_tags(t: str) -> str:
    return re.sub(r"<[^>]*>", "", t)


def strip_markup(t: str) -> str:
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    t = re.sub(r"<(\w+)[^>]*(?:display\s*:\s*none|hidden)[^>]*>.*?</\1>", "", t, flags=re.S | re.I)
    t = re.sub(r"^\[//\]: # \(.*\)$", "", t, flags=re.M)
    return strip_tags(t)
