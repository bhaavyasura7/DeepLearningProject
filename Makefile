.PHONY: setup models data index scenarios demo record eval bakeoff verify test doctor all clean

PYTHON = .venv/bin/python
PYTEST = .venv/bin/pytest
MODEL = $(shell grep -m1 '^  model:' config.yaml | sed 's/.*"\(.*\)"/\1/')
EMBED_MODEL = $(shell grep -m1 'embedding_model:' config.yaml | sed 's/.*"\(.*\)"/\1/')

setup:
	@if [ ! -d ".venv" ]; then uv venv --python 3.11 .venv; fi
	uv pip install -r requirements.txt --python .venv

# Pull the language model and the embedding model into Ollama
models:
	ollama pull $(MODEL)
	ollama pull $(EMBED_MODEL)

# Download MovieLens 32M, fetch TMDB metadata (TMDB_API_KEY in .env), build the catalog
data:
	$(PYTHON) -m src.cinemind.data.build_catalog

# Embed the catalog with nomic-embed-text and build the knowledge graph
index:
	$(PYTHON) -m src.cinemind.retrieval.embed
	$(PYTHON) -m src.cinemind.retrieval.graph

# Bind feed / cold-start scenarios to real MovieLens viewers
scenarios:
	$(PYTHON) scripts/pick_scenario_users.py

demo:
	$(PYTHON) -m src.cinemind.server

# Run every scenario against the real model (vector + hybrid) and save replay traces
record:
	$(PYTHON) scripts/record_traces.py

# Real-viewer cold-start evaluation: split, 200 viewers x 3 configs, all-viewer Recall@50, report
eval:
	$(PYTHON) -m src.cinemind.eval.split
	$(PYTHON) -m src.cinemind.eval.run
	$(PYTHON) -m src.cinemind.eval.recall
	$(PYTHON) -m src.cinemind.eval.report

bakeoff:
	$(PYTHON) scripts/bakeoff.py

verify:
	$(PYTHON) scripts/verify.py

test:
	$(PYTEST) tests/ -v --cov=src/cinemind

clean:
	rm -rf data/processed/* demo/traces/*.tmp .pytest_cache .coverage

# Plain-English checklist of what's ready and what to run next
doctor:
	$(PYTHON) scripts/doctor.py

# Everything after setup, in order (long: MovieLens download, TMDB fetch, embeddings, AI runs)
all: models data index scenarios record eval
