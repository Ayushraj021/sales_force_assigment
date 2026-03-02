"""Password hashing and verification."""

import asyncio
import base64
import hashlib
from concurrent.futures import ThreadPoolExecutor

import bcrypt

# Thread pool for CPU-bound bcrypt operations
_executor = ThreadPoolExecutor(max_workers=4)


def _prehash_password(password: str) -> bytes:
    """Pre-hash password with SHA256 to handle bcrypt's 72-byte limit.

    Bcrypt truncates passwords longer than 72 bytes. By pre-hashing with SHA256,
    we ensure consistent behavior for passwords of any length while maintaining
    security. The base64 encoding ensures the result is ASCII-safe for bcrypt.
    """
    sha256_hash = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(sha256_hash)


def _verify_password_sync(plain_password: str, hashed_password: str) -> bool:
    """Synchronous password verification."""
    prehashed = _prehash_password(plain_password)
    hashed_bytes = hashed_password.encode("utf-8")
    # Try new pre-hashed format first
    if bcrypt.checkpw(prehashed, hashed_bytes):
        return True
    # Fall back to legacy direct format for existing passwords
    # Truncate to 72 bytes to avoid bcrypt error on legacy verification
    legacy_password = plain_password.encode("utf-8")[:72]
    try:
        return bcrypt.checkpw(legacy_password, hashed_bytes)
    except Exception:
        return False


def _get_password_hash_sync(password: str) -> str:
    """Synchronous password hashing."""
    prehashed = _prehash_password(password)
    hashed = bcrypt.hashpw(prehashed, bcrypt.gensalt())
    return hashed.decode("utf-8")


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash (async).

    Supports both pre-hashed (new) and direct (legacy) password formats
    for backwards compatibility during migration.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _executor, _verify_password_sync, plain_password, hashed_password
    )


async def get_password_hash(password: str) -> str:
    """Generate a password hash (async)."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _get_password_hash_sync, password)


# Sync versions for non-async contexts (e.g., CLI scripts)
verify_password_sync = _verify_password_sync
get_password_hash_sync = _get_password_hash_sync
