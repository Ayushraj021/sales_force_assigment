# Sales Forecasting & Marketing Mix Modeling (MMM)

A production-grade web application for **demand forecasting**, **sales prediction**, and **Marketing Mix Modeling (MMM)** to support data-driven business decisions.

## Features

- **Marketing Mix Modeling (MMM)**
  - Bayesian MMM with PyMC-Marketing
  - Custom Ridge/ElasticNet MMM
  - Adstock transformations (Geometric, Weibull, Delayed)
  - Saturation curves (Hill, Logistic, Michaelis-Menten)
  - Channel contribution decomposition

- **Demand Forecasting**
  - Prophet time series forecasting
  - ARIMA/SARIMA models
  - Ensemble forecasting
  - Multi-variate forecasting with regressors

- **Budget Optimization**
  - Constraint-based optimization
  - ROI and marginal ROI analysis
  - What-if scenario analysis
  - Multi-period planning

- **Enterprise Features**
  - Multi-tenant support
  - Role-based access control (RBAC)
  - Audit logging
  - MLflow experiment tracking
  - Scheduled reports

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.11+, FastAPI, Strawberry GraphQL |
| **Database** | PostgreSQL 16 + TimescaleDB |
| **Cache** | Redis 7 |
| **Frontend** | React 18, TanStack Router/Query, Zustand, Tailwind CSS |
| **ML/Data** | PyMC-Marketing, Prophet, scikit-learn, MLflow |
| **Task Queue** | Celery + Redis |
| **Storage** | S3/MinIO |

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Node.js 20+
- Poetry (Python package manager)

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd sales_forecasting
   ```

2. **Start the development environment**
   ```bash
   docker-compose up -d
   ```

3. **Set up the backend**
   ```bash
   cd backend
   cp .env.example .env
   poetry install
   poetry run alembic upgrade head
   poetry run uvicorn app.main:app --reload
   ```

4. **Set up the frontend**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

5. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - GraphQL Playground: http://localhost:8000/api/graphql
   - MLflow UI: http://localhost:5000

### Running Tests

```bash
# Backend tests
cd backend
poetry run pytest

# Frontend tests
cd frontend
npm run test
```

## Project Structure

```
sales_forecasting/
├── backend/
│   ├── app/
│   │   ├── api/              # REST and GraphQL endpoints
│   │   ├── core/             # Security, config, exceptions
│   │   ├── infrastructure/   # Database, cache, external APIs
│   │   ├── ml/               # ML models and transformers
│   │   │   ├── models/       # MMM, forecasting models
│   │   │   ├── transformers/ # Adstock, saturation
│   │   │   └── optimization/ # Budget optimization
│   │   └── workers/          # Celery tasks
│   ├── alembic/              # Database migrations
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── routes/           # TanStack Router pages
│   │   ├── features/         # Feature modules
│   │   ├── components/       # Reusable components
│   │   └── stores/           # Zustand state
│   └── public/
├── docker-compose.yml
└── README.md
```

## API Documentation

### GraphQL Schema

The API is primarily GraphQL-based. Access the interactive playground at `/api/graphql` when running in development mode.

### Key Mutations

- `register` / `login` - Authentication
- `createDataset` - Upload and create datasets
- `createModel` - Create MMM or forecasting models
- `trainModel` - Train a model (async)
- `runOptimization` - Run budget optimization

### Key Queries

- `me` - Current user
- `models` - List models
- `experiments` - List experiments
- `budgetScenarios` - List optimization scenarios

## Environment Variables

See `.env.example` for all available configuration options.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

MIT License
