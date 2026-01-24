"""
Snowflake Data Warehouse Connector

Connects to Snowflake for data import/export and analytics.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Iterator
from contextlib import contextmanager
import logging
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class SnowflakeConfig:
    """Snowflake connection configuration."""
    account: str
    user: str
    password: str
    warehouse: str
    database: str
    schema: str = "PUBLIC"
    role: Optional[str] = None
    authenticator: Optional[str] = None  # For SSO: "externalbrowser"


class SnowflakeConnector:
    """
    Snowflake Data Warehouse Connector.

    Features:
    - Query execution with pandas integration
    - Bulk data loading
    - Table management
    - Warehouse scaling

    Example:
        config = SnowflakeConfig(
            account="xy12345.us-east-1",
            user="analytics_user",
            password="...",
            warehouse="ANALYTICS_WH",
            database="MARKETING",
        )
        connector = SnowflakeConnector(config)

        # Query data
        df = connector.query("SELECT * FROM campaigns WHERE year = 2024")

        # Write data
        connector.write_dataframe(df, "campaign_results")
    """

    def __init__(self, config: SnowflakeConfig):
        self.config = config
        self._connection = None

        try:
            import snowflake.connector
            self._snowflake = snowflake.connector
        except ImportError:
            logger.warning(
                "snowflake-connector-python not installed. "
                "Install with: pip install snowflake-connector-python[pandas]"
            )
            self._snowflake = None

    @contextmanager
    def _get_connection(self):
        """Get Snowflake connection context."""
        if self._snowflake is None:
            raise RuntimeError("Snowflake connector not available")

        conn = self._snowflake.connect(
            account=self.config.account,
            user=self.config.user,
            password=self.config.password,
            warehouse=self.config.warehouse,
            database=self.config.database,
            schema=self.config.schema,
            role=self.config.role,
            authenticator=self.config.authenticator,
        )
        try:
            yield conn
        finally:
            conn.close()

    def query(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
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

                # Fetch all results
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]

                return pd.DataFrame(results, columns=columns)
            finally:
                cursor.close()

    def query_pandas(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> pd.DataFrame:
        """
        Execute query using pandas connector (more efficient).

        Args:
            sql: SQL query
            params: Query parameters

        Returns:
            DataFrame with results
        """
        with self._get_connection() as conn:
            return pd.read_sql(sql, conn, params=params)

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
        chunk_size: int = 10000,
    ) -> int:
        """
        Write DataFrame to Snowflake table.

        Args:
            df: DataFrame to write
            table_name: Target table name
            if_exists: How to handle existing table
            chunk_size: Rows per batch

        Returns:
            Number of rows written
        """
        from snowflake.connector.pandas_tools import write_pandas

        with self._get_connection() as conn:
            # Handle if_exists
            if if_exists == "replace":
                cursor = conn.cursor()
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                cursor.close()

            success, nchunks, nrows, _ = write_pandas(
                conn,
                df,
                table_name,
                database=self.config.database,
                schema=self.config.schema,
                chunk_size=chunk_size,
                auto_create_table=True,
            )

            if success:
                logger.info(f"Wrote {nrows} rows to {table_name}")
                return nrows
            else:
                raise RuntimeError(f"Failed to write to {table_name}")

    def execute(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
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
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = '{schema}'
        ORDER BY TABLE_NAME
        """
        df = self.query(sql)
        return df["TABLE_NAME"].tolist()

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
            COLUMN_NAME,
            DATA_TYPE,
            IS_NULLABLE,
            COLUMN_DEFAULT
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = '{table_name}'
        AND TABLE_SCHEMA = '{self.config.schema}'
        ORDER BY ORDINAL_POSITION
        """
        return self.query(sql)

    def scale_warehouse(
        self,
        size: str,  # 'X-Small', 'Small', 'Medium', 'Large', 'X-Large', etc.
    ) -> None:
        """
        Scale warehouse size.

        Args:
            size: New warehouse size
        """
        sql = f"ALTER WAREHOUSE {self.config.warehouse} SET WAREHOUSE_SIZE = '{size}'"
        self.execute(sql)
        logger.info(f"Scaled warehouse {self.config.warehouse} to {size}")

    def suspend_warehouse(self) -> None:
        """Suspend the warehouse to save costs."""
        sql = f"ALTER WAREHOUSE {self.config.warehouse} SUSPEND"
        self.execute(sql)
        logger.info(f"Suspended warehouse {self.config.warehouse}")

    def resume_warehouse(self) -> None:
        """Resume the warehouse."""
        sql = f"ALTER WAREHOUSE {self.config.warehouse} RESUME"
        self.execute(sql)
        logger.info(f"Resumed warehouse {self.config.warehouse}")

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
        FROM marketing_performance
        WHERE date BETWEEN '{start_date}' AND '{end_date}'
        {channel_filter}
        ORDER BY date, channel
        """
        return self.query(sql)

    def get_sales_data(
        self,
        start_date: str,
        end_date: str,
        granularity: str = "daily",  # 'daily', 'weekly', 'monthly'
    ) -> pd.DataFrame:
        """
        Get sales data for forecasting.

        Args:
            start_date: Start date
            end_date: End date
            granularity: Time granularity

        Returns:
            DataFrame with sales data
        """
        date_trunc = {
            "daily": "DATE",
            "weekly": "WEEK",
            "monthly": "MONTH",
        }.get(granularity, "DATE")

        sql = f"""
        SELECT
            DATE_TRUNC('{date_trunc}', order_date) as date,
            SUM(quantity) as units,
            SUM(revenue) as revenue,
            COUNT(DISTINCT order_id) as orders,
            COUNT(DISTINCT customer_id) as customers
        FROM sales
        WHERE order_date BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY 1
        ORDER BY 1
        """
        return self.query(sql)
