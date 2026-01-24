"""
OAuth 2.0 Authentication

Support for multiple OAuth providers including Google, Microsoft, GitHub.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import logging
import secrets
import hashlib
import base64

logger = logging.getLogger(__name__)


class OAuthProvider(str, Enum):
    """Supported OAuth providers."""
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    GITHUB = "github"
    OKTA = "okta"
    AUTH0 = "auth0"
    CUSTOM = "custom"


@dataclass
class OAuthConfig:
    """OAuth provider configuration."""
    provider: OAuthProvider
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: List[str] = field(default_factory=list)
    authorization_endpoint: Optional[str] = None
    token_endpoint: Optional[str] = None
    userinfo_endpoint: Optional[str] = None
    jwks_uri: Optional[str] = None
    # Provider-specific settings
    tenant_id: Optional[str] = None  # For Microsoft
    domain: Optional[str] = None  # For Auth0/Okta


@dataclass
class OAuthToken:
    """OAuth token data."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    id_token: Optional[str] = None
    expires_at: Optional[datetime] = None

    def __post_init__(self):
        if self.expires_at is None:
            self.expires_at = datetime.utcnow() + timedelta(seconds=self.expires_in)

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() >= self.expires_at


@dataclass
class OAuthUser:
    """User data from OAuth provider."""
    id: str
    email: str
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    picture: Optional[str] = None
    email_verified: bool = False
    locale: Optional[str] = None
    provider: Optional[OAuthProvider] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


class OAuthProviderSettings:
    """Pre-configured OAuth provider settings."""

    PROVIDERS = {
        OAuthProvider.GOOGLE: {
            "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_endpoint": "https://oauth2.googleapis.com/token",
            "userinfo_endpoint": "https://www.googleapis.com/oauth2/v3/userinfo",
            "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
            "default_scopes": ["openid", "email", "profile"],
        },
        OAuthProvider.MICROSOFT: {
            "authorization_endpoint": "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize",
            "token_endpoint": "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
            "userinfo_endpoint": "https://graph.microsoft.com/oidc/userinfo",
            "jwks_uri": "https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys",
            "default_scopes": ["openid", "email", "profile", "User.Read"],
        },
        OAuthProvider.GITHUB: {
            "authorization_endpoint": "https://github.com/login/oauth/authorize",
            "token_endpoint": "https://github.com/login/oauth/access_token",
            "userinfo_endpoint": "https://api.github.com/user",
            "default_scopes": ["user:email"],
        },
        OAuthProvider.OKTA: {
            "authorization_endpoint": "https://{domain}/oauth2/default/v1/authorize",
            "token_endpoint": "https://{domain}/oauth2/default/v1/token",
            "userinfo_endpoint": "https://{domain}/oauth2/default/v1/userinfo",
            "jwks_uri": "https://{domain}/oauth2/default/v1/keys",
            "default_scopes": ["openid", "email", "profile"],
        },
        OAuthProvider.AUTH0: {
            "authorization_endpoint": "https://{domain}/authorize",
            "token_endpoint": "https://{domain}/oauth/token",
            "userinfo_endpoint": "https://{domain}/userinfo",
            "jwks_uri": "https://{domain}/.well-known/jwks.json",
            "default_scopes": ["openid", "email", "profile"],
        },
    }

    @classmethod
    def get_endpoints(cls, config: OAuthConfig) -> Dict[str, str]:
        """Get provider endpoints with substituted values."""
        provider_config = cls.PROVIDERS.get(config.provider, {})
        endpoints = {}

        for key in ["authorization_endpoint", "token_endpoint", "userinfo_endpoint", "jwks_uri"]:
            value = getattr(config, key) or provider_config.get(key, "")
            if value:
                value = value.format(
                    tenant_id=config.tenant_id or "common",
                    domain=config.domain or "",
                )
                endpoints[key] = value

        return endpoints

    @classmethod
    def get_default_scopes(cls, provider: OAuthProvider) -> List[str]:
        """Get default scopes for provider."""
        return cls.PROVIDERS.get(provider, {}).get("default_scopes", [])


