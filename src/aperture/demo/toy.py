"""SIMULATED components for the offline demo. The toy model is NOT a real LLM: it stands in for one that
can read Unicode tag characters and ignores zero-width/bidi/diacritic noise. Use a real target for real results."""

import re

from ..stages import arabic_fold, fold_confusables, nfkc, strip_invisible

_GUARD_CHARS = re.compile("[\u200b-\u200d\u2060\U000e0000-\U000e007f]")
_PHRASE = re.compile(r"reply with only the code", re.I)


def toy_model(text: str) -> str:
    t = "".join(chr(ord(c) - 0xE0000) if 0xE0020 <= ord(c) < 0xE0080 else c for c in text)
    t = fold_confusables(arabic_fold(strip_invisible(nfkc(t))))
    m = re.search(r"(?:the code|\u0627\u0644\u0631\u0645\u0632)\s+(AP-[0-9A-F]{6})", t)
    return m.group(1) if m else "Revenue grew 12% year over year."


def guardrail(t: str) -> bool:  # flags zero-width/tag characters and the (English) instruction phrase
    return bool(_GUARD_CHARS.search(t) or _PHRASE.search(t))


def bilingual_guardrail(t: str) -> bool:
    return guardrail(t) or "\u0627\u0643\u062a\u0628 \u0627\u0644\u0631\u0645\u0632" in t
