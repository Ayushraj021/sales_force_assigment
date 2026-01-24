# Sales Forecasting MLOps Makefile
# Convenience commands for development and production operations

.PHONY: help install dev-up dev-down mlops-up mlops-down mlops-init \
        trigger-pipeline trigger-training trigger-deploy trigger-retrain \
        airflow-ui grafana-ui mlflow-ui prometheus-ui \
        logs-backend logs-airflow logs-worker \
        test lint format clean db-migrate feast-apply dvc-push

# Default target
help:
	@echo "Sales Forecasting MLOps Commands"
	@echo "================================="
	@echo ""
	@echo "Development:"
	@echo "  make install          - Install backend dependencies"
	@echo "  make dev-up           - Start development services"
	@echo "  make dev-down         - Stop development services"
	@echo "  make test             - Run tests"
	@echo "  make lint             - Run linter"
	@echo "  make format           - Format code"
	@echo ""
	@echo "MLOps Stack:"
	@echo "  make mlops-init       - Initialize MLOps services (first time setup)"
	@echo "  make mlops-up         - Start all MLOps services"
	@echo "  make mlops-down       - Stop all MLOps services"
	@echo "  make mlops-restart    - Restart all MLOps services"
	@echo ""
	@echo "Pipeline Triggers:"
	@echo "  make trigger-pipeline - Trigger full ML pipeline"
	@echo "  make trigger-training - Trigger training only"
	@echo "  make trigger-deploy   - Trigger deployment only"
	@echo "  make trigger-retrain  - Trigger retraining (drift response)"
	@echo ""
	@echo "Web UIs:"
	@echo "  make airflow-ui       - Open Airflow UI (localhost:8080)"
	@echo "  make grafana-ui       - Open Grafana dashboards (localhost:3001)"
	@echo "  make mlflow-ui        - Open MLflow UI (localhost:5000)"
	@echo "  make prometheus-ui    - Open Prometheus UI (localhost:9090)"
	@echo ""
	@echo "Logs:"
	@echo "  make logs-backend     - View backend logs"
	@echo "  make logs-airflow     - View Airflow logs"
	@echo "  make logs-worker      - View Celery worker logs"
	@echo ""
	@echo "Database & Storage:"
	@echo "  make db-migrate       - Run database migrations"
	@echo "  make feast-apply      - Apply Feast feature definitions"
	@echo "  make dvc-push         - Push data to DVC remote"

# ============================================
# INSTALLATION & SETUP
# ============================================

install:
	cd backend && poetry install

dev-up:
	docker-compose up -d
	@echo "Development services started"
	@echo "  Backend API: http://localhost:8000"
	@echo "  Frontend: http://localhost:3000"
	@echo "  MLflow: http://localhost:5000"

dev-down:
	docker-compose down
	@echo "Development services stopped"

# ============================================
# MLOPS STACK
# ============================================

mlops-init:
	@echo "Initializing MLOps stack (first time setup)..."
	docker-compose -f docker-compose.yml -f docker-compose.mlops.yml --profile init up -d postgres redis minio
	@echo "Waiting for databases to be ready..."
	sleep 10
	docker-compose -f docker-compose.yml -f docker-compose.mlops.yml --profile init run --rm postgres-init-airflow || true
	docker-compose -f docker-compose.yml -f docker-compose.mlops.yml --profile init run --rm minio-init
	docker-compose -f docker-compose.yml -f docker-compose.mlops.yml --profile init run --rm airflow-init
	@echo "MLOps initialization complete!"

mlops-up:
	docker-compose -f docker-compose.yml -f docker-compose.mlops.yml up -d
	@echo "MLOps services started"
	@echo ""
	@echo "Services available at:"
	@echo "  Backend API:   http://localhost:8000"
	@echo "  Frontend:      http://localhost:3000"
	@echo "  Airflow:       http://localhost:8080 (admin/admin)"
	@echo "  MLflow:        http://localhost:5000"
	@echo "  Grafana:       http://localhost:3001 (admin/admin)"
	@echo "  Prometheus:    http://localhost:9090"
	@echo "  Alertmanager:  http://localhost:9093"
	@echo "  Feast Server:  http://localhost:6566"
	@echo "  MinIO Console: http://localhost:9001 (minioadmin/minioadmin)"

