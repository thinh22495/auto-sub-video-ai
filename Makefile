.PHONY: build up down logs restart clean setup dev

# Build Docker images
build:
	docker compose build

# Start all services (GPU)
up:
	docker compose up -d

# Start all services (CPU only)
up-cpu:
	docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d

# Stop all services
down:
	docker compose down

# View logs
logs:
	docker compose logs -f

# View logs for specific service
logs-app:
	docker compose logs -f autosub-app

logs-ollama:
	docker compose logs -f autosub-ollama

# Restart services
restart:
	docker compose restart

# Clean everything (containers, volumes, images)
clean:
	docker compose down -v --rmi local

# First-time setup: copy env and download models
setup:
	cp -n .env.example .env || true
	mkdir -p data/videos data/subtitles data/output data/models data/db data/ollama
	$(MAKE) build
	$(MAKE) up
	@echo ""
	@echo "AutoSubAI is starting up..."
	@echo "Access the web UI at http://localhost:$${AUTOSUB_PORT:-8080}"
	@echo ""
	@echo "To download the default translation model, run:"
	@echo "  docker compose exec autosub-app bash scripts/setup_models.sh"

# Development: run backend locally (requires Python 3.12 + Redis)
dev-backend:
	cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Development: run frontend locally
dev-frontend:
	cd frontend && npm run dev

# Health check
health:
	@curl -sf http://localhost:$${AUTOSUB_PORT:-8080}/api/health | python3 -m json.tool || echo "API is not running"