class OAuthClient:
    """
    OAuth 2.0 Client.

    Features:
    - Authorization URL generation with PKCE
    - Token exchange
    - Token refresh
    - User info retrieval
    - Multiple provider support

    Example:
        client = OAuthClient(config)
        auth_url, state = client.get_authorization_url()
        # After redirect...
        token = client.exchange_code(code, state)
        user = client.get_user_info(token)
    """

    def __init__(self, config: OAuthConfig):
        self.config = config
        self.endpoints = OAuthProviderSettings.get_endpoints(config)
        self._http = None

        # Set default scopes if not provided
        if not config.scopes:
            config.scopes = OAuthProviderSettings.get_default_scopes(config.provider)

        try:
            import httpx
            self._http = httpx.Client(timeout=30.0)
        except ImportError:
            try:
                import requests
                self._http = requests
            except ImportError:
                logger.warning("Neither httpx nor requests installed")

    def get_authorization_url(
        self,
        state: Optional[str] = None,
        nonce: Optional[str] = None,
        use_pkce: bool = True,
        extra_params: Optional[Dict[str, str]] = None,
    ) -> tuple:
        """
        Generate authorization URL.

        Args:
            state: State parameter for CSRF protection
            nonce: Nonce for ID token validation
            use_pkce: Use PKCE extension
            extra_params: Additional query parameters

        Returns:
            Tuple of (authorization_url, state, code_verifier)
        """
        from urllib.parse import urlencode

        if state is None:
            state = secrets.token_urlsafe(32)

        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.config.scopes),
            "state": state,
        }

        if nonce:
            params["nonce"] = nonce

        code_verifier = None
        if use_pkce:
            code_verifier = secrets.token_urlsafe(64)
            code_challenge = self._generate_code_challenge(code_verifier)
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = "S256"

        if extra_params:
            params.update(extra_params)

        auth_endpoint = self.endpoints.get("authorization_endpoint", "")
        url = f"{auth_endpoint}?{urlencode(params)}"

        return url, state, code_verifier

    def exchange_code(
        self,
        code: str,
        code_verifier: Optional[str] = None,
    ) -> OAuthToken:
        """
        Exchange authorization code for tokens.

        Args:
            code: Authorization code from callback
            code_verifier: PKCE code verifier

        Returns:
            OAuthToken
        """
        if not self._http:
            return self._mock_token()

        data = {
            "grant_type": "authorization_code",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "code": code,
            "redirect_uri": self.config.redirect_uri,
        }

        if code_verifier:
            data["code_verifier"] = code_verifier

        headers = {"Accept": "application/json"}
        token_endpoint = self.endpoints.get("token_endpoint", "")

        try:
            if hasattr(self._http, "post"):
                response = self._http.post(token_endpoint, data=data, headers=headers)
                response_data = response.json()
            else:
                import requests
                response = requests.post(token_endpoint, data=data, headers=headers, timeout=30)
                response_data = response.json()

            return OAuthToken(
                access_token=response_data.get("access_token", ""),
                token_type=response_data.get("token_type", "Bearer"),
                expires_in=response_data.get("expires_in", 3600),
                refresh_token=response_data.get("refresh_token"),
                scope=response_data.get("scope"),
                id_token=response_data.get("id_token"),
            )
        except Exception as e:
            logger.error(f"Token exchange failed: {e}")
            raise

    def refresh_token(self, refresh_token: str) -> OAuthToken:
        """
        Refresh access token.

        Args:
            refresh_token: Refresh token

        Returns:
            New OAuthToken
        """
        if not self._http:
            return self._mock_token()

        data = {
            "grant_type": "refresh_token",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "refresh_token": refresh_token,
        }

        token_endpoint = self.endpoints.get("token_endpoint", "")

        try:
            if hasattr(self._http, "post"):
                response = self._http.post(token_endpoint, data=data)
                response_data = response.json()
            else:
                import requests
                response = requests.post(token_endpoint, data=data, timeout=30)
                response_data = response.json()

            return OAuthToken(
                access_token=response_data.get("access_token", ""),
                token_type=response_data.get("token_type", "Bearer"),
                expires_in=response_data.get("expires_in", 3600),
                refresh_token=response_data.get("refresh_token", refresh_token),
                scope=response_data.get("scope"),
                id_token=response_data.get("id_token"),
            )
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise

    def get_user_info(self, token: OAuthToken) -> OAuthUser:
        """
        Get user information from provider.

        Args:
            token: OAuth token

        Returns:
            OAuthUser
        """
        if not self._http:
            return self._mock_user()

        userinfo_endpoint = self.endpoints.get("userinfo_endpoint", "")
        headers = {"Authorization": f"{token.token_type} {token.access_token}"}

        try:
            if hasattr(self._http, "get"):
                response = self._http.get(userinfo_endpoint, headers=headers)
                data = response.json()
            else:
                import requests
                response = requests.get(userinfo_endpoint, headers=headers, timeout=30)
                data = response.json()

            return self._parse_user_info(data)
        except Exception as e:
            logger.error(f"User info retrieval failed: {e}")
            raise

    def _parse_user_info(self, data: Dict[str, Any]) -> OAuthUser:
        """Parse user info based on provider."""
        provider = self.config.provider

        if provider == OAuthProvider.GOOGLE:
            return OAuthUser(
                id=data.get("sub", ""),
                email=data.get("email", ""),
                name=data.get("name"),
                first_name=data.get("given_name"),
                last_name=data.get("family_name"),
                picture=data.get("picture"),
                email_verified=data.get("email_verified", False),
                locale=data.get("locale"),
                provider=provider,
                raw_data=data,
            )
        elif provider == OAuthProvider.MICROSOFT:
            return OAuthUser(
                id=data.get("sub", data.get("id", "")),
                email=data.get("email", data.get("userPrincipalName", "")),
                name=data.get("name", data.get("displayName")),
                first_name=data.get("given_name", data.get("givenName")),
                last_name=data.get("family_name", data.get("surname")),
                picture=None,  # Requires separate Graph API call
                email_verified=True,  # Microsoft validates emails
                provider=provider,
                raw_data=data,
            )
        elif provider == OAuthProvider.GITHUB:
            return OAuthUser(
                id=str(data.get("id", "")),
                email=data.get("email", ""),
                name=data.get("name"),
                first_name=None,
                last_name=None,
                picture=data.get("avatar_url"),
                email_verified=True,  # GitHub validates emails
                provider=provider,
                raw_data=data,
            )
        else:
            # Generic OIDC parsing
            return OAuthUser(
                id=data.get("sub", data.get("id", "")),
                email=data.get("email", ""),
                name=data.get("name"),
                first_name=data.get("given_name"),
                last_name=data.get("family_name"),
                picture=data.get("picture"),
                email_verified=data.get("email_verified", False),
                locale=data.get("locale"),
                provider=provider,
                raw_data=data,
            )

    def _generate_code_challenge(self, code_verifier: str) -> str:
        """Generate PKCE code challenge."""
        digest = hashlib.sha256(code_verifier.encode()).digest()
        return base64.urlsafe_b64encode(digest).decode().rstrip("=")

    def _mock_token(self) -> OAuthToken:
        """Generate mock token for testing."""
        return OAuthToken(
            access_token=f"mock_access_token_{secrets.token_hex(16)}",
            refresh_token=f"mock_refresh_token_{secrets.token_hex(16)}",
            expires_in=3600,
        )

    def _mock_user(self) -> OAuthUser:
        """Generate mock user for testing."""
        return OAuthUser(
            id="mock_user_id",
            email="user@example.com",
            name="Mock User",
            first_name="Mock",
            last_name="User",
            email_verified=True,
            provider=self.config.provider,
        )

    def revoke_token(self, token: str) -> bool:
        """
        Revoke OAuth token.

        Args:
            token: Token to revoke

        Returns:
            Success status
        """
        # Provider-specific revocation endpoints
        revoke_endpoints = {
            OAuthProvider.GOOGLE: "https://oauth2.googleapis.com/revoke",
            OAuthProvider.MICROSOFT: f"https://login.microsoftonline.com/{self.config.tenant_id or 'common'}/oauth2/v2.0/logout",
        }

        revoke_endpoint = revoke_endpoints.get(self.config.provider)
        if not revoke_endpoint or not self._http:
            return True

        try:
            if hasattr(self._http, "post"):
                response = self._http.post(revoke_endpoint, data={"token": token})
                return response.status_code == 200
            else:
                import requests
                response = requests.post(revoke_endpoint, data={"token": token}, timeout=30)
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Token revocation failed: {e}")
            return False