mlops-down:
	docker-compose -f docker-compose.yml -f docker-compose.mlops.yml down
	@echo "MLOps services stopped"

mlops-restart:
	$(MAKE) mlops-down
	$(MAKE) mlops-up

mlops-status:
	docker-compose -f docker-compose.yml -f docker-compose.mlops.yml ps

# ============================================
# PIPELINE TRIGGERS
# ============================================

API_URL ?= http://localhost:8000

trigger-pipeline:
	@echo "Triggering full ML pipeline..."
	curl -X POST $(API_URL)/api/v1/mlops/pipeline/trigger \
		-H "Content-Type: application/json" \
		-d '{"pipeline_type": "full", "model_types": ["prophet", "arima", "pymc_mmm"], "auto_deploy": true}'
	@echo ""

trigger-training:
	@echo "Triggering training pipeline..."
	curl -X POST $(API_URL)/api/v1/mlops/pipeline/trigger \
		-H "Content-Type: application/json" \
		-d '{"pipeline_type": "training", "model_types": ["prophet", "arima", "pymc_mmm"], "auto_deploy": false}'
	@echo ""

trigger-deploy:
	@echo "Triggering deployment pipeline..."
	curl -X POST $(API_URL)/api/v1/mlops/pipeline/trigger \
		-H "Content-Type: application/json" \
		-d '{"pipeline_type": "deploy", "auto_deploy": true}'
	@echo ""

trigger-retrain:
	@echo "Triggering retraining pipeline (drift response)..."
	curl -X POST $(API_URL)/api/v1/mlops/pipeline/trigger \
		-H "Content-Type: application/json" \
		-d '{"pipeline_type": "retrain", "trigger_source": "drift_alert", "auto_deploy": true}'
	@echo ""

# Get pipeline status
pipeline-status:
	@echo "Getting pipeline run status..."
	@read -p "Enter run_id: " run_id; \
	curl -s $(API_URL)/api/v1/mlops/pipeline/status/$$run_id | python -m json.tool

# ============================================
# WEB UIs
# ============================================

airflow-ui:
	@echo "Opening Airflow UI..."
	@which xdg-open > /dev/null && xdg-open http://localhost:8080 || \
	which open > /dev/null && open http://localhost:8080 || \
	echo "Visit http://localhost:8080 (credentials: admin/admin)"

grafana-ui:
	@echo "Opening Grafana UI..."
	@which xdg-open > /dev/null && xdg-open http://localhost:3001 || \
	which open > /dev/null && open http://localhost:3001 || \
	echo "Visit http://localhost:3001 (credentials: admin/admin)"

mlflow-ui:
	@echo "Opening MLflow UI..."
	@which xdg-open > /dev/null && xdg-open http://localhost:5000 || \
	which open > /dev/null && open http://localhost:5000 || \
	echo "Visit http://localhost:5000"

prometheus-ui:
	@echo "Opening Prometheus UI..."
	@which xdg-open > /dev/null && xdg-open http://localhost:9090 || \
	which open > /dev/null && open http://localhost:9090 || \
	echo "Visit http://localhost:9090"

minio-ui:
	@echo "Opening MinIO Console..."
	@which xdg-open > /dev/null && xdg-open http://localhost:9001 || \
	which open > /dev/null && open http://localhost:9001 || \
	echo "Visit http://localhost:9001 (credentials: minioadmin/minioadmin)"

# ============================================
# LOGS
# ============================================

logs-backend:
	docker-compose -f docker-compose.yml -f docker-compose.mlops.yml logs -f backend

