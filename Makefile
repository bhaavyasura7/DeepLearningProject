.PHONY: setup data index demo record eval verify test clean

PYTHON = .venv/bin/python
PIP = .venv/bin/pip
UVICORN = .venv/bin/uvicorn
PYTEST = .venv/bin/pytest

setup:
	@if [ ! -d ".venv" ]; then uv venv --python 3.11 .venv; fi
	uv pip install -r requirements.txt --python .venv

data:
	$(PYTHON) -m src.cinemind.data.build_catalog

index:
	$(PYTHON) -m src.cinemind.retrieval.embed
	$(PYTHON) -m src.cinemind.retrieval.graph

demo:
	$(PYTHON) -m src.cinemind.server

record:
	$(PYTHON) scripts/record_traces.py

eval:
	$(PYTHON) -m src.cinemind.eval.run
	$(PYTHON) -m src.cinemind.eval.report

verify:
	$(PYTHON) scripts/verify.py

test:
	$(PYTEST) tests/ -v --cov=src/cinemind

clean:
	rm -rf data/processed/* demo/traces/*.tmp .pytest_cache .coverage
