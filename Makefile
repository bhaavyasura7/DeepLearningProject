.PHONY: help install test lint run-backend run-worker run-frontend run-experiments db-migrate db-seed demo

help:
	@echo "Available commands:"
	@echo "  make install         - Install backend and frontend dependencies"
	@echo "  make db-migrate      - Run database migrations"
	@echo "  make db-seed         - Seed MovieLens dataset"
	@echo "  make test            - Run all backend and research tests"
	@echo "  make lint            - Run ruff linter on backend"
	@echo "  make run-backend     - Start FastAPI backend on http://localhost:8000"
	@echo "  make run-worker      - Start asynchronous background agent worker"
	@echo "  make run-frontend    - Start Next.js frontend on http://localhost:3000"
	@echo "  make run-experiments- Run full benchmark evaluation & ablation study"
	@echo "  make demo            - Seed demonstration user and initial interactions"

install:
	pip install -r backend/requirements.txt
	cd frontend && npm install

db-migrate:
	cd backend && alembic upgrade head

db-seed:
	python3 -m app.scripts.import_movielens --csv_path ../data/raw/ml-latest-small/movies.csv

test:
	cd backend && pytest -v

lint:
	ruff check backend research

run-backend:
	cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

run-worker:
	cd backend && python3 -m app.worker

run-frontend:
	cd frontend && npm run dev

run-experiments:
	python3 research/prepare_split.py
	PYTHONPATH=. python3 research/run_experiments.py

demo:
	PYTHONPATH=backend python3 backend/app/scripts/seed_demo.py
