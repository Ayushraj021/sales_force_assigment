"""File upload endpoints."""

import io
import uuid
from pathlib import Path
from typing import Annotated

import pandas as pd
import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.jwt import get_current_user
from app.infrastructure.database.models.dataset import Dataset
from app.infrastructure.database.models.organization import Organization
from app.infrastructure.database.models.user import User
from app.infrastructure.database.session import get_db
from app.infrastructure.storage.s3 import get_s3_client


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase."""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class CamelModel(BaseModel):
    """Base model with camelCase serialization."""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    def model_dump(self, **kwargs):
        """Override to always serialize with aliases (camelCase)."""
        kwargs.setdefault('by_alias', True)
        return super().model_dump(**kwargs)

logger = structlog.get_logger()

router = APIRouter()

# Allowed file extensions
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".parquet"}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

# Upload configuration - can be customized per organization
UPLOAD_CONFIG = {
    "allowed_extensions": list(ALLOWED_EXTENSIONS),
    "max_file_size_bytes": MAX_FILE_SIZE,
    "max_file_size_display": "100MB",
    "guidelines": [
        {"text": "Include a date column in YYYY-MM-DD or similar format", "type": "required"},
        {"text": "First row should contain column headers", "type": "required"},
        {"text": "Numeric values should not contain currency symbols", "type": "recommended"},
        {"text": "No special characters in column names (use underscores)", "type": "recommended"},
        {"text": "Ensure consistent data types in each column", "type": "recommended"},
    ],
    "required_columns": [
        {"name": "Date/Time", "description": "A column with date or timestamp values", "type": "required", "examples": ["date", "timestamp", "week", "month"]},
        {"name": "Target Metric", "description": "Revenue, sales, or conversions to predict", "type": "required", "examples": ["revenue", "sales", "conversions"]},
    ],
    "optional_columns": [
        {"name": "Marketing Spend", "description": "Total or channel-level marketing spend", "type": "recommended", "examples": ["spend", "cost", "budget"]},
        {"name": "Channel Breakdown", "description": "Individual channel spend columns", "type": "optional", "examples": ["tv_spend", "digital_spend", "search_spend"]},
        {"name": "External Factors", "description": "Seasonality, holidays, economic indicators", "type": "optional", "examples": ["is_holiday", "temperature", "gdp"]},
    ],
    "template_columns": ["date", "revenue", "tv_spend", "digital_spend", "search_spend", "social_spend", "email_spend"],
}


class UploadConfigResponse(CamelModel):
    """Upload configuration response."""

    allowed_extensions: list[str]
    max_file_size_bytes: int
    max_file_size_display: str
    guidelines: list[dict]
    required_columns: list[dict]
    optional_columns: list[dict]
    template_columns: list[str]


class UploadResponse(CamelModel):
    """Upload response model."""

    file_id: str
    filename: str
    size_bytes: int
    rows: int
    columns: int
    column_names: list[str]
    preview: list[dict]


class DetectedColumnsResponse(CamelModel):
    """Detected columns analysis response."""

    date_columns: list[str]
    numeric_columns: list[str]
    categorical_columns: list[str]
    potential_target: str | None
    potential_spend_columns: list[str]


class FileValidationResult(CamelModel):
    """File validation result."""

    is_valid: bool
    errors: list[str]
    warnings: list[str]
    row_count: int | None
    column_count: int | None
    detected_columns: DetectedColumnsResponse | None = None  # Column analysis


@router.get("/upload/config", response_model=UploadConfigResponse, response_model_by_alias=True)
async def get_upload_config() -> UploadConfigResponse:
    """Get upload configuration including guidelines and required columns."""
    return UploadConfigResponse(**UPLOAD_CONFIG)


def validate_file_extension(filename: str) -> bool:
    """Validate file extension."""
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS


def validate_file_size(size: int) -> bool:
    """Validate file size."""
    return size <= MAX_FILE_SIZE


def analyze_columns(df: pd.DataFrame) -> dict:
    """Analyze dataframe columns and detect their types."""
    analysis = {
        "date_columns": [],
        "numeric_columns": [],
        "categorical_columns": [],
        "potential_target": None,
        "potential_spend_columns": [],
    }

    for col in df.columns:
        col_lower = col.lower()

        # Detect date columns
        if any(keyword in col_lower for keyword in ["date", "time", "week", "month", "year"]):
            analysis["date_columns"].append(col)
            continue

        # Check if column is numeric
        if pd.api.types.is_numeric_dtype(df[col]):
            analysis["numeric_columns"].append(col)

            # Detect potential target columns
            if any(keyword in col_lower for keyword in ["revenue", "sales", "conversion", "target", "outcome"]):
                analysis["potential_target"] = col

            # Detect potential spend columns
            if any(keyword in col_lower for keyword in ["spend", "cost", "budget", "investment"]):
                analysis["potential_spend_columns"].append(col)
        else:
            # Try to parse as date
            try:
                pd.to_datetime(df[col].head(100), errors='raise')
                analysis["date_columns"].append(col)
            except:
                analysis["categorical_columns"].append(col)

    return analysis


async def read_file_to_dataframe(file: UploadFile) -> pd.DataFrame:
    """Read uploaded file into pandas DataFrame."""
    if not file.filename:
        raise ValueError("No filename provided")
    ext = Path(file.filename).suffix.lower()
    content = await file.read()

    if ext == ".csv":
        from io import BytesIO
        df = pd.read_csv(BytesIO(content))
    elif ext in {".xlsx", ".xls"}:
        from io import BytesIO
        df = pd.read_excel(BytesIO(content))
    elif ext == ".parquet":
        from io import BytesIO
        df = pd.read_parquet(BytesIO(content))
    else:
        raise ValueError(f"Unsupported file format: {ext}")

    return df


@router.post("/upload/data", response_model=UploadResponse, response_model_by_alias=True)
async def upload_data_file(
    file: Annotated[UploadFile, File(description="Data file to upload")],
    name: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UploadResponse:
    """Upload a data file (CSV, Excel, Parquet)."""
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    if not validate_file_extension(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Ensure user has an organization (create default if needed)
    organization_id = current_user.organization_id
    if not organization_id:
        # Create a default personal organization for the user
        default_org = Organization(
            id=uuid.uuid4(),
            name=f"{current_user.email}'s Workspace",
            slug=f"user-{current_user.id}",
        )
        db.add(default_org)

        # Update user with the new organization
        current_user.organization_id = default_org.id
        organization_id = default_org.id

        await db.flush()  # Ensure the organization is created before using its ID
        logger.info(
            "Created default organization for user",
            user_id=str(current_user.id),
            organization_id=str(organization_id),
        )

    # Read file content
    try:
        df = await read_file_to_dataframe(file)
    except Exception as e:
        logger.error("Failed to read file", error=str(e), filename=file.filename)
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

    # Generate dataset ID
    dataset_id = uuid.uuid4()

    # Convert DataFrame to parquet bytes for S3 upload
    parquet_buffer = io.BytesIO()
    try:
        df.to_parquet(parquet_buffer, index=False)
        parquet_buffer.seek(0)
    except Exception as e:
        logger.error("Failed to convert to parquet", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to convert file: {str(e)}")

    # Upload to S3/MinIO
    storage_key = f"datasets/{organization_id}/{dataset_id}.parquet"
    try:
        s3_client = get_s3_client()
        storage_path = s3_client.upload_file(
            file_obj=parquet_buffer,
            key=storage_key,
            content_type="application/octet-stream",
            metadata={
                "dataset_id": str(dataset_id),
                "organization_id": str(organization_id),
                "original_filename": file.filename or "unknown",
            },
        )
        logger.info(
            "File uploaded to S3/MinIO",
            storage_path=storage_path,
            dataset_id=str(dataset_id),
        )
    except Exception as e:
        logger.error("Failed to upload to S3/MinIO", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to save file to storage: {str(e)}")

    # Get file info
    await file.seek(0)
    content = await file.read()
    original_file_size = len(content)

    # Analyze columns
    column_analysis = analyze_columns(df)

    # Build column types dict
    column_types = {}
    for col in df.columns:
        dtype = str(df[col].dtype)
        column_types[col] = dtype

    # Create dataset record in database
    dataset_name = name or Path(file.filename).stem
    dataset = Dataset(
        id=dataset_id,
        name=dataset_name,
        description=description,
        organization_id=organization_id,
        row_count=len(df),
        column_count=len(df.columns),
        file_size_bytes=original_file_size,
        storage_path=str(storage_path),
        storage_format="parquet",
        schema_definition={"columns": list(df.columns)},
        column_types=column_types,
        extra_metadata={
            "original_filename": file.filename,
            "detected_columns": column_analysis,
        },
        is_active=True,
    )

    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)

    # Create preview (first 10 rows)
    preview = df.head(10).to_dict(orient="records")

    logger.info(
        "File uploaded and saved successfully",
        dataset_id=str(dataset_id),
        filename=file.filename,
        rows=len(df),
        columns=len(df.columns),
        user_id=str(current_user.id),
        organization_id=str(organization_id),
    )

    return UploadResponse(
        file_id=str(dataset_id),
        filename=file.filename,
        size_bytes=original_file_size,
        rows=len(df),
        columns=len(df.columns),
        column_names=list(df.columns),
        preview=preview,
    )


@router.post("/upload/validate", response_model=FileValidationResult, response_model_by_alias=True)
async def validate_data_file(
    file: Annotated[UploadFile, File(description="Data file to validate")],
    current_user: User = Depends(get_current_user),
) -> FileValidationResult:
    """Validate a data file without saving it."""
    errors: list[str] = []
    warnings: list[str] = []

    # Validate filename
    if not file.filename:
        return FileValidationResult(
            is_valid=False,
            errors=["No filename provided"],
            warnings=[],
            row_count=None,
            column_count=None,
        )

    # Validate extension
    if not validate_file_extension(file.filename):
        errors.append(f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    # Try to read file
    row_count = None
    column_count = None
    detected_columns = None
    try:
        df = await read_file_to_dataframe(file)
        row_count = len(df)
        column_count = len(df.columns)

        # Analyze columns for intelligent detection
        detected_columns = analyze_columns(df)

        # Check for common issues
        if df.empty:
            errors.append("File contains no data")

        # Check for missing values
        missing_pct = df.isnull().sum().sum() / (row_count * column_count) * 100
        if missing_pct > 50:
            errors.append(f"Too many missing values: {missing_pct:.1f}%")
        elif missing_pct > 10:
            warnings.append(f"High missing value rate: {missing_pct:.1f}%")

        # Check for duplicate rows
        duplicates = df.duplicated().sum()
        if duplicates > 0:
            warnings.append(f"Found {duplicates} duplicate rows")

        # Check for required columns using intelligent detection
        if not detected_columns["date_columns"]:
            warnings.append("No date column detected. Time series analysis requires a date column.")

        if not detected_columns["potential_target"]:
            warnings.append("No target metric (revenue/sales) detected. Consider adding a target column.")

        # Provide helpful info about detected columns
        if detected_columns["potential_spend_columns"]:
            logger.info(
                "Detected spend columns",
                spend_columns=detected_columns["potential_spend_columns"]
            )

    except Exception as e:
        errors.append(f"Failed to parse file: {str(e)}")

    # Convert detected_columns dict to response model
    detected_columns_response = None
    if detected_columns:
        detected_columns_response = DetectedColumnsResponse(
            date_columns=detected_columns["date_columns"],
            numeric_columns=detected_columns["numeric_columns"],
            categorical_columns=detected_columns["categorical_columns"],
            potential_target=detected_columns["potential_target"],
            potential_spend_columns=detected_columns["potential_spend_columns"],
        )

    return FileValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        row_count=row_count,
        column_count=column_count,
        detected_columns=detected_columns_response,
    )
