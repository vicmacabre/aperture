"""A deliberately flawed pipeline. The bug: normalization runs AFTER the guardrail, so the guardrail
judges different text from the one the model reads."""

from aperture.demo.toy import guardrail, toy_model
from aperture.stages import nfkc, strip_tags

STAGES = [
    ("loader", lambda t: t),
    ("strip_tags", strip_tags),
    ("guardrail", guardrail, "guardrail"),
    ("nfkc", nfkc),
    ("model", toy_model, "model"),
]
