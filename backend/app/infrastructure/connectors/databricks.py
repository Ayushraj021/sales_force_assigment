"""
Databricks Connector

Connects to Databricks for data import/export and analytics.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Iterator
import logging
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class DatabricksConfig:
    """Databricks connection configuration."""
    host: str  # e.g., "adb-xxx.azuredatabricks.net"
    token: str  # Personal access token
    http_path: str  # SQL warehouse HTTP path
    catalog: str = "main"
    schema: str = "default"


class DatabricksConnector:
    """
    Databricks Connector.

    Features:
    - Query execution via SQL warehouse
    - Unity Catalog integration
    - Delta table operations
    - MLflow integration

    Example:
        config = DatabricksConfig(
            host="adb-xxx.azuredatabricks.net",
            token="dapi...",
            http_path="/sql/1.0/warehouses/xxx",
            catalog="analytics",
            schema="marketing",
        )
        connector = DatabricksConnector(config)

        # Query data
        df = connector.query("SELECT * FROM campaigns WHERE year = 2024")

        # Write to Delta table
        connector.write_dataframe(df, "campaign_results")
    """

    def __init__(self, config: DatabricksConfig):
        self.config = config
        self._connection = None

        try:
            from databricks import sql
            self._databricks_sql = sql
        except ImportError:
            logger.warning(
                "databricks-sql-connector not installed. "
                "Install with: pip install databricks-sql-connector"
            )
            self._databricks_sql = None

    def _get_connection(self):
        """Get Databricks SQL connection."""
        if self._databricks_sql is None:
            raise RuntimeError("Databricks SQL connector not available")

        if self._connection is None:
            self._connection = self._databricks_sql.connect(
                server_hostname=self.config.host,
                http_path=self.config.http_path,
                access_token=self.config.token,
            )

        return self._connection

    def close(self):
        """Close the connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

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
        conn = self._get_connection()
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
        conn = self._get_connection()
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
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
        finally:
            cursor.close()

    def write_dataframe(
        self,
        df: pd.DataFrame,
        table_name: str,
        mode: str = "append",  # 'append', 'overwrite', 'error'
    ) -> int:
        """
        Write DataFrame to Delta table.

        Args:
            df: DataFrame to write
            table_name: Target table name
            mode: Write mode (append, overwrite, error)

        Returns:
            Number of rows written
        """
        full_table_name = f"{self.config.catalog}.{self.config.schema}.{table_name}"

        # Create temp view and insert
        # For production, use Spark DataFrame API via Databricks Connect
        if mode == "overwrite":
            self.execute(f"DROP TABLE IF EXISTS {full_table_name}")

        # Generate CREATE TABLE if needed
        create_sql = self._generate_create_table(df, full_table_name)
        self.execute(f"CREATE TABLE IF NOT EXISTS {full_table_name} AS {create_sql} WHERE 1=0")

        # Insert data using VALUES
        if len(df) > 0:
            columns = ", ".join([f"`{c}`" for c in df.columns])

            # Batch insert
            batch_size = 1000
            for start in range(0, len(df), batch_size):
                batch = df.iloc[start:start + batch_size]
                values = []
                for _, row in batch.iterrows():
                    row_values = []
                    for val in row:
                        if pd.isna(val):
                            row_values.append("NULL")
                        elif isinstance(val, str):
                            row_values.append(f"'{val}'")
                        else:
                            row_values.append(str(val))
                    values.append(f"({', '.join(row_values)})")

                insert_sql = f"""
                INSERT INTO {full_table_name} ({columns})
                VALUES {', '.join(values)}
                """
                self.execute(insert_sql)

        logger.info(f"Wrote {len(df)} rows to {full_table_name}")
        return len(df)

    def _generate_create_table(
        self,
        df: pd.DataFrame,
        table_name: str,
    ) -> str:
        """Generate SELECT statement to derive schema."""
        columns = []
        for col in df.columns:
            dtype = str(df[col].dtype)
            if "int" in dtype:
                columns.append(f"CAST(NULL AS BIGINT) AS `{col}`")
            elif "float" in dtype:
                columns.append(f"CAST(NULL AS DOUBLE) AS `{col}`")
            elif "bool" in dtype:
                columns.append(f"CAST(NULL AS BOOLEAN) AS `{col}`")
            elif "datetime" in dtype:
                columns.append(f"CAST(NULL AS TIMESTAMP) AS `{col}`")
            else:
                columns.append(f"CAST(NULL AS STRING) AS `{col}`")

        return f"SELECT {', '.join(columns)}"

    def get_catalogs(self) -> List[str]:
        """
        List catalogs in Unity Catalog.

        Returns:
            List of catalog names
        """
        df = self.query("SHOW CATALOGS")
        return df["catalog"].tolist()

    def get_schemas(self, catalog: Optional[str] = None) -> List[str]:
        """
        List schemas in catalog.

        Args:
            catalog: Catalog name (default: configured catalog)

        Returns:
            List of schema names
        """
        catalog = catalog or self.config.catalog
        df = self.query(f"SHOW SCHEMAS IN {catalog}")
        return df["databaseName"].tolist()

    def get_tables(
        self,
        catalog: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> List[str]:
        """
        List tables in schema.

        Args:
            catalog: Catalog name
            schema: Schema name

        Returns:
            List of table names
        """
        catalog = catalog or self.config.catalog
        schema = schema or self.config.schema
        df = self.query(f"SHOW TABLES IN {catalog}.{schema}")
        return df["tableName"].tolist()

    def get_table_schema(self, table_name: str) -> pd.DataFrame:
        """
        Get table schema/columns.

        Args:
            table_name: Table name

        Returns:
            DataFrame with column info
        """
        full_name = f"{self.config.catalog}.{self.config.schema}.{table_name}"
        return self.query(f"DESCRIBE TABLE {full_name}")

    def get_table_history(self, table_name: str) -> pd.DataFrame:
        """
        Get Delta table history.

        Args:
            table_name: Table name

        Returns:
            DataFrame with version history
        """
        full_name = f"{self.config.catalog}.{self.config.schema}.{table_name}"
        return self.query(f"DESCRIBE HISTORY {full_name}")

    def optimize_table(self, table_name: str, z_order_cols: Optional[List[str]] = None) -> None:
        """
        Optimize Delta table (compaction and Z-ordering).

        Args:
            table_name: Table name
            z_order_cols: Columns to Z-order by
        """
        full_name = f"{self.config.catalog}.{self.config.schema}.{table_name}"
        sql = f"OPTIMIZE {full_name}"

        if z_order_cols:
            cols = ", ".join(z_order_cols)
            sql += f" ZORDER BY ({cols})"

        self.execute(sql)
        logger.info(f"Optimized table {table_name}")

    def vacuum_table(self, table_name: str, retention_hours: int = 168) -> None:
        """
        Vacuum Delta table to remove old files.

        Args:
            table_name: Table name
            retention_hours: Retention period in hours (default: 7 days)
        """
        full_name = f"{self.config.catalog}.{self.config.schema}.{table_name}"
        self.execute(f"VACUUM {full_name} RETAIN {retention_hours} HOURS")
        logger.info(f"Vacuumed table {table_name}")

    def time_travel_query(
        self,
        table_name: str,
        version: Optional[int] = None,
        timestamp: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Query table at a specific version or timestamp.

        Args:
            table_name: Table name
            version: Version number
            timestamp: Timestamp string

        Returns:
            DataFrame with results
        """
        full_name = f"{self.config.catalog}.{self.config.schema}.{table_name}"

        if version is not None:
            sql = f"SELECT * FROM {full_name} VERSION AS OF {version}"
        elif timestamp:
            sql = f"SELECT * FROM {full_name} TIMESTAMP AS OF '{timestamp}'"
        else:
            sql = f"SELECT * FROM {full_name}"

        return self.query(sql)

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
        full_name = f"{self.config.catalog}.{self.config.schema}.marketing_performance"
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
        FROM {full_name}
        WHERE date BETWEEN '{start_date}' AND '{end_date}'
        {channel_filter}
        ORDER BY date, channel
        """
        return self.query(sql)

    def run_sql_file(self, file_path: str) -> None:
        """
        Execute SQL from a file.

        Args:
            file_path: Path to SQL file
        """
        with open(file_path, "r") as f:
            sql = f.read()

        # Split by semicolon and execute each statement
        statements = [s.strip() for s in sql.split(";") if s.strip()]
        for stmt in statements:
            self.execute(stmt)

        logger.info(f"Executed {len(statements)} statements from {file_path}")
