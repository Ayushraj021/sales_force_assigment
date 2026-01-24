"""
Amazon Redshift Connector

Connects to Redshift for data import/export and analytics.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Iterator
from contextlib import contextmanager
import logging
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class RedshiftConfig:
    """Redshift connection configuration."""
    host: str
    port: int = 5439
    database: str = "dev"
    user: str = ""
    password: str = ""
    schema: str = "public"
    iam_role: Optional[str] = None  # For IAM-based auth
    region: str = "us-east-1"
    ssl: bool = True


class RedshiftConnector:
    """
    Amazon Redshift Connector.

    Features:
    - Query execution with pandas integration
    - COPY/UNLOAD for S3 integration
    - Table management
    - Cluster operations

    Example:
        config = RedshiftConfig(
            host="my-cluster.xxx.us-east-1.redshift.amazonaws.com",
            database="analytics",
            user="admin",
            password="...",
        )
        connector = RedshiftConnector(config)

        # Query data
        df = connector.query("SELECT * FROM campaigns WHERE year = 2024")

        # Write data
        connector.write_dataframe(df, "campaign_results")
    """

    def __init__(self, config: RedshiftConfig):
        self.config = config
        self._connection = None

        try:
            import redshift_connector
            self._redshift = redshift_connector
        except ImportError:
            try:
                # Fallback to psycopg2
                import psycopg2
                self._redshift = psycopg2
                self._use_psycopg2 = True
            except ImportError:
                logger.warning(
                    "redshift_connector or psycopg2 not installed. "
                    "Install with: pip install redshift_connector"
                )
                self._redshift = None
                self._use_psycopg2 = False

    @contextmanager
    def _get_connection(self):
        """Get Redshift connection context."""
        if self._redshift is None:
            raise RuntimeError("Redshift connector not available")

        if hasattr(self, "_use_psycopg2") and self._use_psycopg2:
            conn = self._redshift.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password,
                sslmode="require" if self.config.ssl else "disable",
            )
        else:
            conn = self._redshift.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password,
                ssl=self.config.ssl,
            )
        try:
            yield conn
        finally:
            conn.close()

    def query(
        self,
        sql: str,
        params: Optional[tuple] = None,
    ) -> pd.DataFrame:
        """
        Execute query and return results as DataFrame.

        Args:
            sql: SQL query
            params: Query parameters

        Returns:
            DataFrame with results
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)

                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]

                return pd.DataFrame(results, columns=columns)
            finally:
                cursor.close()

    def query_chunks(
        self,
        sql: str,
        chunk_size: int = 10000,
    ) -> Iterator[pd.DataFrame]:
        """
        Execute query and yield results in chunks.

        Args:
            sql: SQL query
            chunk_size: Rows per chunk

        Yields:
            DataFrame chunks
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql)

                while True:
                    rows = cursor.fetchmany(chunk_size)
                    if not rows:
                        break

                    columns = [desc[0] for desc in cursor.description]
                    yield pd.DataFrame(rows, columns=columns)
            finally:
                cursor.close()

    def write_dataframe(
        self,
        df: pd.DataFrame,
        table_name: str,
        if_exists: str = "append",  # 'fail', 'replace', 'append'
    ) -> int:
        """
        Write DataFrame to Redshift table.

        Args:
            df: DataFrame to write
            table_name: Target table name
            if_exists: How to handle existing table

        Returns:
            Number of rows written
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            try:
                # Handle if_exists
                if if_exists == "replace":
                    cursor.execute(f"DROP TABLE IF EXISTS {self.config.schema}.{table_name}")
                    conn.commit()

                # Create table if needed
                if if_exists in ("replace", "fail"):
                    create_sql = self._generate_create_table(df, table_name)
                    cursor.execute(create_sql)
                    conn.commit()

                # Insert data
                columns = ", ".join(df.columns)
                placeholders = ", ".join(["%s"] * len(df.columns))
                insert_sql = f"""
                INSERT INTO {self.config.schema}.{table_name} ({columns})
                VALUES ({placeholders})
                """

                for _, row in df.iterrows():
                    cursor.execute(insert_sql, tuple(row))

                conn.commit()
                logger.info(f"Wrote {len(df)} rows to {table_name}")
                return len(df)

            finally:
                cursor.close()

    def _generate_create_table(
        self,
        df: pd.DataFrame,
        table_name: str,
    ) -> str:
        """Generate CREATE TABLE statement from DataFrame."""
        type_mapping = {
            "int64": "BIGINT",
            "int32": "INTEGER",
            "float64": "DOUBLE PRECISION",
            "float32": "REAL",
            "bool": "BOOLEAN",
            "datetime64[ns]": "TIMESTAMP",
            "object": "VARCHAR(256)",
        }

        columns = []
        for col in df.columns:
            dtype = str(df[col].dtype)
            sql_type = type_mapping.get(dtype, "VARCHAR(256)")
            columns.append(f'"{col}" {sql_type}')

        columns_sql = ", ".join(columns)
        return f"CREATE TABLE {self.config.schema}.{table_name} ({columns_sql})"

    def execute(
        self,
        sql: str,
        params: Optional[tuple] = None,
    ) -> None:
        """
        Execute SQL statement (non-query).

        Args:
            sql: SQL statement
            params: Statement parameters
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                conn.commit()
            finally:
                cursor.close()

    def copy_from_s3(
        self,
        table_name: str,
        s3_path: str,
        format: str = "CSV",
        delimiter: str = ",",
        ignore_header: int = 1,
    ) -> None:
        """
        COPY data from S3 into Redshift table.

        Args:
            table_name: Target table
            s3_path: S3 path (s3://bucket/path)
            format: File format (CSV, JSON, PARQUET)
            delimiter: Field delimiter for CSV
            ignore_header: Number of header rows to skip
        """
        if not self.config.iam_role:
            raise ValueError("IAM role required for S3 operations")

        sql = f"""
        COPY {self.config.schema}.{table_name}
        FROM '{s3_path}'
        IAM_ROLE '{self.config.iam_role}'
        FORMAT AS {format}
        """

        if format == "CSV":
            sql += f" DELIMITER '{delimiter}' IGNOREHEADER {ignore_header}"

        self.execute(sql)
        logger.info(f"Copied data from {s3_path} to {table_name}")

    def unload_to_s3(
        self,
        sql: str,
        s3_path: str,
        format: str = "CSV",
        parallel: bool = True,
    ) -> None:
        """
        UNLOAD query results to S3.

        Args:
            sql: Query to unload
            s3_path: S3 destination path
            format: Output format (CSV, PARQUET)
            parallel: Enable parallel unload
        """
        if not self.config.iam_role:
            raise ValueError("IAM role required for S3 operations")

        unload_sql = f"""
        UNLOAD ('{sql.replace("'", "''")}')
        TO '{s3_path}'
        IAM_ROLE '{self.config.iam_role}'
        FORMAT AS {format}
        """

        if not parallel:
            unload_sql += " PARALLEL OFF"

        self.execute(unload_sql)
        logger.info(f"Unloaded data to {s3_path}")

    def get_tables(self, schema: Optional[str] = None) -> List[str]:
        """
        List tables in schema.

        Args:
            schema: Schema name (default: configured schema)

        Returns:
            List of table names
        """
        schema = schema or self.config.schema
        sql = f"""
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = '{schema}'
        ORDER BY tablename
        """
        df = self.query(sql)
        return df["tablename"].tolist()

    def get_table_schema(self, table_name: str) -> pd.DataFrame:
        """
        Get table schema/columns.

        Args:
            table_name: Table name

        Returns:
            DataFrame with column info
        """
        sql = f"""
        SELECT
            column_name,
            data_type,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_name = '{table_name}'
        AND table_schema = '{self.config.schema}'
        ORDER BY ordinal_position
        """
        return self.query(sql)

    def vacuum_table(self, table_name: str, full: bool = False) -> None:
        """
        VACUUM table to reclaim space and resort rows.

        Args:
            table_name: Table to vacuum
            full: Full vacuum (slower, more thorough)
        """
        vacuum_type = "FULL" if full else ""
        sql = f"VACUUM {vacuum_type} {self.config.schema}.{table_name}"
        self.execute(sql)
        logger.info(f"Vacuumed table {table_name}")

    def analyze_table(self, table_name: str) -> None:
        """
        ANALYZE table to update statistics.

        Args:
            table_name: Table to analyze
        """
        sql = f"ANALYZE {self.config.schema}.{table_name}"
        self.execute(sql)
        logger.info(f"Analyzed table {table_name}")

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
        FROM {self.config.schema}.marketing_performance
        WHERE date BETWEEN '{start_date}' AND '{end_date}'
        {channel_filter}
        ORDER BY date, channel
        """
        return self.query(sql)

    def get_cluster_info(self) -> Dict[str, Any]:
        """
        Get cluster information.

        Returns:
            Dict with cluster metrics
        """
        sql = """
        SELECT
            SUM(capacity) as total_capacity_mb,
            SUM(used) as used_mb,
            SUM(capacity) - SUM(used) as free_mb
        FROM stv_partitions
        WHERE part_begin = 0
        """
        df = self.query(sql)

        return {
            "total_capacity_mb": df["total_capacity_mb"].iloc[0],
            "used_mb": df["used_mb"].iloc[0],
            "free_mb": df["free_mb"].iloc[0],
        }
