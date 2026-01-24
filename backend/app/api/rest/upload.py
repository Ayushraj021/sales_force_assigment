"""File upload endpoints."""

import uuid
from pathlib import Path
from typing import Annotated

import pandas as pd
import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.config import settings
from app.core.security.jwt import get_current_user
from app.infrastructure.database.models.user import User

logger = structlog.get_logger()

router = APIRouter()

# Allowed file extensions
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".parquet"}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB


class UploadResponse(BaseModel):
    """Upload response model."""

    file_id: str
    filename: str
    size_bytes: int
    rows: int
    columns: int
    column_names: list[str]
    preview: list[dict]


class FileValidationResult(BaseModel):
    """File validation result."""

    is_valid: bool
    errors: list[str]
    warnings: list[str]
    row_count: int | None
    column_count: int | None


def validate_file_extension(filename: str) -> bool:
    """Validate file extension."""
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS


def validate_file_size(size: int) -> bool:
    """Validate file size."""
    return size <= MAX_FILE_SIZE


async def read_file_to_dataframe(file: UploadFile) -> pd.DataFrame:
    """Read uploaded file into pandas DataFrame."""
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


@router.post("/upload/data", response_model=UploadResponse)
async def upload_data_file(
    file: Annotated[UploadFile, File(description="Data file to upload")],
    name: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
    current_user: User = Depends(get_current_user),
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

    # Read file content
    try:
        df = await read_file_to_dataframe(file)
    except Exception as e:
        logger.error("Failed to read file", error=str(e), filename=file.filename)
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

    # Generate file ID
    file_id = str(uuid.uuid4())

    # Get file info
    await file.seek(0)
    content = await file.read()
    file_size = len(content)

    # Create preview (first 10 rows)
    preview = df.head(10).to_dict(orient="records")

    logger.info(
        "File uploaded successfully",
        file_id=file_id,
        filename=file.filename,
        rows=len(df),
        columns=len(df.columns),
        user_id=str(current_user.id),
    )

    return UploadResponse(
        file_id=file_id,
        filename=file.filename,
        size_bytes=file_size,
        rows=len(df),
        columns=len(df.columns),
        column_names=list(df.columns),
        preview=preview,
    )


@router.post("/upload/validate", response_model=FileValidationResult)
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
    try:
        df = await read_file_to_dataframe(file)
        row_count = len(df)
        column_count = len(df.columns)

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

        # Check for potential date column
        date_columns = [col for col in df.columns if "date" in col.lower()]
        if not date_columns:
            warnings.append("No date column detected. Time series analysis requires a date column.")

    except Exception as e:
        errors.append(f"Failed to parse file: {str(e)}")

    return FileValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        row_count=row_count,
        column_count=column_count,
    )
