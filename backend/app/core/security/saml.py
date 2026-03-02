"""
SAML SSO Authentication

Enterprise Single Sign-On using SAML 2.0 protocol.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
import base64
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


@dataclass
class SAMLConfig:
    """SAML configuration."""
    entity_id: str
    acs_url: str  # Assertion Consumer Service URL
    slo_url: Optional[str] = None  # Single Logout URL
    idp_entity_id: Optional[str] = None
    idp_sso_url: Optional[str] = None
    idp_slo_url: Optional[str] = None
    idp_certificate: Optional[str] = None
    sp_certificate: Optional[str] = None
    sp_private_key: Optional[str] = None
    name_id_format: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    authn_requests_signed: bool = True
    want_assertions_signed: bool = True
    want_assertions_encrypted: bool = False
    metadata_valid_secs: int = 86400
    attribute_mapping: Dict[str, str] = field(default_factory=lambda: {
        "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
        "first_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
        "last_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
        "groups": "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups",
    })


@dataclass
class SAMLUser:
    """User data from SAML assertion."""
    name_id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    groups: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    session_index: Optional[str] = None
    session_not_on_or_after: Optional[datetime] = None


@dataclass
class SAMLResponse:
    """Parsed SAML response."""
    user: SAMLUser
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    raw_response: Optional[str] = None


class SAMLProvider:
    """
    SAML 2.0 Service Provider.

    Features:
    - AuthnRequest generation
    - Response validation
    - Assertion parsing
    - Single Logout support
    - SP metadata generation

    Example:
        provider = SAMLProvider(config)
        auth_url = provider.create_authn_request()
        # After redirect...
        response = provider.process_response(saml_response)
        if response.is_valid:
            user = response.user
    """

    NAMESPACES = {
        "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
        "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
        "ds": "http://www.w3.org/2000/09/xmldsig#",
        "xenc": "http://www.w3.org/2001/04/xmlenc#",
        "md": "urn:oasis:names:tc:SAML:2.0:metadata",
    }

    def __init__(self, config: SAMLConfig):
        self.config = config
        self._onelogin_saml = None

        try:
            from onelogin.saml2.auth import OneLogin_Saml2_Auth
            from onelogin.saml2.settings import OneLogin_Saml2_Settings
            self._onelogin_saml = True
        except ImportError:
            logger.warning("python-saml not installed, using basic SAML support")

    def get_settings(self) -> Dict[str, Any]:
        """Get SAML settings for OneLogin library."""
        return {
            "strict": True,
            "debug": False,
            "sp": {
                "entityId": self.config.entity_id,
                "assertionConsumerService": {
                    "url": self.config.acs_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                },
                "singleLogoutService": {
                    "url": self.config.slo_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                } if self.config.slo_url else None,
                "NameIDFormat": self.config.name_id_format,
                "x509cert": self.config.sp_certificate or "",
                "privateKey": self.config.sp_private_key or "",
            },
            "idp": {
                "entityId": self.config.idp_entity_id or "",
                "singleSignOnService": {
                    "url": self.config.idp_sso_url or "",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "singleLogoutService": {
                    "url": self.config.idp_slo_url or "",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                } if self.config.idp_slo_url else None,
                "x509cert": self.config.idp_certificate or "",
            },
            "security": {
                "authnRequestsSigned": self.config.authn_requests_signed,
                "wantAssertionsSigned": self.config.want_assertions_signed,
                "wantAssertionsEncrypted": self.config.want_assertions_encrypted,
            },
        }

    def create_authn_request(
        self,
        relay_state: Optional[str] = None,
        force_authn: bool = False,
    ) -> str:
        """
        Create SAML AuthnRequest and return redirect URL.

        Args:
            relay_state: State to preserve across redirect
            force_authn: Force re-authentication

        Returns:
            Redirect URL to IdP
        """
        if self._onelogin_saml:
            return self._create_authn_request_onelogin(relay_state, force_authn)
        return self._create_authn_request_basic(relay_state)

    def _create_authn_request_onelogin(
        self,
        relay_state: Optional[str],
        force_authn: bool,
    ) -> str:
        """Create AuthnRequest using OneLogin library."""
        from onelogin.saml2.auth import OneLogin_Saml2_Auth

        # Create mock request for library
        request = {
            "https": "on",
            "http_host": self.config.entity_id.split("//")[1].split("/")[0],
            "script_name": "/saml",
            "get_data": {},
            "post_data": {},
        }

        auth = OneLogin_Saml2_Auth(request, self.get_settings())
        return auth.login(relay_state, force_authn=force_authn)

    def _create_authn_request_basic(self, relay_state: Optional[str]) -> str:
        """Create basic AuthnRequest (fallback)."""
        import uuid
        from urllib.parse import urlencode

        request_id = f"_id{uuid.uuid4().hex}"
        issue_instant = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        authn_request = f"""<samlp:AuthnRequest
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{issue_instant}"
    Destination="{self.config.idp_sso_url}"
    AssertionConsumerServiceURL="{self.config.acs_url}"
    ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
    <saml:Issuer>{self.config.entity_id}</saml:Issuer>
    <samlp:NameIDPolicy Format="{self.config.name_id_format}" AllowCreate="true"/>
