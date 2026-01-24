#!/bin/bash
# Setup script for Sales Forecasting application

set -e

echo "Setting up Sales Forecasting application..."

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed. Aborting." >&2; exit 1; }
command -v docker-compose >/dev/null 2>&1 || command -v docker >/dev/null 2>&1 || { echo "Docker Compose is required. Aborting." >&2; exit 1; }

# Navigate to project root
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

echo "Project root: $PROJECT_ROOT"

# Start infrastructure services
echo "Starting infrastructure services (PostgreSQL, Redis, MinIO)..."
docker-compose up -d postgres redis minio

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10

# Setup backend
echo "Setting up backend..."
cd "$PROJECT_ROOT/backend"

if [ -f ".env" ]; then
    echo ".env file already exists, skipping..."
else
    echo "Creating .env file from example..."
    cp .env.example .env
fi

if command -v poetry >/dev/null 2>&1; then
    echo "Installing Python dependencies with Poetry..."
    poetry install

    echo "Running database migrations..."
    poetry run alembic upgrade head
else
    echo "Poetry not found. Please install Poetry and run:"
    echo "  cd backend && poetry install && poetry run alembic upgrade head"
fi

# Setup frontend
echo "Setting up frontend..."
cd "$PROJECT_ROOT/frontend"

if command -v npm >/dev/null 2>&1; then
    echo "Installing Node.js dependencies..."
    npm install
else
    echo "npm not found. Please install Node.js and run:"
    echo "  cd frontend && npm install"
fi

echo ""
echo "Setup complete!"
echo ""
echo "To start the development servers:"
echo ""
echo "  Backend:  cd backend && poetry run uvicorn app.main:app --reload"
echo "  Frontend: cd frontend && npm run dev"
echo ""
echo "Or start everything with Docker:"
echo "  docker-compose up"
echo ""
echo "Access the application:"
echo "  Frontend:           http://localhost:3000"
echo "  Backend API:        http://localhost:8000"
echo "  GraphQL Playground: http://localhost:8000/api/graphql"
echo "  API Docs:           http://localhost:8000/api/docs"
