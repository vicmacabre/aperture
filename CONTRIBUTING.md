# Contributing to Aperture

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Running the checks

```bash
ruff check .
ruff format --check .
mypy
pytest -q
```

Or in one line: `ruff check . && ruff format --check . && mypy && pytest -q`.

## Adding a carrier

A carrier is a single function registered with `@carrier(...)`:

```python
from aperture.carriers import carrier

@carrier("my_trick", "invisible", invisible=True)
def my_trick(s: str) -> str:
    ...
```

Every carrier **must** satisfy the contract in
`tests/test_carriers.py::test_carrier_contract`: non-empty, deterministic,
different from plain text unless `control=True`, and must not crash on
`""`, `"é☃😀"`, or `"\x00\n"`.

## Adding an oracle, target, or reporter

See `docs/ARCHITECTURE.md` for the port contract each one must satisfy.

## Pull requests

- One logical change per PR.
- Run the full check suite before pushing.
- New features need a test. Bug fixes need a regression test.
- Security issues → see `SECURITY.md`, do not open a public issue.