</samlp:AuthnRequest>"""

        encoded_request = base64.b64encode(authn_request.encode()).decode()
        params = {"SAMLRequest": encoded_request}
        if relay_state:
            params["RelayState"] = relay_state

        return f"{self.config.idp_sso_url}?{urlencode(params)}"

    def process_response(
        self,
        saml_response: str,
        request_id: Optional[str] = None,
    ) -> SAMLResponse:
        """
        Process SAML response from IdP.

        Args:
            saml_response: Base64 encoded SAML response
            request_id: Expected request ID for validation

        Returns:
            SAMLResponse with user data
        """
        if self._onelogin_saml:
            return self._process_response_onelogin(saml_response, request_id)
        return self._process_response_basic(saml_response)

    def _process_response_onelogin(
        self,
        saml_response: str,
        request_id: Optional[str],
    ) -> SAMLResponse:
        """Process response using OneLogin library."""
        from onelogin.saml2.auth import OneLogin_Saml2_Auth

        request = {
            "https": "on",
            "http_host": self.config.entity_id.split("//")[1].split("/")[0],
            "script_name": "/saml/acs",
            "get_data": {},
            "post_data": {"SAMLResponse": saml_response},
        }

        auth = OneLogin_Saml2_Auth(request, self.get_settings())
        auth.process_response(request_id=request_id)
        errors = auth.get_errors()

        if errors:
            return SAMLResponse(
                user=SAMLUser(name_id="", email=""),
                is_valid=False,
                errors=list(errors),
                raw_response=saml_response,
            )

        # Extract user data
        attributes = auth.get_attributes()
        name_id = auth.get_nameid()

        user = SAMLUser(
            name_id=name_id,
            email=self._get_attribute(attributes, "email") or name_id,
            first_name=self._get_attribute(attributes, "first_name"),
            last_name=self._get_attribute(attributes, "last_name"),
            groups=self._get_attribute_list(attributes, "groups"),
            attributes=attributes,
            session_index=auth.get_session_index(),
            session_not_on_or_after=auth.get_session_expiration(),
        )

        return SAMLResponse(
            user=user,
            is_valid=True,
            raw_response=saml_response,
        )

    def _process_response_basic(self, saml_response: str) -> SAMLResponse:
        """Basic response processing (fallback)."""
        try:
            decoded = base64.b64decode(saml_response)
            root = ET.fromstring(decoded)

            # Extract NameID
            name_id_elem = root.find(".//saml:NameID", self.NAMESPACES)
            name_id = name_id_elem.text if name_id_elem is not None else ""

            # Extract attributes
            attributes = {}
            for attr in root.findall(".//saml:Attribute", self.NAMESPACES):
                name = attr.get("Name", "")
                values = [v.text for v in attr.findall("saml:AttributeValue", self.NAMESPACES) if v.text]
                attributes[name] = values[0] if len(values) == 1 else values

            user = SAMLUser(
                name_id=name_id,
                email=self._get_mapped_attribute(attributes, "email") or name_id,
                first_name=self._get_mapped_attribute(attributes, "first_name"),
                last_name=self._get_mapped_attribute(attributes, "last_name"),
                groups=self._get_mapped_attribute_list(attributes, "groups"),
                attributes=attributes,
            )

            return SAMLResponse(user=user, is_valid=True, raw_response=saml_response)

        except Exception as e:
            logger.error(f"SAML response parsing failed: {e}")
            return SAMLResponse(
                user=SAMLUser(name_id="", email=""),
                is_valid=False,
                errors=[str(e)],
                raw_response=saml_response,
            )

    def _get_attribute(self, attributes: Dict, key: str) -> Optional[str]:
        """Get attribute by mapped key."""
        mapped_key = self.config.attribute_mapping.get(key, key)
        value = attributes.get(mapped_key, [])
        return value[0] if value else None

    def _get_attribute_list(self, attributes: Dict, key: str) -> List[str]:
        """Get attribute list by mapped key."""
        mapped_key = self.config.attribute_mapping.get(key, key)
        return attributes.get(mapped_key, [])

    def _get_mapped_attribute(self, attributes: Dict, key: str) -> Optional[str]:
        """Get attribute by mapped key from raw attributes."""
        mapped_key = self.config.attribute_mapping.get(key, key)
        value = attributes.get(mapped_key)
        if isinstance(value, list):
            return value[0] if value else None
        return value

    def _get_mapped_attribute_list(self, attributes: Dict, key: str) -> List[str]:
        """Get attribute list by mapped key from raw attributes."""
        mapped_key = self.config.attribute_mapping.get(key, key)
        value = attributes.get(mapped_key)
        if isinstance(value, list):
            return value
        return [value] if value else []

    def create_logout_request(
        self,
        name_id: str,
        session_index: Optional[str] = None,
    ) -> str:
        """
        Create SAML logout request.

        Args:
            name_id: User's NameID
            session_index: Session index from login

        Returns:
            Redirect URL for logout
        """
        import uuid
        from urllib.parse import urlencode

        request_id = f"_id{uuid.uuid4().hex}"
        issue_instant = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        session_index_xml = f'<samlp:SessionIndex>{session_index}</samlp:SessionIndex>' if session_index else ""

        logout_request = f"""<samlp:LogoutRequest
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{issue_instant}"
    Destination="{self.config.idp_slo_url}">
    <saml:Issuer>{self.config.entity_id}</saml:Issuer>
    <saml:NameID Format="{self.config.name_id_format}">{name_id}</saml:NameID>
    {session_index_xml}
