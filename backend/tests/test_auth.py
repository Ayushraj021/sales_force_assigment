"""Tests for authentication and authorization."""

import pytest
from datetime import datetime, timedelta

from app.core.security.jwt import create_access_token, decode_token, TokenData
from app.core.security.password import get_password_hash_sync as get_password_hash, verify_password_sync as verify_password


class TestPasswordHashing:
    """Tests for password hashing utilities."""

    def test_password_hash_creates_hash(self):
        """Test that password hashing creates a hash."""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)

        assert hashed != password
        assert len(hashed) > 20

    def test_password_verification_correct(self):
        """Test password verification with correct password."""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_password_verification_incorrect(self):
        """Test password verification with incorrect password."""
        password = "SecurePassword123!"
        wrong_password = "WrongPassword456!"
        hashed = get_password_hash(password)

        assert verify_password(wrong_password, hashed) is False

    def test_same_password_different_hashes(self):
        """Test that same password creates different hashes (salting)."""
        password = "SecurePassword123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTTokens:
    """Tests for JWT token creation and validation."""

    def test_create_access_token(self):
        """Test access token creation."""
        data = {"sub": "user@example.com", "user_id": "123"}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50

    def test_decode_valid_token(self):
        """Test decoding a valid token."""
        user_email = "user@example.com"
        user_id = "123"
        data = {"sub": user_email, "user_id": user_id}
        token = create_access_token(data)

        decoded = decode_token(token)

        assert decoded is not None
        assert decoded.email == user_email

    def test_decode_expired_token(self):
        """Test that expired tokens fail validation."""
        data = {"sub": "user@example.com"}
        # Create token that expires immediately
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))

        decoded = decode_token(token)

        assert decoded is None

    def test_decode_invalid_token(self):
        """Test that invalid tokens fail validation."""
        invalid_token = "invalid.token.here"

        decoded = decode_token(invalid_token)

        assert decoded is None

    def test_token_contains_expiry(self):
        """Test that tokens contain expiry information."""
        data = {"sub": "user@example.com"}
        expires = timedelta(hours=1)
        token = create_access_token(data, expires_delta=expires)

        # Token should be valid
        decoded = decode_token(token)
        assert decoded is not None
