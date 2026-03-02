"""Report management mutations."""

from typing import Optional
from uuid import UUID, uuid4

import strawberry
import structlog
from sqlalchemy import select
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.report import (
    CreateReportInput,
    ExportType,
    GenerateReportInput,
    GenerateReportResult,
    ReportType,
    ScheduledReportType,
    ScheduleReportInput,
    UpdateReportInput,
)
from app.core.exceptions import NotFoundError, ValidationError
from app.infrastructure.database.models.report import (
    Export,
    Report,
    ScheduledReport,
)

logger = structlog.get_logger()

# Valid report types
VALID_REPORT_TYPES = {"mmm", "forecast", "optimization", "attribution", "custom"}

# Valid export formats
VALID_EXPORT_FORMATS = {"pdf", "excel", "csv", "pptx", "html"}


def report_to_graphql(report: Report) -> ReportType:
    """Convert report to GraphQL type."""
    return ReportType(
        id=report.id,
        name=report.name,
        description=report.description,
        report_type=report.report_type,
        template=report.template,
        sections=report.sections,
        available_formats=report.available_formats,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


def scheduled_report_to_graphql(scheduled: ScheduledReport) -> ScheduledReportType:
    """Convert scheduled report to GraphQL type."""
    return ScheduledReportType(
        id=scheduled.id,
        name=scheduled.name,
        is_active=scheduled.is_active,
        schedule_type=scheduled.schedule_type,
        schedule_config=scheduled.schedule_config,
        timezone=scheduled.timezone,
        delivery_method=scheduled.delivery_method,
        delivery_config=scheduled.delivery_config,
        recipients=scheduled.recipients,
        export_format=scheduled.export_format,
        last_run_at=scheduled.last_run_at,
        last_run_status=scheduled.last_run_status,
        next_run_at=scheduled.next_run_at,
        report_id=scheduled.report_id,
        created_at=scheduled.created_at,
        updated_at=scheduled.updated_at,
    )


def export_to_graphql(export: Export) -> ExportType:
    """Convert export to GraphQL type."""
    return ExportType(
        id=export.id,
        export_type=export.export_type,
        export_format=export.export_format,
        status=export.status,
        file_path=export.file_path,
        file_size_bytes=export.file_size_bytes,
        download_url=export.download_url,
        expires_at=export.expires_at,
        error_message=export.error_message,
        created_at=export.created_at,
        updated_at=export.updated_at,
    )


@strawberry.type
class ReportMutation:
    """Report management mutations."""

    @strawberry.mutation
    async def create_report(
        self,
        info: Info,
        input: CreateReportInput,
    ) -> ReportType:
        """Create a new report template."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Validate name
        if not input.name or len(input.name.strip()) == 0:
            raise ValidationError("Report name is required")

        # Validate report type
        if input.report_type not in VALID_REPORT_TYPES:
            raise ValidationError(
                f"Invalid report type '{input.report_type}'. "
                f"Valid types: {', '.join(sorted(VALID_REPORT_TYPES))}"
            )

        # Create report
        report = Report(
            id=uuid4(),
            name=input.name.strip(),
            description=input.description,
            report_type=input.report_type,
            template=input.template or {},
            sections=input.sections or [],
            available_formats=input.available_formats or ["pdf", "excel"],
            organization_id=current_user.organization_id,
            created_by_id=current_user.id,
        )
        db.add(report)

        await db.commit()
        await db.refresh(report)

        logger.info(
            "Report created",
            report_id=str(report.id),
            created_by=str(current_user.id),
        )

        return report_to_graphql(report)

    @strawberry.mutation
    async def update_report(
        self,
        info: Info,
        report_id: UUID,
        input: UpdateReportInput,
    ) -> ReportType:
        """Update a report template."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get report
        result = await db.execute(
            select(Report).where(
                Report.id == report_id,
                Report.organization_id == current_user.organization_id,
            )
        )
        report = result.scalar_one_or_none()

        if not report:
            raise NotFoundError("Report", str(report_id))

        # Update fields
        if input.name is not None:
            if len(input.name.strip()) == 0:
                raise ValidationError("Report name cannot be empty")
            report.name = input.name.strip()

        if input.description is not None:
            report.description = input.description

        if input.template is not None:
            report.template = input.template

        if input.sections is not None:
            report.sections = input.sections

        if input.available_formats is not None:
            report.available_formats = input.available_formats

        await db.commit()
        await db.refresh(report)

        logger.info(
            "Report updated",
            report_id=str(report.id),
            updated_by=str(current_user.id),
        )

        return report_to_graphql(report)

    @strawberry.mutation
    async def delete_report(
        self,
        info: Info,
        report_id: UUID,
    ) -> bool:
        """Delete a report template."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get report
        result = await db.execute(
            select(Report).where(
                Report.id == report_id,
                Report.organization_id == current_user.organization_id,
            )
        )
        report = result.scalar_one_or_none()

        if not report:
            raise NotFoundError("Report", str(report_id))

        # Delete report (cascade deletes scheduled reports)
        await db.delete(report)
        await db.commit()

        logger.info(
            "Report deleted",
            report_id=str(report_id),
            deleted_by=str(current_user.id),
        )

        return True

    @strawberry.mutation
    async def schedule_report(
        self,
        info: Info,
        input: ScheduleReportInput,
    ) -> ScheduledReportType:
        """Schedule a report for automatic generation."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Verify report exists
        result = await db.execute(
            select(Report).where(
                Report.id == input.report_id,
                Report.organization_id == current_user.organization_id,
            )
        )
        report = result.scalar_one_or_none()

        if not report:
            raise NotFoundError("Report", str(input.report_id))

        # Validate schedule type
        valid_schedule_types = {"daily", "weekly", "monthly"}
        if input.schedule_type not in valid_schedule_types:
            raise ValidationError(
                f"Invalid schedule type. Valid: {', '.join(valid_schedule_types)}"
            )

        # Validate export format
        if input.export_format not in VALID_EXPORT_FORMATS:
            raise ValidationError(
                f"Invalid export format. Valid: {', '.join(VALID_EXPORT_FORMATS)}"
            )

        # Validate recipients
        if not input.recipients:
            raise ValidationError("At least one recipient is required")

        # Create scheduled report
        scheduled = ScheduledReport(
            id=uuid4(),
            name=input.name,
            is_active=True,
            schedule_type=input.schedule_type,
            schedule_config=input.schedule_config or {},
            timezone=input.timezone,
            delivery_method=input.delivery_method,
            delivery_config=input.delivery_config or {},
            recipients=input.recipients,
            export_format=input.export_format,
            report_id=input.report_id,
            organization_id=current_user.organization_id,
        )
        db.add(scheduled)

        await db.commit()
        await db.refresh(scheduled)

        logger.info(
            "Report scheduled",
            scheduled_id=str(scheduled.id),
            report_id=str(report.id),
            created_by=str(current_user.id),
        )

        return scheduled_report_to_graphql(scheduled)

    @strawberry.mutation
    async def cancel_scheduled_report(
        self,
        info: Info,
        scheduled_id: UUID,
    ) -> bool:
        """Cancel a scheduled report."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get scheduled report
        result = await db.execute(
            select(ScheduledReport).where(
                ScheduledReport.id == scheduled_id,
                ScheduledReport.organization_id == current_user.organization_id,
            )
        )
        scheduled = result.scalar_one_or_none()

        if not scheduled:
            raise NotFoundError("Scheduled report", str(scheduled_id))

        scheduled.is_active = False

        await db.commit()

        logger.info(
            "Scheduled report cancelled",
            scheduled_id=str(scheduled_id),
            cancelled_by=str(current_user.id),
        )

        return True

    @strawberry.mutation
    async def generate_report(
        self,
        info: Info,
        input: GenerateReportInput,
    ) -> GenerateReportResult:
        """Generate a report immediately."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Verify report exists
        result = await db.execute(
            select(Report).where(
                Report.id == input.report_id,
                Report.organization_id == current_user.organization_id,
            )
        )
        report = result.scalar_one_or_none()

        if not report:
            raise NotFoundError("Report", str(input.report_id))

        # Validate export format
        if input.export_format not in VALID_EXPORT_FORMATS:
            raise ValidationError(
                f"Invalid export format. Valid: {', '.join(VALID_EXPORT_FORMATS)}"
            )

        # Create export job
        export = Export(
            id=uuid4(),
            export_type="report",
            export_format=input.export_format,
            status="pending",
            config={
                "report_id": str(report.id),
                "parameters": input.parameters or {},
            },
            organization_id=current_user.organization_id,
            created_by_id=current_user.id,
        )
        db.add(export)

        await db.commit()
        await db.refresh(export)

        logger.info(
            "Report generation started",
            export_id=str(export.id),
            report_id=str(report.id),
            requested_by=str(current_user.id),
        )

        # TODO: Queue report generation task
        # from app.infrastructure.celery.tasks import generate_report
        # generate_report.delay(str(export.id))

        return GenerateReportResult(
            success=True,
            message="Report generation started",
            export_id=export.id,
            download_url=None,  # Will be available after generation
        )
