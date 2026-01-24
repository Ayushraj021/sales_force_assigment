"""
Tests for MCP authentication module.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.mcp.core.auth import (
    MCPAuthenticator,
    MCPTokenClaims,
    MCP_SCOPES,
    ROLE_DEFAULT_SCOPES,
)
from app.mcp.core.exceptions import MCPError, MCPErrorCode


class TestMCPTokenClaims:
    """Tests for MCPTokenClaims."""

    def test_has_scope(self, test_user_claims: MCPTokenClaims):
        """Test scope checking."""
        assert test_user_claims.has_scope("data:read")
        assert not test_user_claims.has_scope("data:delete")

    def test_has_any_scope(self, test_user_claims: MCPTokenClaims):
        """Test any scope checking."""
        assert test_user_claims.has_any_scope(["data:read", "data:delete"])
        assert not test_user_claims.has_any_scope(["data:delete", "admin:full"])

    def test_has_all_scopes(self, test_user_claims: MCPTokenClaims):
        """Test all scopes checking."""
        assert test_user_claims.has_all_scopes(["data:read", "data:write"])
        assert not test_user_claims.has_all_scopes(["data:read", "data:delete"])

    def test_is_expired(self):
        """Test expiration checking."""
        # Not expired
        claims = MCPTokenClaims(
            sub=str(uuid4()),
            org_id=str(uuid4()),
            scopes=set(),
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
        )
        assert not claims.is_expired()

        # Expired
        expired_claims = MCPTokenClaims(
            sub=str(uuid4()),
            org_id=str(uuid4()),
            scopes=set(),
            exp=datetime.now(timezone.utc) - timedelta(hours=1),
            iat=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        assert expired_claims.is_expired()


class TestMCPAuthenticator:
    """Tests for MCPAuthenticator."""

    @pytest.fixture
    def authenticator(self) -> MCPAuthenticator:
        """Create authenticator for tests."""
        return MCPAuthenticator(secret_key="test-secret-key")

    @pytest.mark.asyncio
    async def test_validate_valid_token(
        self,
        authenticator: MCPAuthenticator,
        auth_token: str,
    ):
        """Test validating a valid token."""
        claims = await authenticator.validate_token(auth_token)

        assert claims is not None
        assert claims.sub is not None
        assert claims.org_id is not None
        assert "data:read" in claims.scopes

    @pytest.mark.asyncio
    async def test_validate_expired_token(
        self,
        authenticator: MCPAuthenticator,
    ):
        """Test validating an expired token."""
        # Create expired token
        token = authenticator.create_mcp_token(
            user_id=uuid4(),
            organization_id=uuid4(),
            roles=["analyst"],
            expires_delta=timedelta(seconds=-1),
        )

        with pytest.raises(MCPError) as exc:
            await authenticator.validate_token(token)

        assert exc.value.code == MCPErrorCode.AUTHENTICATION_REQUIRED
        assert "expired" in exc.value.message.lower()

    @pytest.mark.asyncio
    async def test_validate_invalid_token(
        self,
        authenticator: MCPAuthenticator,
    ):
        """Test validating an invalid token."""
        with pytest.raises(MCPError) as exc:
            await authenticator.validate_token("invalid.token.here")

        assert exc.value.code == MCPErrorCode.AUTHENTICATION_REQUIRED

    @pytest.mark.asyncio
    async def test_check_scope_from_token(
        self,
        authenticator: MCPAuthenticator,
        test_user_claims: MCPTokenClaims,
    ):
        """Test scope checking."""
        assert await authenticator.check_scope(test_user_claims, "data:read")
        assert not await authenticator.check_scope(test_user_claims, "admin:full")

    @pytest.mark.asyncio
    async def test_require_scope_success(
        self,
        authenticator: MCPAuthenticator,
        test_user_claims: MCPTokenClaims,
    ):
        """Test require scope with valid scope."""
        # Should not raise
        await authenticator.require_scope(test_user_claims, "data:read")

    @pytest.mark.asyncio
    async def test_require_scope_failure(
        self,
        authenticator: MCPAuthenticator,
        test_user_claims: MCPTokenClaims,
    ):
        """Test require scope with missing scope."""
        with pytest.raises(MCPError) as exc:
            await authenticator.require_scope(test_user_claims, "admin:full")

        assert exc.value.code == MCPErrorCode.INSUFFICIENT_SCOPE

    def test_create_mcp_token(
        self,
        authenticator: MCPAuthenticator,
    ):
        """Test token creation."""
        token = authenticator.create_mcp_token(
            user_id=uuid4(),
            organization_id=uuid4(),
            roles=["analyst"],
            tier="professional",
        )

        assert token is not None
        assert len(token.split(".")) == 3  # JWT format

    def test_www_authenticate_header(
        self,
        authenticator: MCPAuthenticator,
    ):
        """Test WWW-Authenticate header generation."""
        header = authenticator.get_www_authenticate_header()
        assert 'Bearer realm="mcp"' in header

        header_with_error = authenticator.get_www_authenticate_header(
            error="invalid_token",
            error_description="Token expired",
        )
        assert "invalid_token" in header_with_error


class TestRoleDefaultScopes:
    """Tests for role to scope mapping."""

    def test_viewer_scopes(self):
        """Test viewer role has read-only scopes."""
        scopes = ROLE_DEFAULT_SCOPES["viewer"]
        assert "data:read" in scopes
        assert "data:write" not in scopes
        assert "models:train" not in scopes

    def test_analyst_scopes(self):
        """Test analyst role has appropriate scopes."""
        scopes = ROLE_DEFAULT_SCOPES["analyst"]
        assert "data:read" in scopes
        assert "models:train" in scopes
        assert "forecast:create" in scopes
        assert "data:delete" not in scopes

    def test_admin_scopes(self):
        """Test admin role has full scopes."""
        scopes = ROLE_DEFAULT_SCOPES["admin"]
        assert "data:read" in scopes
        assert "data:write" in scopes
        assert "data:delete" in scopes
        assert "models:deploy" in scopes


class TestMCPScopes:
    """Tests for MCP scope to RBAC mapping."""

    def test_data_read_scope_mapping(self):
        """Test data:read maps to correct RBAC permissions."""
        permissions = MCP_SCOPES["data:read"]
        assert len(permissions) > 0

    def test_models_train_scope_mapping(self):
        """Test models:train maps to correct RBAC permissions."""
        permissions = MCP_SCOPES["models:train"]
        assert len(permissions) > 0
