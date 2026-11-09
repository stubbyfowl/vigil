PY := .venv/bin/python
PORT ?= 8000

.PHONY: setup dev demo build data eval test lint

setup:
	test -d .venv || python3.12 -m venv .venv
	.venv/bin/pip install -q -r backend/requirements.txt
	cd frontend && npm ci

# Backend on :8000, Vite on :5173. Open http://localhost:5173
dev:
	@trap 'kill 0' INT TERM EXIT; \
	(cd backend && ../$(PY) -m uvicorn app.main:app --port $(PORT) --reload) & \
	(cd frontend && npm run dev) & \
	wait

build:
	cd frontend && npm run build

# One port, built frontend, Demo Director plays on load.
demo: build
	$(PY) scripts/demo_director.py serve --port $(PORT)

data:
	$(PY) scripts/generate_data.py

eval:
	$(PY) scripts/evaluate_detector.py

test:
	cd backend && ../$(PY) -m pytest -q
	cd frontend && npm test

lint:
	.venv/bin/ruff check backend scripts
	cd backend && ../.venv/bin/mypy app
	cd frontend && npm run lint && npx tsc --noEmit
