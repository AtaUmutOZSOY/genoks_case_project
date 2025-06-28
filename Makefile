# Genoks Multi-tenant API Makefile
# Provides convenient commands for development, testing, and deployment

.PHONY: help test test-unit test-integration test-security test-performance test-tenant test-all test-coverage test-report lint format setup-dev setup-test build run clean docker-build docker-up docker-down migrate shell

# Default target
help:
	@echo "Genoks Multi-tenant API Development Commands"
	@echo "============================================="
	@echo ""
	@echo "Testing Commands:"
	@echo "  test              - Run all tests"
	@echo "  test-unit         - Run unit tests only"
	@echo "  test-integration  - Run integration tests only"
	@echo "  test-security     - Run security tests only"
	@echo "  test-performance  - Run performance tests only"
	@echo "  test-tenant       - Run tenant-specific tests only"
	@echo "  test-coverage     - Run tests with coverage report"
	@echo "  test-report       - Generate comprehensive test report"
	@echo "  test-failed       - Re-run only failed tests"
	@echo ""
	@echo "Code Quality Commands:"
	@echo "  lint              - Run all linting checks"
	@echo "  format            - Format code with black and isort"
	@echo "  format-check      - Check code formatting without changes"
	@echo ""
	@echo "Development Commands:"
	@echo "  setup-dev         - Setup development environment"
	@echo "  setup-test        - Setup test environment"
	@echo "  migrate           - Run database migrations"
	@echo "  shell             - Open Django shell"
	@echo "  run               - Run development server"
	@echo ""
	@echo "Docker Commands:"
	@echo "  docker-build      - Build Docker images"
	@echo "  docker-up         - Start Docker containers"
	@echo "  docker-down       - Stop Docker containers"
	@echo "  docker-logs       - View Docker logs"
	@echo ""
	@echo "Utility Commands:"
	@echo "  clean             - Clean temporary files"
	@echo "  build             - Build project for production"

# Testing Commands
test:
	python scripts/run_tests.py all --verbose

test-unit:
	python scripts/run_tests.py unit --verbose

test-integration:
	python scripts/run_tests.py integration --verbose

test-security:
	python scripts/run_tests.py security --verbose

test-performance:
	python scripts/run_tests.py performance --verbose

test-tenant:
	python scripts/run_tests.py tenant --verbose

test-coverage:
	python scripts/run_tests.py all --coverage --verbose

test-report:
	python scripts/run_tests.py report

test-failed:
	python scripts/run_tests.py failed --verbose

test-ci:
	python scripts/run_tests.py ci

# Code Quality Commands
lint:
	python scripts/run_tests.py lint

format:
	black .
	isort .
	@echo "✅ Code formatting completed!"

format-check:
	black --check --diff .
	isort --check-only --diff .
	@echo "✅ Code formatting check completed!"

# Development Commands
setup-dev:
	@echo "🛠️ Setting up development environment..."
	pip install -r requirements.txt
	python manage.py migrate
	@echo "✅ Development environment setup completed!"

setup-test:
	python scripts/run_tests.py setup

migrate:
	python manage.py migrate

makemigrations:
	python manage.py makemigrations

shell:
	python manage.py shell

run:
	python manage.py runserver 0.0.0.0:8000

collectstatic:
	python manage.py collectstatic --noinput

# Docker Commands
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-restart:
	docker-compose restart

docker-shell:
	docker-compose exec web python manage.py shell

docker-migrate:
	docker-compose exec web python manage.py migrate

docker-test:
	docker-compose exec web python scripts/run_tests.py all --verbose

# Production Commands
build:
	@echo "🏗️ Building project for production..."
	pip install -r requirements.txt
	python manage.py collectstatic --noinput
	python manage.py migrate
	@echo "✅ Production build completed!"

# Utility Commands
clean:
	@echo "🧹 Cleaning temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf test_report.html
	rm -rf test_results.xml
	rm -rf coverage.json
	rm -rf dist/
	rm -rf build/
	@echo "✅ Cleanup completed!"

# Database Commands
reset-db:
	@echo "⚠️ Resetting database..."
	python manage.py flush --noinput
	python manage.py migrate
	@echo "✅ Database reset completed!"

create-superuser:
	python manage.py createsuperuser

# Security Commands
check-security:
	python manage.py check --deploy
	safety check
	bandit -r apps/ utils/ middleware/

# Documentation Commands
docs-build:
	@echo "📚 Building documentation..."
	# Add documentation build commands here
	@echo "✅ Documentation build completed!"

# CI/CD Commands
ci-test:
	make test-ci

ci-lint:
	make lint

ci-security:
	make check-security

ci-build:
	make build

# Quick development workflow
dev: format lint test
	@echo "✅ Development workflow completed!"

# Full CI workflow
ci: ci-lint ci-security ci-test ci-build
	@echo "✅ CI workflow completed!"

# Environment-specific commands
dev-server:
	DJANGO_SETTINGS_MODULE=config.settings.development python manage.py runserver

prod-server:
	DJANGO_SETTINGS_MODULE=config.settings.production gunicorn config.wsgi:application

test-server:
	DJANGO_SETTINGS_MODULE=config.settings.testing python manage.py runserver

# Backup and restore commands
backup-db:
	@echo "💾 Creating database backup..."
	pg_dump $(DATABASE_URL) > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✅ Database backup completed!"

# Load test data
load-fixtures:
	python manage.py loaddata fixtures/*.json

# Performance monitoring
profile:
	python -m cProfile -o profile_output.prof manage.py runserver --noreload

# Code analysis
analyze:
	prospector apps/ utils/ middleware/
	pylint apps/ utils/ middleware/

# Update dependencies
update-deps:
	pip-compile requirements.in
	pip install -r requirements.txt 