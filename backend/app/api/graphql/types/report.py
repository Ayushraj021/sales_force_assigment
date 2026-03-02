"""Report GraphQL types."""

from datetime import datetime
from typing import Optional
from uuid import UUID

import strawberry
from strawberry.scalars import JSON


@strawberry.type
class ReportType:
    """Report template type."""

    id: UUID
    name: str
    description: Optional[str]
    report_type: str
    template: JSON
    sections: JSON
    available_formats: JSON
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ScheduledReportType:
    """Scheduled report type."""

    id: UUID
    name: str
    is_active: bool
    schedule_type: str
    schedule_config: JSON
    timezone: str
    delivery_method: str
    delivery_config: JSON
    recipients: JSON
    export_format: str
    last_run_at: Optional[str]
    last_run_status: Optional[str]
    next_run_at: Optional[str]
    report_id: UUID
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ExportType:
    """Export job type."""

    id: UUID
    export_type: str
    export_format: str
    status: str
    file_path: Optional[str]
    file_size_bytes: Optional[int]
    download_url: Optional[str]
    expires_at: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime


@strawberry.input
class CreateReportInput:
    """Input for creating a report template."""

    name: str
    description: Optional[str] = None
    report_type: str  # mmm, forecast, optimization
    template: Optional[JSON] = None
    sections: Optional[JSON] = None
    available_formats: Optional[list[str]] = None


@strawberry.input
class UpdateReportInput:
    """Input for updating a report template."""

    name: Optional[str] = None
    description: Optional[str] = None
    template: Optional[JSON] = None
    sections: Optional[JSON] = None
    available_formats: Optional[list[str]] = None


@strawberry.input
class ScheduleReportInput:
    """Input for scheduling a report."""

    report_id: UUID
    name: str
    schedule_type: str  # daily, weekly, monthly
    schedule_config: Optional[JSON] = None
    timezone: str = "UTC"
    delivery_method: str = "email"
    delivery_config: Optional[JSON] = None
    recipients: list[str]
    export_format: str = "pdf"


@strawberry.input
class GenerateReportInput:
    """Input for generating a report."""

    report_id: UUID
    export_format: str = "pdf"
    parameters: Optional[JSON] = None


@strawberry.type
class GenerateReportResult:
    """Result of report generation."""

    success: bool
    message: str
    export_id: Optional[UUID] = None
    download_url: Optional[str] = None
