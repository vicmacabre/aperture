.PHONY: install lint test demo clean

install:
	pip install -e ".[dev]"

lint:
	ruff check .
	ruff format --check .
	mypy

test:
	pytest -q

demo:
	cd src && python -m aperture demo && python -m aperture demo --hardened

clean:
	rm -rf .aperture .pytest_cache .mypy_cache .ruff_cache *.egg-info build dist
	rm -f r.json leaky.json hard.json *.sarif r.html report.html