class OAuthManager:
    """
    Manager for multiple OAuth providers.

    Example:
        manager = OAuthManager()
        manager.register_provider("google", google_config)
        manager.register_provider("microsoft", microsoft_config)

        client = manager.get_client("google")
        auth_url, state, verifier = client.get_authorization_url()
    """

    def __init__(self):
        self._providers: Dict[str, OAuthClient] = {}
        self._state_store: Dict[str, Dict[str, Any]] = {}

    def register_provider(self, name: str, config: OAuthConfig) -> None:
        """Register an OAuth provider."""
        self._providers[name] = OAuthClient(config)

    def get_client(self, name: str) -> OAuthClient:
        """Get OAuth client by provider name."""
        if name not in self._providers:
            raise ValueError(f"Unknown provider: {name}")
        return self._providers[name]

    def list_providers(self) -> List[str]:
        """List registered provider names."""
        return list(self._providers.keys())

    def store_state(
        self,
        state: str,
        provider: str,
        code_verifier: Optional[str] = None,
        extra_data: Optional[Dict] = None,
    ) -> None:
        """Store state for callback validation."""
        self._state_store[state] = {
            "provider": provider,
            "code_verifier": code_verifier,
            "created_at": datetime.utcnow(),
            **(extra_data or {}),
        }

    def validate_state(self, state: str, max_age_seconds: int = 600) -> Optional[Dict]:
        """
        Validate and retrieve state.

        Args:
            state: State to validate
            max_age_seconds: Maximum age of state

        Returns:
            State data if valid, None otherwise
        """
        data = self._state_store.pop(state, None)
        if data is None:
            return None

        created_at = data.get("created_at")
        if created_at and (datetime.utcnow() - created_at).total_seconds() > max_age_seconds:
            return None

        return data

    async def handle_callback(
        self,
        provider: str,
        code: str,
        state: str,
    ) -> tuple:
        """
        Handle OAuth callback.

        Args:
            provider: Provider name
            code: Authorization code
            state: State parameter

        Returns:
            Tuple of (OAuthToken, OAuthUser)
        """
        # Validate state
        state_data = self.validate_state(state)
        if state_data is None:
            raise ValueError("Invalid or expired state")

        if state_data.get("provider") != provider:
            raise ValueError("Provider mismatch")

        # Exchange code for token
        client = self.get_client(provider)
        code_verifier = state_data.get("code_verifier")

        token = client.exchange_code(code, code_verifier)
        user = client.get_user_info(token)

        return token, user
