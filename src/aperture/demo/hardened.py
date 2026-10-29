"""The same pipeline, fixed: clean first, judge the cleaned text, then let the model read it."""

from aperture.demo.toy import bilingual_guardrail, toy_model
from aperture.stages import arabic_fold, fold_confusables, nfkc, strip_invisible, strip_markup

STAGES = [
    ("loader", lambda t: t),
    ("strip_markup", strip_markup),
    ("nfkc", nfkc),
    ("strip_invisible", strip_invisible),
    ("arabic_fold", arabic_fold),
    ("confusables", fold_confusables),
    ("guardrail", bilingual_guardrail, "guardrail"),
    ("model", toy_model, "model"),
]
