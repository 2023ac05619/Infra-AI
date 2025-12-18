# InfraAI Makefile

.PHONY: help install run-api run-worker test lint format clean docker-build docker-up docker-down

help:
	@echo "InfraAI Backend - Available Commands:"
	@echo ""
	@echo "  make install      - Install dependencies"
	@echo "  make run-api      - Run API server"
	@echo "  make run-worker   - Run background worker"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linters"
	@echo "  make format       - Format code"
	@echo "  make clean        - Clean cache files"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-up    - Start all services"
	@echo "  make docker-down  - Stop all services"
	@echo ""

install:
	pip install -r requirements.txt

run-api:
	python -m app.main

run-worker:
	python -m app.worker

test:
	@echo "Running tests..."
	pytest tests/ -v

lint:
	@echo "Running linters..."
	ruff check app/
	mypy app/

format:
	@echo "Formatting code..."
	ruff format app/

clean:
	@echo "Cleaning cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete

docker-build:
	docker build -t infraai-backend:latest .

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

db-migrate:
	@echo "Running database migrations..."
	python -c "import asyncio; from app.db import init_db; asyncio.run(init_db())"

db-backup:
	@echo "Backing up database..."
	pg_dump -U infraal -F c infraal > backup_$(shell date +%Y%m%d_%H%M%S).dump
