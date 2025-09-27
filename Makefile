.PHONY: help install test lint clean setup run health-check

# Default target
help:
	@echo "X.com Auto-Reply Service - Available Commands:"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install dependencies"
	@echo "  make setup           Setup credentials and configuration"
	@echo ""
	@echo "Development:"
	@echo "  make test            Run tests"
	@echo "  make lint            Run linting"
	@echo "  make clean           Clean temporary files"
	@echo ""
	@echo "Operations:"
	@echo "  make run             Run the service (dry-run mode)"
	@echo "  make run-prod        Run the service (production mode)"
	@echo "  make health-check    Perform health check"
	@echo "  make status          Show service status"
	@echo ""
	@echo "Maintenance:"
	@echo "  make cleanup         Clean old data and logs"
	@echo "  make backup          Backup configuration and data"

# Installation
install:
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt
	@echo "✅ Dependencies installed"

# Setup
setup:
	@echo "🔧 Setting up X Reply Service..."
	python setup_credentials.py
	@echo "✅ Setup completed"

# Testing
test:
	@echo "🧪 Running tests..."
	python -m pytest tests/ -v
	@echo "✅ Tests completed"

test-coverage:
	@echo "🧪 Running tests with coverage..."
	python -m pytest tests/ --cov=src --cov-report=html --cov-report=term
	@echo "✅ Coverage report generated"

# Linting
lint:
	@echo "🔍 Running linting..."
	python -m flake8 src/ --max-line-length=100 --ignore=E203,W503
	python -m black --check src/
	python -m isort --check-only src/
	@echo "✅ Linting completed"

lint-fix:
	@echo "🔧 Fixing linting issues..."
	python -m black src/
	python -m isort src/
	@echo "✅ Linting issues fixed"

# Cleaning
clean:
	@echo "🧹 Cleaning temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.tmp" -delete
	find . -type f -name "*~" -delete
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	@echo "✅ Cleanup completed"

# Operations
run:
	@echo "🚀 Running X Reply Service (dry-run mode)..."
	python main.py --dry-run --verbose

run-test:
	@echo "🔬 Running X Reply Service (test mode)..."
	python main.py --dry-run --test-mode --verbose

run-prod:
	@echo "🚀 Running X Reply Service (production mode)..."
	python main.py --verbose

health-check:
	@echo "🏥 Performing health check..."
	python health_check.py

status:
	@echo "📊 Checking service status..."
	python main.py --status

# Maintenance
cleanup:
	@echo "🗑️ Cleaning old data and logs..."
	python cleanup.py --days 30

cleanup-dry:
	@echo "🧪 Dry run cleanup (showing what would be cleaned)..."
	python cleanup.py --days 30 --dry-run

backup:
	@echo "💾 Creating backup..."
	@mkdir -p backups
	@tar -czf backups/x-reply-service-backup-$(shell date +%Y%m%d-%H%M%S).tar.gz \
		config/ data/ logs/ --exclude=config/config.yaml
	@echo "✅ Backup created in backups/"

# Development helpers
dev-install:
	@echo "🛠️ Installing development dependencies..."
	pip install -r requirements.txt
	pip install pytest pytest-cov black flake8 isort
	@echo "✅ Development environment ready"

check-config:
	@echo "⚙️ Checking configuration..."
	python -c "from src.x_reply_service.config import validate_config; errors = validate_config(); print('✅ Configuration valid' if not errors else '❌ Configuration errors: ' + str(errors))"

# Docker support (if needed in future)
docker-build:
	@echo "🐳 Building Docker image..."
	docker build -t x-reply-service .

docker-run:
	@echo "🐳 Running Docker container..."
	docker run --rm -v $(PWD)/config:/app/config -v $(PWD)/data:/app/data x-reply-service

# Cron setup helper
install-cron:
	@echo "⏰ Setting up cron job..."
	@echo "Adding hourly cron job for X Reply Service..."
	@(crontab -l 2>/dev/null; echo "0 * * * * cd $(PWD) && python main.py >> logs/cron.log 2>&1") | crontab -
	@echo "✅ Cron job installed (runs every hour)"

remove-cron:
	@echo "⏰ Removing cron job..."
	@crontab -l | grep -v "x-reply-service\|main.py" | crontab -
	@echo "✅ Cron job removed"

# Quick start
quickstart: install setup run-test
	@echo ""
	@echo "🎉 Quick start completed!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Review config/config.yaml and customize as needed"
	@echo "2. Run 'make health-check' to verify everything is working"
	@echo "3. Run 'make run' to test in dry-run mode"
	@echo "4. Run 'make install-cron' to set up automatic hourly execution"
