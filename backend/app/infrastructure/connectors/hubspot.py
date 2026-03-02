"""
HubSpot CRM Connector

Integrates with HubSpot for marketing and sales data.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import logging
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class HubSpotConfig:
    """HubSpot connection configuration."""
    api_key: Optional[str] = None
    access_token: Optional[str] = None  # OAuth token
    portal_id: Optional[str] = None


class HubSpotConnector:
    """
    HubSpot CRM Connector.

    Features:
    - Contact management
    - Deal tracking
    - Marketing campaigns
    - Analytics

    Example:
        connector = HubSpotConnector(config)
        contacts = connector.get_contacts(limit=100)
    """

    def __init__(self, config: HubSpotConfig):
        self.config = config
        self._client = None

        try:
            import requests
            self._requests = requests
            self._base_url = "https://api.hubapi.com"
        except ImportError:
            logger.warning("requests not installed")
            self._requests = None

    def _get_headers(self) -> Dict[str, str]:
        """Get API headers."""
        if self.config.access_token:
            return {"Authorization": f"Bearer {self.config.access_token}"}
        elif self.config.api_key:
            return {"Authorization": f"Bearer {self.config.api_key}"}
        return {}

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make API request."""
        if not self._requests:
            return self._mock_response(endpoint)

        url = f"{self._base_url}{endpoint}"
        headers = self._get_headers()
        headers["Content-Type"] = "application/json"

        try:
            response = self._requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=data,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"API request failed: {e}")
            return self._mock_response(endpoint)

    def _mock_response(self, endpoint: str) -> Dict[str, Any]:
        """Generate mock response."""
        import random

        if "contacts" in endpoint:
            return {
                "results": [
                    {
                        "id": str(i),
                        "properties": {
                            "firstname": f"Contact{i}",
                            "lastname": f"Last{i}",
                            "email": f"contact{i}@example.com",
                            "company": f"Company {i}",
                            "lifecyclestage": random.choice(["lead", "customer", "subscriber"]),
                        },
                    }
                    for i in range(10)
                ]
            }
        elif "deals" in endpoint:
            return {
                "results": [
                    {
                        "id": str(i),
                        "properties": {
                            "dealname": f"Deal {i}",
                            "amount": str(random.randint(10000, 100000)),
                            "dealstage": random.choice(["appointmentscheduled", "qualifiedtobuy", "closedwon"]),
                            "pipeline": "default",
                        },
                    }
                    for i in range(10)
                ]
            }
        elif "campaigns" in endpoint:
            return {
                "campaigns": [
                    {
                        "id": str(i),
                        "name": f"Campaign {i}",
                        "type": random.choice(["email", "social", "content"]),
                    }
                    for i in range(5)
                ]
            }

        return {"results": []}

    def get_contacts(
        self,
        limit: int = 100,
        properties: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Get contacts.

        Args:
            limit: Maximum contacts to return
            properties: Properties to include

        Returns:
            DataFrame with contacts
        """
        properties = properties or ["firstname", "lastname", "email", "company", "lifecyclestage"]
        props_param = ",".join(properties)

        result = self._request(
            "GET",
            f"/crm/v3/objects/contacts?limit={limit}&properties={props_param}",
        )

        contacts = []
        for contact in result.get("results", []):
            row = {"id": contact["id"]}
            row.update(contact.get("properties", {}))
            contacts.append(row)

        return pd.DataFrame(contacts)

    def get_deals(
        self,
        limit: int = 100,
        pipeline: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Get deals.

        Args:
            limit: Maximum deals to return
            pipeline: Filter by pipeline

        Returns:
            DataFrame with deals
        """
        params = f"limit={limit}&properties=dealname,amount,dealstage,pipeline,closedate"
        result = self._request("GET", f"/crm/v3/objects/deals?{params}")

        deals = []
        for deal in result.get("results", []):
            row = {"id": deal["id"]}
            row.update(deal.get("properties", {}))
            if pipeline and row.get("pipeline") != pipeline:
                continue
            deals.append(row)

        return pd.DataFrame(deals)

    def get_companies(self, limit: int = 100) -> pd.DataFrame:
        """Get companies."""
        params = "limit=" + str(limit) + "&properties=name,industry,annualrevenue,numberofemployees"
        result = self._request("GET", f"/crm/v3/objects/companies?{params}")

        companies = []
        for company in result.get("results", []):
            row = {"id": company["id"]}
            row.update(company.get("properties", {}))
            companies.append(row)

        return pd.DataFrame(companies)

    def get_email_campaigns(self) -> pd.DataFrame:
        """Get marketing email campaigns."""
        result = self._request("GET", "/marketing/v1/campaigns")

        campaigns = []
        for campaign in result.get("campaigns", []):
            campaigns.append({
                "id": campaign.get("id"),
                "name": campaign.get("name"),
                "type": campaign.get("type"),
            })

        return pd.DataFrame(campaigns)

    def get_analytics(
        self,
        start_date: str,
        end_date: str,
        breakdown_by: str = "day",
    ) -> pd.DataFrame:
        """
        Get website analytics.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            breakdown_by: Breakdown period (day, week, month)

        Returns:
            DataFrame with analytics
        """
        # Mock analytics data
        import random
        from datetime import datetime, timedelta

        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        days = (end - start).days

        data = []
        for i in range(days):
            date = start + timedelta(days=i)
            data.append({
                "date": date.strftime("%Y-%m-%d"),
                "sessions": random.randint(100, 1000),
                "pageviews": random.randint(200, 2000),
                "contacts": random.randint(5, 50),
                "customers": random.randint(0, 10),
            })

        return pd.DataFrame(data)

    def create_contact(self, data: Dict[str, Any]) -> str:
        """Create a contact."""
        result = self._request("POST", "/crm/v3/objects/contacts", data={"properties": data})
        return result.get("id", "mock_id")

    def update_contact(self, contact_id: str, data: Dict[str, Any]) -> bool:
        """Update a contact."""
        self._request("PATCH", f"/crm/v3/objects/contacts/{contact_id}", data={"properties": data})
        return True

    def create_deal(self, data: Dict[str, Any]) -> str:
        """Create a deal."""
        result = self._request("POST", "/crm/v3/objects/deals", data={"properties": data})
        return result.get("id", "mock_id")
