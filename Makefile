# =============================================================================
# Kraionyx - Medical STT & EHR Integration System
# =============================================================================
# Usage: make help
# =============================================================================

.DEFAULT_GOAL := help
SHELL := /bin/bash

# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------
COMPOSE_FULL   := docker compose -f deploy/docker-compose.yml
COMPOSE_INFRA  := docker compose -f deploy/docker-compose.infra.yml
GO_SERVICES    := services/api-gateway services/fhir-adapter
PYTHON_SERVICES := services/audio-processor services/stt-engine services/clinical-nlp

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

.PHONY: help
help: ## Show this help message
	@echo ""
	@echo "  Kraionyx — Medical STT & EHR Integration System"
	@echo "  ================================================"
	@echo ""
	@echo "  Usage: make <target>"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ---------------------------------------------------------------------------
# Infrastructure
# ---------------------------------------------------------------------------

.PHONY: infra-up
infra-up: ## Start infrastructure services (Kafka, Redis, Kafka UI)
	$(COMPOSE_INFRA) up -d
	@echo ""
	@echo "Infrastructure is starting..."
	@echo "  Kafka UI: http://localhost:8080"
	@echo "  Kafka:    localhost:9094"
	@echo "  Redis:    localhost:6379"

.PHONY: infra-down
infra-down: ## Stop infrastructure services
	$(COMPOSE_INFRA) down

.PHONY: infra-logs
infra-logs: ## Tail infrastructure logs
	$(COMPOSE_INFRA) logs -f

# ---------------------------------------------------------------------------
# Full Stack
# ---------------------------------------------------------------------------

.PHONY: up
up: ## Start the full stack (build + launch all services)
	$(COMPOSE_FULL) up -d --build

.PHONY: down
down: ## Stop the full stack and remove volumes
	$(COMPOSE_FULL) down -v

.PHONY: logs
logs: ## Tail all service logs
	$(COMPOSE_FULL) logs -f

.PHONY: ps
ps: ## Show running containers
	$(COMPOSE_FULL) ps

# ---------------------------------------------------------------------------
# Kafka Topics
# ---------------------------------------------------------------------------

.PHONY: topics
topics: ## Create all Kafka topics (idempotent)
	@bash scripts/create-kafka-topics.sh

# ---------------------------------------------------------------------------
# TLS Certificates
# ---------------------------------------------------------------------------

.PHONY: certs
certs: ## Generate TLS dev certificates using mkcert
	@bash scripts/generate-certs.sh

# ---------------------------------------------------------------------------
# Build (Go services)
# ---------------------------------------------------------------------------

.PHONY: build-gateway
build-gateway: ## Build the API Gateway binary
	cd services/api-gateway && go build -o bin/api-gateway ./cmd/server

.PHONY: build-fhir
build-fhir: ## Build the FHIR Adapter binary
	cd services/fhir-adapter && go build -o bin/fhir-adapter ./cmd/adapter

.PHONY: build
build: build-gateway build-fhir ## Build all Go service binaries

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------

.PHONY: test-go
test-go: ## Run Go tests for all Go services
	@for svc in $(GO_SERVICES); do \
		echo "=== Testing $$svc ==="; \
		cd $$svc && go test -v -race -coverprofile=cover.out ./... && cd - > /dev/null; \
	done

.PHONY: test-python
test-python: ## Run pytest for all Python services
	@for svc in $(PYTHON_SERVICES); do \
		echo "=== Testing $$svc ==="; \
		if [ -d "$$svc" ]; then \
			cd $$svc && python -m pytest -v --tb=short tests/ && cd - > /dev/null; \
		else \
			echo "  [SKIP] $$svc not found"; \
		fi; \
	done

.PHONY: test
test: test-go test-python ## Run all tests (Go + Python)

# ---------------------------------------------------------------------------
# QA & Chaos Testing
# ---------------------------------------------------------------------------

.PHONY: test-qa-load
test-qa-load: ## Run the QA load tests against API Gateway
	@echo "=== Running API Gateway Load Tests ==="
	cd tests/qa/load && go run main.go -c 50 -d 5s

.PHONY: test-qa-chaos
test-qa-chaos: ## Run the Chaos engineering tests (requires running infra)
	@echo "=== Running Chaos Engineering Tests ==="
	@bash tests/qa/chaos/chaos_test.sh

.PHONY: test-qa-fuzz
test-qa-fuzz: ## Run Go fuzzing tests on API gateway
	@echo "=== Running Go Fuzzing Tests ==="
	cd services/api-gateway/internal/handler && go test -fuzz=Fuzz -fuzztime=10s

.PHONY: generate-qa-data
generate-qa-data: ## Generate synthetic clinical data for testing
	@echo "=== Generating Synthetic Clinical Data ==="
	cd tests/qa/data_generator && python generate_clinical_data.py

.PHONY: test-qa
test-qa: test-qa-load test-qa-fuzz test-qa-chaos ## Run the entire QA testing suite

# ---------------------------------------------------------------------------
# Linting
# ---------------------------------------------------------------------------

.PHONY: lint-go
lint-go: ## Run Go linter (golangci-lint)
	@for svc in $(GO_SERVICES); do \
		echo "=== Linting $$svc ==="; \
		cd $$svc && golangci-lint run ./... && cd - > /dev/null; \
	done

.PHONY: lint-python
lint-python: ## Run Python linter (ruff)
	@for svc in $(PYTHON_SERVICES); do \
		echo "=== Linting $$svc ==="; \
		if [ -d "$$svc" ]; then \
			ruff check $$svc; \
		else \
			echo "  [SKIP] $$svc not found"; \
		fi; \
	done

.PHONY: lint
lint: lint-go lint-python ## Run all linters

# ---------------------------------------------------------------------------
# Protobuf
# ---------------------------------------------------------------------------

.PHONY: proto
proto: ## Generate Go code from protobuf definitions
	@echo "Generating protobuf code..."
	@mkdir -p shared/gen
	protoc \
		--proto_path=proto \
		--go_out=shared/gen --go_opt=paths=source_relative \
		--go-grpc_out=shared/gen --go-grpc_opt=paths=source_relative \
		proto/kraionyx/v1/*.proto
	@echo "Protobuf generation complete."

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

.PHONY: clean
clean: ## Remove binaries, caches, and build artifacts
	@echo "Cleaning build artifacts..."
	@for svc in $(GO_SERVICES); do \
		rm -rf $$svc/bin; \
		rm -f $$svc/cover.out; \
	done
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf shared/gen
	@echo "Clean complete."

# ---------------------------------------------------------------------------
# Setup (first-time onboarding)
# ---------------------------------------------------------------------------

.PHONY: setup
setup: certs infra-up ## First-time setup: generate certs, start infra, create topics
	@echo ""
	@echo "Waiting for Kafka to become healthy..."
	@sleep 10
	@$(MAKE) topics
	@echo ""
	@echo "============================================"
	@echo "  Kraionyx setup complete!"
	@echo "============================================"
	@echo ""
	@echo "  Next steps:"
	@echo "    1. Copy .env.example to .env and configure"
	@echo "    2. Run 'make up' to start all services"
	@echo "    3. Visit Kafka UI at http://localhost:8080"
	@echo ""
