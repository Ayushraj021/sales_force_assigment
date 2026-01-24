"""
Salesforce CRM Connector

Integrates with Salesforce for customer and sales data.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import logging
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class SalesforceConfig:
    """Salesforce connection configuration."""
    username: str
    password: str
    security_token: str
    domain: str = "login"  # "login" or "test"
    client_id: Optional[str] = None
    client_secret: Optional[str] = None


class SalesforceConnector:
    """
    Salesforce CRM Connector.

    Features:
    - SOQL queries
    - Object CRUD operations
    - Bulk data operations
    - Report access

    Example:
        connector = SalesforceConnector(config)
        accounts = connector.query("SELECT Id, Name FROM Account LIMIT 10")
    """

    def __init__(self, config: SalesforceConfig):
        self.config = config
        self._sf = None

        try:
            from simple_salesforce import Salesforce
            self._sf = Salesforce(
                username=config.username,
                password=config.password,
                security_token=config.security_token,
                domain=config.domain,
            )
        except ImportError:
            logger.warning("simple-salesforce not installed")
        except Exception as e:
            logger.error(f"Failed to connect to Salesforce: {e}")

    def query(self, soql: str) -> pd.DataFrame:
        """
        Execute SOQL query.

        Args:
            soql: SOQL query string

        Returns:
            DataFrame with results
        """
        if not self._sf:
            return self._mock_query(soql)

        try:
            result = self._sf.query_all(soql)
            records = result.get("records", [])

            # Remove attributes
            for record in records:
                record.pop("attributes", None)

            return pd.DataFrame(records)
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return pd.DataFrame()

    def _mock_query(self, soql: str) -> pd.DataFrame:
        """Generate mock data for testing."""
        import random

        if "Account" in soql:
            return pd.DataFrame({
                "Id": [f"001{i:015d}" for i in range(10)],
                "Name": [f"Account {i}" for i in range(10)],
                "Industry": random.choices(["Tech", "Finance", "Healthcare"], k=10),
                "AnnualRevenue": [random.randint(100000, 10000000) for _ in range(10)],
            })
        elif "Opportunity" in soql:
            return pd.DataFrame({
                "Id": [f"006{i:015d}" for i in range(10)],
                "Name": [f"Opportunity {i}" for i in range(10)],
                "Amount": [random.randint(10000, 500000) for _ in range(10)],
                "StageName": random.choices(["Prospecting", "Negotiation", "Closed Won"], k=10),
            })
        elif "Lead" in soql:
            return pd.DataFrame({
                "Id": [f"00Q{i:015d}" for i in range(10)],
                "Name": [f"Lead {i}" for i in range(10)],
                "Company": [f"Company {i}" for i in range(10)],
                "Status": random.choices(["New", "Contacted", "Qualified"], k=10),
            })

        return pd.DataFrame()

    def get_object(self, object_name: str, record_id: str) -> Dict[str, Any]:
        """Get a single record."""
        if not self._sf:
            return {"Id": record_id, "Name": f"Mock {object_name}"}

        obj = getattr(self._sf, object_name)
        return obj.get(record_id)

    def create_object(self, object_name: str, data: Dict[str, Any]) -> str:
        """Create a new record."""
        if not self._sf:
            return "mock_id_001"

        obj = getattr(self._sf, object_name)
        result = obj.create(data)
        return result.get("id")

    def update_object(self, object_name: str, record_id: str, data: Dict[str, Any]) -> bool:
        """Update a record."""
        if not self._sf:
            return True

        obj = getattr(self._sf, object_name)
        obj.update(record_id, data)
        return True

    def delete_object(self, object_name: str, record_id: str) -> bool:
        """Delete a record."""
        if not self._sf:
            return True

        obj = getattr(self._sf, object_name)
        obj.delete(record_id)
        return True

    def get_accounts(self, limit: int = 100) -> pd.DataFrame:
        """Get accounts."""
        soql = f"""
        SELECT Id, Name, Industry, AnnualRevenue, NumberOfEmployees,
               BillingCity, BillingCountry, CreatedDate
        FROM Account
        ORDER BY AnnualRevenue DESC
        LIMIT {limit}
        """
        return self.query(soql)

    def get_opportunities(
        self,
        stage: Optional[str] = None,
        limit: int = 100,
    ) -> pd.DataFrame:
        """Get opportunities."""
        stage_filter = f"AND StageName = '{stage}'" if stage else ""
        soql = f"""
        SELECT Id, Name, Amount, StageName, CloseDate, AccountId,
               Probability, ForecastCategory, CreatedDate
        FROM Opportunity
        WHERE IsClosed = false
        {stage_filter}
        ORDER BY Amount DESC
        LIMIT {limit}
        """
        return self.query(soql)

    def get_leads(
        self,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> pd.DataFrame:
        """Get leads."""
        status_filter = f"AND Status = '{status}'" if status else ""
        soql = f"""
        SELECT Id, Name, Company, Email, Phone, Status,
               LeadSource, Industry, CreatedDate
        FROM Lead
        WHERE IsConverted = false
        {status_filter}
        ORDER BY CreatedDate DESC
        LIMIT {limit}
        """
        return self.query(soql)

    def get_campaign_members(self, campaign_id: str) -> pd.DataFrame:
        """Get campaign members."""
        soql = f"""
        SELECT Id, ContactId, LeadId, Status, FirstRespondedDate
        FROM CampaignMember
        WHERE CampaignId = '{campaign_id}'
        """
        return self.query(soql)

    def describe_object(self, object_name: str) -> Dict[str, Any]:
        """Get object metadata."""
        if not self._sf:
            return {"name": object_name, "fields": []}

        obj = getattr(self._sf, object_name)
        return obj.describe()
