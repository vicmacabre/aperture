"""Arabic-script carriers. Why a dedicated pack: pipelines normalize Arabic differently from Latin
(most strip tatweel/tashkeel; NFKC alone does not), and ZWNJ is *legitimate* in Persian/Arabic text, so
blunt invisible-character stripping has a real false-positive cost."""

import unicodedata

from .base import carrier

# NFKC-reversible presentation forms (isolated shapes), derived from the Unicode database itself.
_ISOLATED = {
    unicodedata.normalize("NFKC", c): c for c in map(chr, range(0xFE70, 0xFEFD)) if unicodedata.decomposition(c).startswith("<isolated>")
}


def _after_letters(s: str, mark: str) -> str:
    return "".join(c + mark if "\u0621" <= c <= "\u064a" else c for c in s)


@carrier("control-ar", "control", lang="ar", control=True)
def control_ar(s: str) -> str:
    return s


@carrier("ar_tatweel", "arabic", lang="ar")
def ar_tatweel(s: str) -> str:  # kashida stretching
    return _after_letters(s, "\u0640")


@carrier("ar_tashkeel", "arabic", lang="ar")
def ar_tashkeel(s: str) -> str:  # vowel diacritics
    return _after_letters(s, "\u064e")


@carrier("ar_presentation", "arabic", lang="ar")
def ar_presentation(s: str) -> str:
    return "".join(_ISOLATED.get(c, c) for c in s)


@carrier("ar_yeh_kaf", "arabic", lang="ar")
def ar_yeh_kaf(s: str) -> str:  # Persian kaf/yeh lookalikes for Arabic kaf/yeh
    return s.translate({0x643: 0x6A9, 0x64A: 0x6CC})


@carrier("ar_bidi_marks", "arabic", lang="ar", invisible=True)
def ar_bidi_marks(s: str) -> str:  # right-to-left marks between letters
    return _after_letters(s, "\u200f")


@carrier("ar_zwnj", "arabic", lang="ar", invisible=True)
def ar_zwnj(s: str) -> str:  # legitimate in Persian, so naive stripping damages real text
    return _after_letters(s, "\u200c")