</samlp:LogoutRequest>"""

        encoded_request = base64.b64encode(logout_request.encode()).decode()
        return f"{self.config.idp_slo_url}?{urlencode({'SAMLRequest': encoded_request})}"

    def generate_metadata(self) -> str:
        """
        Generate SP metadata XML.

        Returns:
            SP metadata as XML string
        """
        valid_until = (datetime.utcnow() + timedelta(seconds=self.config.metadata_valid_secs)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

        cert_section = ""
        if self.config.sp_certificate:
            cert_data = self.config.sp_certificate.replace("-----BEGIN CERTIFICATE-----", "").replace(
                "-----END CERTIFICATE-----", ""
            ).replace("\n", "")
            cert_section = f"""<md:KeyDescriptor use="signing">
            <ds:KeyInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
                <ds:X509Data>
                    <ds:X509Certificate>{cert_data}</ds:X509Certificate>
                </ds:X509Data>
            </ds:KeyInfo>
        </md:KeyDescriptor>"""

        slo_section = ""
        if self.config.slo_url:
            slo_section = f"""<md:SingleLogoutService
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            Location="{self.config.slo_url}"/>"""

        metadata = f"""<?xml version="1.0" encoding="UTF-8"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
    entityID="{self.config.entity_id}"
    validUntil="{valid_until}">
    <md:SPSSODescriptor
        AuthnRequestsSigned="{str(self.config.authn_requests_signed).lower()}"
        WantAssertionsSigned="{str(self.config.want_assertions_signed).lower()}"
        protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        {cert_section}
        {slo_section}
        <md:NameIDFormat>{self.config.name_id_format}</md:NameIDFormat>
        <md:AssertionConsumerService
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
            Location="{self.config.acs_url}"
            index="0"
            isDefault="true"/>
    </md:SPSSODescriptor>
</md:EntityDescriptor>"""

        return metadata


# Pre-configured IdP settings
class IdentityProviders:
    """Common IdP configurations."""

    @staticmethod
    def azure_ad(tenant_id: str) -> Dict[str, str]:
        """Azure AD (Entra ID) configuration."""
        return {
            "idp_entity_id": f"https://sts.windows.net/{tenant_id}/",
            "idp_sso_url": f"https://login.microsoftonline.com/{tenant_id}/saml2",
            "idp_slo_url": f"https://login.microsoftonline.com/{tenant_id}/saml2",
        }

    @staticmethod
    def okta(domain: str) -> Dict[str, str]:
        """Okta configuration."""
        return {
            "idp_entity_id": f"http://www.okta.com/{domain}",
            "idp_sso_url": f"https://{domain}.okta.com/app/saml2/sso",
            "idp_slo_url": f"https://{domain}.okta.com/app/saml2/slo",
        }

    @staticmethod
    def onelogin(subdomain: str) -> Dict[str, str]:
        """OneLogin configuration."""
        return {
            "idp_entity_id": f"https://app.onelogin.com/saml/metadata/{subdomain}",
            "idp_sso_url": f"https://{subdomain}.onelogin.com/trust/saml2/http-redirect/sso",
            "idp_slo_url": f"https://{subdomain}.onelogin.com/trust/saml2/http-redirect/slo",
        }

    @staticmethod
    def google_workspace(domain: str) -> Dict[str, str]:
        """Google Workspace configuration."""
        return {
            "idp_entity_id": f"https://accounts.google.com/o/saml2?idpid={domain}",
            "idp_sso_url": f"https://accounts.google.com/o/saml2/idp?idpid={domain}",
            "idp_slo_url": "",  # Google doesn't support SLO
        }
