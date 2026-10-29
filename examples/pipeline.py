"""A pipeline file: wrap YOUR real functions. Each stage is (name, fn) or (name, fn, role).
  transform (default) fn(text) -> text      guardrail  fn(text) -> True if it should be blocked
  model               fn(text) -> reply     (optional: without it you still learn what REACHES the model)
Run:  aperture run --pipeline examples/pipeline.py --authorized-by "Your Name"
"""

from aperture.stages import nfkc, strip_markup

# from my_app import load_document, is_suspicious, ask_llm   # <- your real code goes here
STAGES = [
    ("clean", strip_markup),
    ("normalize", nfkc),
    # ("guardrail", is_suspicious, "guardrail"),
    # ("llm", ask_llm, "model"),
]
