.PHONY: dev lint test index-build clean doctor

dev:
	docker compose up -d

lint:
	ruff check src/ tests/ traceai/
	ruff format --check src/ tests/ traceai/

test:
	pytest tests/ -v

index-build:
	python scripts/build_reference_index.py

doctor:
	python -m traceai.cli doctor --show-config

clean:
	docker compose down -v
	find . -type d -name "__pycache__" -exec rm -rf {} +
