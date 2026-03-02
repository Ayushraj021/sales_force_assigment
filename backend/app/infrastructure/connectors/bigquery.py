"""
Google BigQuery Connector

Connects to BigQuery for data import/export and analytics.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Iterator
import logging
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class BigQueryConfig:
    """BigQuery connection configuration."""
    project_id: str
    credentials_path: Optional[str] = None  # Path to service account JSON
    location: str = "US"
    dataset: Optional[str] = None


class BigQueryConnector:
    """
    Google BigQuery Connector.

    Features:
    - Query execution with pandas integration
    - Table management
    - Dataset operations
    - Streaming inserts

    Example:
        config = BigQueryConfig(
            project_id="my-project",
            credentials_path="/path/to/credentials.json",
            dataset="marketing_analytics",
        )
        connector = BigQueryConnector(config)

        # Query data
        df = connector.query("SELECT * FROM `my-project.dataset.table`")

        # Write data
        connector.write_dataframe(df, "results_table")
    """

    def __init__(self, config: BigQueryConfig):
        self.config = config
        self._client = None

        try:
            from google.cloud import bigquery
            from google.oauth2 import service_account

            if config.credentials_path:
                credentials = service_account.Credentials.from_service_account_file(
                    config.credentials_path
                )
                self._client = bigquery.Client(
                    project=config.project_id,
                    credentials=credentials,
                    location=config.location,
                )
            else:
                # Use default credentials
                self._client = bigquery.Client(
                    project=config.project_id,
                    location=config.location,
                )
            self._bigquery = bigquery
        except ImportError:
            logger.warning(
                "google-cloud-bigquery not installed. "
                "Install with: pip install google-cloud-bigquery[pandas]"
            )
            self._bigquery = None

    def query(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> pd.DataFrame:
        """
        Execute query and return results as DataFrame.

        Args:
            sql: SQL query (can use parameterized queries)
            params: Query parameters

        Returns:
            DataFrame with results
        """
        if self._client is None:
            raise RuntimeError("BigQuery client not available")

        job_config = self._bigquery.QueryJobConfig()

        if params:
            job_config.query_parameters = [
                self._bigquery.ScalarQueryParameter(k, self._infer_type(v), v)
                for k, v in params.items()
            ]

        query_job = self._client.query(sql, job_config=job_config)
        return query_job.to_dataframe()

    def _infer_type(self, value: Any) -> str:
        """Infer BigQuery type from Python value."""
        if isinstance(value, bool):
            return "BOOL"
        elif isinstance(value, int):
            return "INT64"
        elif isinstance(value, float):
            return "FLOAT64"
        elif isinstance(value, str):
            return "STRING"
        else:
            return "STRING"

    def query_to_table(
        self,
        sql: str,
        destination_table: str,
        write_disposition: str = "WRITE_TRUNCATE",
    ) -> int:
        """
        Execute query and write results to table.

        Args:
            sql: SQL query
            destination_table: Destination table (dataset.table)
            write_disposition: WRITE_TRUNCATE, WRITE_APPEND, WRITE_EMPTY

        Returns:
            Number of rows written
        """
        if self._client is None:
            raise RuntimeError("BigQuery client not available")

        table_ref = f"{self.config.project_id}.{destination_table}"

        job_config = self._bigquery.QueryJobConfig(
            destination=table_ref,
            write_disposition=write_disposition,
        )

        query_job = self._client.query(sql, job_config=job_config)
        query_job.result()  # Wait for completion

        return query_job.total_rows

    def write_dataframe(
        self,
        df: pd.DataFrame,
        table_name: str,
        if_exists: str = "append",  # 'fail', 'replace', 'append'
    ) -> int:
        """
        Write DataFrame to BigQuery table.

        Args:
            df: DataFrame to write
            table_name: Table name (without project/dataset prefix)
            if_exists: How to handle existing table

        Returns:
            Number of rows written
        """
        if self._client is None:
            raise RuntimeError("BigQuery client not available")

        dataset = self.config.dataset
        if not dataset:
            raise ValueError("Dataset must be configured for write operations")

        table_ref = f"{self.config.project_id}.{dataset}.{table_name}"

        write_disposition = {
            "fail": self._bigquery.WriteDisposition.WRITE_EMPTY,
            "replace": self._bigquery.WriteDisposition.WRITE_TRUNCATE,
            "append": self._bigquery.WriteDisposition.WRITE_APPEND,
        }.get(if_exists, self._bigquery.WriteDisposition.WRITE_APPEND)

        job_config = self._bigquery.LoadJobConfig(
            write_disposition=write_disposition,
            autodetect=True,
        )

        job = self._client.load_table_from_dataframe(
            df, table_ref, job_config=job_config
        )
        job.result()  # Wait for completion

        logger.info(f"Wrote {len(df)} rows to {table_ref}")
        return len(df)

    def stream_insert(
        self,
        rows: List[Dict[str, Any]],
        table_name: str,
    ) -> List[Dict]:
        """
        Stream insert rows into table (real-time).

        Args:
            rows: List of row dictionaries
            table_name: Table name

        Returns:
            List of errors (empty if successful)
        """
        if self._client is None:
            raise RuntimeError("BigQuery client not available")

        dataset = self.config.dataset
        table_ref = f"{self.config.project_id}.{dataset}.{table_name}"

        errors = self._client.insert_rows_json(table_ref, rows)
        if errors:
            logger.error(f"Streaming insert errors: {errors}")

        return errors

    def get_datasets(self) -> List[str]:
        """
        List datasets in project.

        Returns:
            List of dataset names
        """
        if self._client is None:
            raise RuntimeError("BigQuery client not available")

        datasets = list(self._client.list_datasets())
        return [ds.dataset_id for ds in datasets]

    def get_tables(self, dataset: Optional[str] = None) -> List[str]:
        """
        List tables in dataset.

        Args:
            dataset: Dataset name (default: configured dataset)

        Returns:
            List of table names
        """
        if self._client is None:
            raise RuntimeError("BigQuery client not available")

        dataset = dataset or self.config.dataset
        tables = list(self._client.list_tables(dataset))
        return [t.table_id for t in tables]

    def get_table_schema(self, table_name: str) -> pd.DataFrame:
        """
        Get table schema/columns.

        Args:
            table_name: Table name

        Returns:
            DataFrame with column info
        """
        if self._client is None:
            raise RuntimeError("BigQuery client not available")

        dataset = self.config.dataset
        table_ref = f"{self.config.project_id}.{dataset}.{table_name}"
        table = self._client.get_table(table_ref)

        schema_data = []
        for field in table.schema:
            schema_data.append({
                "column_name": field.name,
                "data_type": field.field_type,
                "mode": field.mode,
                "description": field.description,
            })

        return pd.DataFrame(schema_data)

    def create_dataset(
        self,
        dataset_name: str,
        location: Optional[str] = None,
    ) -> None:
        """
        Create a new dataset.

        Args:
            dataset_name: Dataset name
            location: Dataset location
        """
        if self._client is None:
            raise RuntimeError("BigQuery client not available")

        dataset_ref = f"{self.config.project_id}.{dataset_name}"
        dataset = self._bigquery.Dataset(dataset_ref)
        dataset.location = location or self.config.location

        self._client.create_dataset(dataset, exists_ok=True)
        logger.info(f"Created dataset {dataset_name}")

    def delete_table(self, table_name: str) -> None:
        """
        Delete a table.

        Args:
            table_name: Table name
        """
        if self._client is None:
            raise RuntimeError("BigQuery client not available")

        dataset = self.config.dataset
        table_ref = f"{self.config.project_id}.{dataset}.{table_name}"
        self._client.delete_table(table_ref, not_found_ok=True)
        logger.info(f"Deleted table {table_name}")

    def get_marketing_data(
        self,
        start_date: str,
        end_date: str,
        channels: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Get marketing performance data.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            channels: Optional list of channels to filter

        Returns:
            DataFrame with marketing data
        """
        dataset = self.config.dataset
        channel_filter = ""
        if channels:
            channel_list = ", ".join([f"'{c}'" for c in channels])
            channel_filter = f"AND channel IN ({channel_list})"

        sql = f"""
        SELECT
            date,
            channel,
            campaign_id,
            campaign_name,
            impressions,
            clicks,
            conversions,
            spend,
            revenue
        FROM `{self.config.project_id}.{dataset}.marketing_performance`
        WHERE date BETWEEN '{start_date}' AND '{end_date}'
        {channel_filter}
        ORDER BY date, channel
        """
        return self.query(sql)

    def export_to_gcs(
        self,
        sql: str,
        gcs_uri: str,
        format: str = "CSV",  # CSV, JSON, AVRO, PARQUET
    ) -> None:
        """
        Export query results to Google Cloud Storage.

        Args:
            sql: SQL query
            gcs_uri: GCS URI (gs://bucket/path)
            format: Export format
        """
        if self._client is None:
            raise RuntimeError("BigQuery client not available")

        # First, query to temp table
        temp_table = f"temp_export_{int(pd.Timestamp.now().timestamp())}"
        self.query_to_table(sql, f"{self.config.dataset}.{temp_table}")

        # Then export to GCS
        table_ref = f"{self.config.project_id}.{self.config.dataset}.{temp_table}"

        job_config = self._bigquery.ExtractJobConfig(
            destination_format=getattr(
                self._bigquery.DestinationFormat, format
            ),
        )

        extract_job = self._client.extract_table(
            table_ref, gcs_uri, job_config=job_config
        )
        extract_job.result()

        # Clean up temp table
        self.delete_table(temp_table)

        logger.info(f"Exported to {gcs_uri}")
