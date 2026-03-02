"""Application configuration using Pydantic Settings."""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Sales Forecasting API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    API_PREFIX: str = "/api"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "sales_forecasting"
    DATABASE_URL: str | None = None
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None
    REDIS_DB: int = 0
    REDIS_URL: str | None = None

    # Celery
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None

    # MLflow
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"
    MLFLOW_EXPERIMENT_NAME: str = "sales-forecasting"

    # S3/MinIO
    S3_ENDPOINT_URL: str | None = None
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None
    S3_BUCKET_NAME: str = "sales-forecasting-artifacts"
    S3_REGION: str = "us-east-1"

    # DVC
    DVC_REMOTE_URL: str | None = None
    DVC_REMOTE_NAME: str = "minio"

    # Apache Airflow
    AIRFLOW_BASE_URL: str = "http://localhost:8080"
    AIRFLOW_API_URL: str = "http://localhost:8080/api/v1"
    AIRFLOW_USERNAME: str = "admin"
    AIRFLOW_PASSWORD: str = "admin"

    # Feast Feature Store
    FEAST_REPO_PATH: str = "/app/feast_repo"
    FEAST_SERVER_URL: str = "http://localhost:6566"
    FEAST_ONLINE_STORE_TYPE: str = "redis"
    FEAST_OFFLINE_STORE_TYPE: str = "postgres"

    # Prometheus Monitoring
    PROMETHEUS_URL: str = "http://localhost:9090"
    PROMETHEUS_PUSHGATEWAY_URL: str | None = None
    METRICS_EXPORTER_PORT: int = 8001

    # Grafana
    GRAFANA_URL: str = "http://localhost:3001"
    GRAFANA_API_KEY: str | None = None

    # Alertmanager
    ALERTMANAGER_URL: str = "http://localhost:9093"

    # Quality Gates Configuration
    QUALITY_GATE_MAPE_IMPROVEMENT: float = 2.0  # Percentage improvement required
    QUALITY_GATE_MAX_MAPE: float = 0.15  # Maximum absolute MAPE threshold
    QUALITY_GATE_DRIFT_P_VALUE: float = 0.05  # Drift detection threshold
    QUALITY_GATE_MAX_LATENCY_MS: float = 500.0  # P99 latency threshold
    QUALITY_GATE_MIN_GE_SUCCESS: float = 0.95  # Great Expectations success rate

    # Model Registry
    MODEL_REGISTRY_STAGE_STAGING: str = "Staging"
    MODEL_REGISTRY_STAGE_PRODUCTION: str = "Production"
    MODEL_REGISTRY_STAGE_ARCHIVED: str = "Archived"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60

    # Data Storage
    DATA_UPLOAD_DIR: str = "/tmp/sales_forecasting/uploads"

    @model_validator(mode="after")
    def assemble_db_url(self) -> "Settings":
        """Assemble database URL from components if not provided."""
        if self.DATABASE_URL is None:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        return self

    @model_validator(mode="after")
    def assemble_redis_url(self) -> "Settings":
        """Assemble Redis URL from components if not provided."""
        if self.REDIS_URL is None:
            if self.REDIS_PASSWORD:
                self.REDIS_URL = (
                    f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
                )
            else:
                self.REDIS_URL = f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return self

    @model_validator(mode="after")
    def assemble_celery_urls(self) -> "Settings":
        """Assemble Celery broker and result backend URLs."""
        if self.CELERY_BROKER_URL is None:
            self.CELERY_BROKER_URL = self.REDIS_URL
        if self.CELERY_RESULT_BACKEND is None:
            self.CELERY_RESULT_BACKEND = self.REDIS_URL
        return self

    @property
    def sync_database_url(self) -> str:
        """Get synchronous database URL for Alembic."""
        if self.DATABASE_URL:
            return self.DATABASE_URL.replace("+asyncpg", "")
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
