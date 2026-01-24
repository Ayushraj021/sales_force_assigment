"""
Clean Room Providers

Implementations for various data clean room platforms.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import pandas as pd

from .clean_room import CleanRoomQuery, QueryResult, QueryType

logger = logging.getLogger(__name__)


@dataclass
class AWSCleanRoomConfig:
    """AWS Clean Rooms configuration."""
    collaboration_id: str
    membership_id: str
    region: str = "us-east-1"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None


class AWSCleanRoomProvider:
    """
    AWS Clean Rooms Provider.

    Integrates with AWS Clean Rooms for privacy-preserving data collaboration.
    """

    def __init__(self, config: AWSCleanRoomConfig):
        self.config = config
        self._client = None

        try:
            import boto3
            self._client = boto3.client(
                "cleanrooms",
                region_name=config.region,
                aws_access_key_id=config.aws_access_key_id,
                aws_secret_access_key=config.aws_secret_access_key,
            )
        except ImportError:
            logger.warning("boto3 not installed. Install with: pip install boto3")

    def connect(self) -> bool:
        """Test connection to AWS Clean Rooms."""
        if not self._client:
            return False

        try:
            self._client.get_collaboration(
                collaborationIdentifier=self.config.collaboration_id
            )
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    def execute_query(self, query: CleanRoomQuery) -> QueryResult:
        """Execute a query in AWS Clean Rooms."""
        if not self._client:
            return QueryResult(
                query_id=query.query_id,
                status="failed",
                error_message="AWS client not available",
            )

        try:
            # Build SQL from query
            sql = self._build_sql(query)

            # Start protected query
            response = self._client.start_protected_query(
                type="SQL",
                membershipIdentifier=self.config.membership_id,
                sqlParameters={"queryString": sql},
                resultConfiguration={
                    "outputConfiguration": {
                        "s3": {
                            "resultFormat": "CSV",
                            "bucket": "clean-room-results",
                            "keyPrefix": f"queries/{query.query_id}/",
                        }
                    }
                },
            )

            query_execution_id = response["protectedQuery"]["id"]

            # Wait for completion (simplified - should use waiter in production)
            import time
            for _ in range(60):
                status_response = self._client.get_protected_query(
                    membershipIdentifier=self.config.membership_id,
                    protectedQueryIdentifier=query_execution_id,
                )
                status = status_response["protectedQuery"]["status"]

                if status == "SUCCESS":
                    # Fetch results
                    result_s3_path = status_response["protectedQuery"]["result"]["output"]["s3"]["location"]
                    df = self._fetch_s3_results(result_s3_path)

                    return QueryResult(
                        query_id=query.query_id,
                        status="success",
                        row_count=len(df),
                        data=df,
                    )
                elif status in ("FAILED", "CANCELLED"):
                    return QueryResult(
                        query_id=query.query_id,
                        status="failed",
                        error_message=f"Query {status}",
                    )

                time.sleep(2)

            return QueryResult(
                query_id=query.query_id,
                status="failed",
                error_message="Query timeout",
            )

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return QueryResult(
                query_id=query.query_id,
                status="failed",
                error_message=str(e),
            )

    def _build_sql(self, query: CleanRoomQuery) -> str:
        """Build SQL from CleanRoomQuery."""
        # Build SELECT clause
        select_parts = []
        for col in query.select_columns:
            select_parts.append(col)
        for col, agg in query.aggregations.items():
            select_parts.append(f"{agg.value.upper()}(*) as {col}")

        select_clause = ", ".join(select_parts) or "*"

        # Build FROM clause
        from_clause = query.datasets[0]
        for i, dataset in enumerate(query.datasets[1:], 1):
            join_key = query.join_keys[0] if query.join_keys else "id"
            from_clause += f" JOIN {dataset} ON {query.datasets[0]}.{join_key} = {dataset}.{join_key}"

        # Build WHERE clause
        where_clause = ""
        if query.filters:
            conditions = [f"{k} = '{v}'" for k, v in query.filters.items()]
            where_clause = " WHERE " + " AND ".join(conditions)

        # Build GROUP BY clause
        group_clause = ""
        if query.group_by:
            group_clause = " GROUP BY " + ", ".join(query.group_by)

        return f"SELECT {select_clause} FROM {from_clause}{where_clause}{group_clause}"

    def _fetch_s3_results(self, s3_path: str) -> pd.DataFrame:
        """Fetch query results from S3."""
        import boto3
        s3 = boto3.client("s3")

        # Parse S3 path
        path_parts = s3_path.replace("s3://", "").split("/", 1)
        bucket = path_parts[0]
        key = path_parts[1]

        obj = s3.get_object(Bucket=bucket, Key=key)
        return pd.read_csv(obj["Body"])

    def list_datasets(self) -> List[str]:
        """List available datasets in the collaboration."""
        if not self._client:
            return []

        try:
            response = self._client.list_configured_tables(
                membershipIdentifier=self.config.membership_id
            )
            return [t["name"] for t in response.get("configuredTableSummaries", [])]
        except Exception as e:
            logger.error(f"Failed to list datasets: {e}")
            return []

    def get_schema(self, dataset: str) -> Dict[str, str]:
        """Get dataset schema."""
        if not self._client:
            return {}

        try:
            response = self._client.get_configured_table(
                configuredTableIdentifier=dataset
            )
            columns = response.get("configuredTable", {}).get("allowedColumns", [])
            return {col: "string" for col in columns}  # Simplified
        except Exception as e:
            logger.error(f"Failed to get schema: {e}")
            return {}


@dataclass
class SnowflakeCleanRoomConfig:
    """Snowflake Data Clean Room configuration."""
    account: str
    user: str
    password: str
    clean_room_name: str
    role: str = "CLEANROOM_ROLE"


class SnowflakeCleanRoomProvider:
    """
    Snowflake Data Clean Room Provider.

    Integrates with Snowflake's native clean room capabilities.
    """

    def __init__(self, config: SnowflakeCleanRoomConfig):
        self.config = config
        self._connection = None

        try:
            import snowflake.connector
            self._snowflake = snowflake.connector
        except ImportError:
            logger.warning("snowflake-connector-python not installed")
            self._snowflake = None

    def connect(self) -> bool:
        """Connect to Snowflake clean room."""
        if not self._snowflake:
            return False

        try:
            self._connection = self._snowflake.connect(
                account=self.config.account,
                user=self.config.user,
                password=self.config.password,
                role=self.config.role,
            )
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    def execute_query(self, query: CleanRoomQuery) -> QueryResult:
        """Execute a query in Snowflake clean room."""
        if not self._connection:
            return QueryResult(
                query_id=query.query_id,
                status="failed",
                error_message="Not connected",
            )

        try:
            cursor = self._connection.cursor()

            # Use clean room context
            cursor.execute(f"USE ROLE {self.config.role}")
            cursor.execute(f"CALL samooha_cleanroom.consumer.use_cleanroom('{self.config.clean_room_name}')")

            # Build and execute query
            sql = self._build_sql(query)
            cursor.execute(sql)

            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            df = pd.DataFrame(results, columns=columns)

            cursor.close()

            return QueryResult(
                query_id=query.query_id,
                status="success",
                row_count=len(df),
                data=df,
            )

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return QueryResult(
                query_id=query.query_id,
                status="failed",
                error_message=str(e),
            )

    def _build_sql(self, query: CleanRoomQuery) -> str:
        """Build SQL for Snowflake clean room."""
        # Similar to AWS implementation
        select_parts = []
        for col in query.select_columns:
            select_parts.append(col)
        for col, agg in query.aggregations.items():
            select_parts.append(f"{agg.value.upper()}(*) as {col}")

        select_clause = ", ".join(select_parts) or "*"
        from_clause = query.datasets[0]

        group_clause = ""
        if query.group_by:
            group_clause = " GROUP BY " + ", ".join(query.group_by)

        return f"SELECT {select_clause} FROM {from_clause}{group_clause}"

    def list_datasets(self) -> List[str]:
        """List available datasets."""
        if not self._connection:
            return []

        try:
            cursor = self._connection.cursor()
            cursor.execute(f"CALL samooha_cleanroom.consumer.list_available_tables('{self.config.clean_room_name}')")
            results = cursor.fetchall()
            cursor.close()
            return [r[0] for r in results]
        except Exception as e:
            logger.error(f"Failed to list datasets: {e}")
            return []

    def get_schema(self, dataset: str) -> Dict[str, str]:
        """Get dataset schema."""
        if not self._connection:
            return {}

        try:
            cursor = self._connection.cursor()
            cursor.execute(f"DESCRIBE TABLE {dataset}")
            results = cursor.fetchall()
            cursor.close()
            return {r[0]: r[1] for r in results}
        except Exception as e:
            logger.error(f"Failed to get schema: {e}")
            return {}


@dataclass
class GoogleAdsDataHubConfig:
    """Google Ads Data Hub configuration."""
    project_id: str
    credentials_path: str
    customer_id: str
    linked_accounts: List[str] = None


class GoogleAdsDataHubProvider:
    """
    Google Ads Data Hub Provider.

    Integrates with Google Ads Data Hub for privacy-safe ad measurement.
    """

    def __init__(self, config: GoogleAdsDataHubConfig):
        self.config = config
        self._client = None

        try:
            from google.cloud import bigquery
            from google.oauth2 import service_account

            credentials = service_account.Credentials.from_service_account_file(
                config.credentials_path
            )
            self._client = bigquery.Client(
                project=config.project_id,
                credentials=credentials,
            )
            self._bigquery = bigquery
        except ImportError:
            logger.warning("google-cloud-bigquery not installed")
            self._bigquery = None

    def connect(self) -> bool:
        """Test connection to Ads Data Hub."""
        if not self._client:
            return False

        try:
            # Test query to verify access
            query = "SELECT 1"
            self._client.query(query).result()
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    def execute_query(self, query: CleanRoomQuery) -> QueryResult:
        """Execute a query in Ads Data Hub."""
        if not self._client:
            return QueryResult(
                query_id=query.query_id,
                status="failed",
                error_message="Client not available",
            )

        try:
            sql = self._build_adh_sql(query)

            # Execute with privacy checks
            job_config = self._bigquery.QueryJobConfig(
                use_query_cache=False,
            )

            query_job = self._client.query(sql, job_config=job_config)
            df = query_job.to_dataframe()

            return QueryResult(
                query_id=query.query_id,
                status="success",
                row_count=len(df),
                data=df,
                metadata={"bytes_processed": query_job.total_bytes_processed},
            )

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return QueryResult(
                query_id=query.query_id,
                status="failed",
                error_message=str(e),
            )

    def _build_adh_sql(self, query: CleanRoomQuery) -> str:
        """Build SQL for Ads Data Hub."""
        # ADH requires specific table formats
        adh_tables = {
            "impressions": "adh.google_ads_impressions",
            "clicks": "adh.google_ads_clicks",
            "conversions": "adh.google_ads_conversions",
        }

        # Map query datasets to ADH tables
        from_tables = []
        for dataset in query.datasets:
            table = adh_tables.get(dataset, f"adh.{dataset}")
            from_tables.append(table)

        select_parts = []
        for col in query.select_columns:
            select_parts.append(col)
        for col, agg in query.aggregations.items():
            select_parts.append(f"{agg.value.upper()}(*) as {col}")

        select_clause = ", ".join(select_parts) or "COUNT(*) as user_count"
        from_clause = from_tables[0]

        group_clause = ""
        if query.group_by:
            group_clause = " GROUP BY " + ", ".join(query.group_by)

        # ADH requires HAVING clause for privacy
        having_clause = " HAVING COUNT(*) >= 50"

        return f"SELECT {select_clause} FROM {from_clause}{group_clause}{having_clause}"

    def list_datasets(self) -> List[str]:
        """List available ADH datasets."""
        return [
            "impressions",
            "clicks",
            "conversions",
            "youtube_impressions",
            "display_impressions",
        ]

    def get_schema(self, dataset: str) -> Dict[str, str]:
        """Get dataset schema."""
        # Return common ADH columns
        common_columns = {
            "user_id": "STRING",
            "impression_id": "STRING",
            "campaign_id": "INT64",
            "ad_group_id": "INT64",
            "timestamp": "TIMESTAMP",
            "device_type": "STRING",
            "geo_country": "STRING",
        }
        return common_columns
