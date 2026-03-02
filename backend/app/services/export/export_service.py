"""
Export Service

Data and report export functionality.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum
import logging
import pandas as pd
import io

logger = logging.getLogger(__name__)


class ExportFormat(str, Enum):
    """Export file formats."""
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"
    PARQUET = "parquet"
    PDF = "pdf"


@dataclass
class ExportConfig:
    """Export configuration."""
    format: ExportFormat = ExportFormat.CSV
    include_index: bool = False
    date_format: str = "%Y-%m-%d"
    compression: Optional[str] = None  # gzip, zip, etc.
    sheet_name: str = "Sheet1"


class ExportService:
    """
    Export Service.

    Features:
    - Multiple format support
    - Data export
    - Report generation
    - Streaming export

    Example:
        service = ExportService()

        # Export to CSV
        bytes_data = service.export(df, ExportConfig(format=ExportFormat.CSV))

        # Export to file
        service.export_to_file(df, "/path/to/output.xlsx", ExportConfig(format=ExportFormat.EXCEL))
    """

    def export(
        self,
        data: Union[pd.DataFrame, Dict[str, pd.DataFrame]],
        config: Optional[ExportConfig] = None,
    ) -> bytes:
        """
        Export data to bytes.

        Args:
            data: DataFrame or dict of DataFrames
            config: Export configuration

        Returns:
            Exported data as bytes
        """
        config = config or ExportConfig()

        if isinstance(data, dict):
            return self._export_multiple(data, config)
        return self._export_single(data, config)

    def _export_single(self, df: pd.DataFrame, config: ExportConfig) -> bytes:
        """Export single DataFrame."""
        buffer = io.BytesIO()

        if config.format == ExportFormat.CSV:
            df.to_csv(buffer, index=config.include_index, date_format=config.date_format)

        elif config.format == ExportFormat.EXCEL:
            df.to_excel(buffer, index=config.include_index, sheet_name=config.sheet_name)

        elif config.format == ExportFormat.JSON:
            json_str = df.to_json(orient="records", date_format="iso")
            buffer.write(json_str.encode())

        elif config.format == ExportFormat.PARQUET:
            df.to_parquet(buffer, index=config.include_index)

        buffer.seek(0)
        return buffer.read()

    def _export_multiple(
        self,
        data: Dict[str, pd.DataFrame],
        config: ExportConfig,
    ) -> bytes:
        """Export multiple DataFrames."""
        buffer = io.BytesIO()

        if config.format == ExportFormat.EXCEL:
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                for name, df in data.items():
                    df.to_excel(writer, sheet_name=name[:31], index=config.include_index)

        elif config.format == ExportFormat.JSON:
            import json
            result = {name: df.to_dict(orient="records") for name, df in data.items()}
            buffer.write(json.dumps(result).encode())

        else:
            # For other formats, just export first DataFrame
            first_df = list(data.values())[0]
            return self._export_single(first_df, config)

        buffer.seek(0)
        return buffer.read()

    def export_to_file(
        self,
        data: Union[pd.DataFrame, Dict[str, pd.DataFrame]],
        file_path: str,
        config: Optional[ExportConfig] = None,
    ) -> str:
        """
        Export data to file.

        Args:
            data: DataFrame or dict of DataFrames
            file_path: Output file path
            config: Export configuration

        Returns:
            File path
        """
        content = self.export(data, config)

        mode = "wb"
        with open(file_path, mode) as f:
            f.write(content)

        logger.info(f"Exported to {file_path}")
        return file_path

    def get_mime_type(self, format: ExportFormat) -> str:
        """Get MIME type for format."""
        mime_types = {
            ExportFormat.CSV: "text/csv",
            ExportFormat.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ExportFormat.JSON: "application/json",
            ExportFormat.PARQUET: "application/octet-stream",
            ExportFormat.PDF: "application/pdf",
        }
        return mime_types.get(format, "application/octet-stream")

    def get_file_extension(self, format: ExportFormat) -> str:
        """Get file extension for format."""
        extensions = {
            ExportFormat.CSV: ".csv",
            ExportFormat.EXCEL: ".xlsx",
            ExportFormat.JSON: ".json",
            ExportFormat.PARQUET: ".parquet",
            ExportFormat.PDF: ".pdf",
        }
        return extensions.get(format, ".dat")
