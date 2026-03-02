"""Report queries."""

from typing import Optional
from uuid import UUID

import strawberry
import structlog
from sqlalchemy import select
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.report import (
    ExportType,
    ReportType,
    ScheduledReportType,
)
from app.core.exceptions import NotFoundError
from app.infrastructure.database.models.report import (
    Export,
    Report,
    ScheduledReport,
)

logger = structlog.get_logger()


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
class ReportQuery:
    """Report queries."""

    @strawberry.field
    async def reports(
        self,
        info: Info,
        report_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ReportType]:
        """Get all report templates for the organization."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        query = select(Report).where(
            Report.organization_id == current_user.organization_id
        )

        if report_type is not None:
            query = query.where(Report.report_type == report_type)

        query = query.order_by(Report.created_at.desc()).offset(offset).limit(limit)

        result = await db.execute(query)
        reports = result.scalars().all()

        return [report_to_graphql(r) for r in reports]

    @strawberry.field
    async def report(
        self,
        info: Info,
        report_id: UUID,
    ) -> ReportType:
        """Get a specific report template by ID."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = await db.execute(
            select(Report).where(
                Report.id == report_id,
                Report.organization_id == current_user.organization_id,
            )
        )
        report = result.scalar_one_or_none()

        if not report:
            raise NotFoundError("Report", str(report_id))

        return report_to_graphql(report)

    @strawberry.field
    async def scheduled_reports(
        self,
        info: Info,
        is_active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ScheduledReportType]:
        """Get all scheduled reports for the organization."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        query = select(ScheduledReport).where(
            ScheduledReport.organization_id == current_user.organization_id
        )

        if is_active is not None:
            query = query.where(ScheduledReport.is_active == is_active)

        query = query.order_by(ScheduledReport.created_at.desc()).offset(offset).limit(limit)

        result = await db.execute(query)
        scheduled = result.scalars().all()

        return [scheduled_report_to_graphql(s) for s in scheduled]

    @strawberry.field
    async def exports(
        self,
        info: Info,
        status: Optional[str] = None,
        export_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ExportType]:
        """Get all exports for the organization."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        query = select(Export).where(
            Export.organization_id == current_user.organization_id
        )

        if status is not None:
            query = query.where(Export.status == status)

        if export_type is not None:
            query = query.where(Export.export_type == export_type)

        query = query.order_by(Export.created_at.desc()).offset(offset).limit(limit)

        result = await db.execute(query)
        exports = result.scalars().all()

        return [export_to_graphql(e) for e in exports]

    @strawberry.field
    async def export(
        self,
        info: Info,
        export_id: UUID,
    ) -> ExportType:
        """Get a specific export by ID."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = await db.execute(
            select(Export).where(
                Export.id == export_id,
                Export.organization_id == current_user.organization_id,
            )
        )
        export = result.scalar_one_or_none()

        if not export:
            raise NotFoundError("Export", str(export_id))

        return export_to_graphql(export)

    @strawberry.field
    async def report_types(self) -> list[str]:
        """Get list of available report types."""
        return ["mmm", "forecast", "optimization", "attribution", "custom"]

    @strawberry.field
    async def export_formats(self) -> list[str]:
        """Get list of available export formats."""
        return ["pdf", "excel", "csv", "pptx", "html"]