logs-airflow:
	docker-compose -f docker-compose.yml -f docker-compose.mlops.yml logs -f airflow-webserver airflow-scheduler airflow-worker

logs-worker:
	docker-compose -f docker-compose.yml -f docker-compose.mlops.yml logs -f celery_worker

logs-all:
	docker-compose -f docker-compose.yml -f docker-compose.mlops.yml logs -f

# ============================================
# DATABASE & STORAGE
# ============================================

db-migrate:
	cd backend && poetry run alembic upgrade head

db-revision:
	@read -p "Enter migration message: " msg; \
	cd backend && poetry run alembic revision --autogenerate -m "$$msg"

feast-apply:
	docker-compose -f docker-compose.yml -f docker-compose.mlops.yml exec feast-server feast apply

dvc-push:
	cd mlops/dvc && dvc push

dvc-pull:
	cd mlops/dvc && dvc pull

# ============================================
# TESTING & CODE QUALITY
# ============================================

test:
	cd backend && poetry run pytest tests/ -v

test-ml:
	cd backend && poetry run pytest tests/ml/ -v

test-coverage:
	cd backend && poetry run pytest tests/ -v --cov=app --cov-report=html

lint:
	cd backend && poetry run ruff check app/
	cd backend && poetry run mypy app/

format:
	cd backend && poetry run black app/ tests/
	cd backend && poetry run ruff check --fix app/

# ============================================
# CLEANUP
# ============================================

clean:
	docker-compose -f docker-compose.yml -f docker-compose.mlops.yml down -v
	rm -rf backend/.pytest_cache
	rm -rf backend/.mypy_cache
	rm -rf backend/.ruff_cache
	rm -rf backend/htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned up all containers, volumes, and cache files"

clean-volumes:
	docker-compose -f docker-compose.yml -f docker-compose.mlops.yml down -v
	@echo "Removed all Docker volumes"

# ============================================
# KUBERNETES DEPLOYMENT
# ============================================

k8s-deploy-staging:
	helm upgrade --install sales-forecasting-staging \
		./mlops/infrastructure/helm/charts/sales-forecasting \
		-f ./mlops/infrastructure/helm/charts/sales-forecasting/values-staging.yaml \
		-n sales-forecasting-staging --create-namespace

k8s-deploy-prod:
	helm upgrade --install sales-forecasting \
		./mlops/infrastructure/helm/charts/sales-forecasting \
		-f ./mlops/infrastructure/helm/charts/sales-forecasting/values-prod.yaml \
		-n sales-forecasting-prod --create-namespace

k8s-rollback:
	@read -p "Enter namespace (staging/prod): " ns; \
	helm rollback sales-forecasting -n sales-forecasting-$$ns

k8s-status:
	@echo "=== Staging ==="
	kubectl get pods -n sales-forecasting-staging 2>/dev/null || echo "Staging namespace not found"
	@echo ""
	@echo "=== Production ==="
	kubectl get pods -n sales-forecasting-prod 2>/dev/null || echo "Production namespace not found"

# ============================================
# MONITORING CHECKS
# ============================================

check-health:
	@echo "Checking service health..."
	@echo "Backend: $$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health || echo 'DOWN')"
	@echo "Airflow: $$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/health || echo 'DOWN')"
	@echo "MLflow:  $$(curl -s -o /dev/null -w '%{http_code}' http://localhost:5000/health || echo 'DOWN')"
	@echo "Prometheus: $$(curl -s -o /dev/null -w '%{http_code}' http://localhost:9090/-/healthy || echo 'DOWN')"
	@echo "Grafana: $$(curl -s -o /dev/null -w '%{http_code}' http://localhost:3001/api/health || echo 'DOWN')"

check-drift:
	@echo "Checking for data drift..."
	curl -s $(API_URL)/api/v1/mlops/drift/check | python -m json.tool

check-model-performance:
	@echo "Getting model performance metrics..."
	curl -s $(API_URL)/api/v1/mlops/models/performance | python -m json.tool
