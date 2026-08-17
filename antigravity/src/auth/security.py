"""Security utilities for the ERP authentication system.

Provides password hashing, token generation, rate limiting, input
sanitization, and lightweight data encryption. Password hashing uses
bcrypt when available, falling back to PBKDF2-HMAC-SHA256 from the
standard library.

Functions:
    hash_password: Hash a plaintext password.
    verify_password: Verify a plaintext password against a hash.
    generate_session_token: Create a cryptographically secure session token.
    generate_secret_key: Create a hex-encoded secret key for configuration.
    check_password_strength: Validate password meets minimum requirements.
    sanitize_input: Strip dangerous characters for basic XSS prevention.
    is_rate_limited: In-memory sliding-window rate limiter.
    clear_rate_limit: Remove a key from the rate limit store.
    encrypt_data: Simple XOR-based data encryption.
    decrypt_data: Reverse XOR-based data decryption.
"""

import base64
import hashlib
import os
import secrets
import time
from typing import Optional

# ── Bcrypt availability check ──────────────────────────────────────
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False

# ── In-memory rate limit store ─────────────────────────────────────
_rate_limit_store: dict[str, list[float]] = {}


# ====================================================================
# Password Hashing
# ====================================================================

def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt or PBKDF2 fallback.

    When bcrypt is installed the password is hashed with a random salt
    using the default work factor. Otherwise PBKDF2-HMAC-SHA256 is used
    with 100 000 iterations and a 32-byte random salt. The fallback
    format is ``pbkdf2$<salt_hex>$<hash_hex>``.

    Args:
        password: The plaintext password to hash.

    Returns:
        str: The hashed password string.

    Raises:
        ValueError: If the password is empty.
    """
    if not password:
        raise ValueError("Password cannot be empty")

    if BCRYPT_AVAILABLE:
        return bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt(),
        ).decode('utf-8')

    # PBKDF2 fallback
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100_000,
    )
    return f"pbkdf2${salt.hex()}${key.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify a plaintext password against a stored hash.

    Automatically detects whether the hash was produced by bcrypt or the
    PBKDF2 fallback and applies the matching algorithm.

    Args:
        password: The plaintext password to verify.
        hashed: The stored password hash.

    Returns:
        bool: True if the password matches, False otherwise.
    """
    if not password or not hashed:
        return False

    try:
        if hashed.startswith('pbkdf2$'):
            parts = hashed.split('$')
            if len(parts) != 3:
                return False
            salt = bytes.fromhex(parts[1])
            stored_key = parts[2]
            key = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt,
                100_000,
            )
            return key.hex() == stored_key

        if BCRYPT_AVAILABLE:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                hashed.encode('utf-8'),
            )

        return False
    except Exception:
        # Never leak information through error messages
        return False


# ====================================================================
# Token / Key Generation
# ====================================================================

def generate_session_token() -> str:
    """Generate a cryptographically secure URL-safe session token.

    Uses 64 bytes of randomness (86+ characters after base64 encoding).

    Returns:
        str: A URL-safe base64-encoded token.
    """
    return secrets.token_urlsafe(64)


def generate_secret_key() -> str:
    """Generate a hex-encoded secret key suitable for application config.

    Uses 32 bytes of randomness producing a 64-character hex string.

    Returns:
        str: A 64-character hexadecimal secret key.
    """
    return secrets.token_hex(32)


# ====================================================================
# Password Strength
# ====================================================================

def check_password_strength(password: str) -> tuple[bool, str]:
    """Validate that a password meets the minimum strength requirements.

    Currently enforces a minimum length of 6 characters. Additional
    rules (uppercase, digit, special char) can be added here without
    changing callers.

    Args:
        password: The plaintext password to evaluate.

    Returns:
        tuple: ``(True, message)`` if acceptable,
               ``(False, reason)`` if too weak.
    """
    if not password:
        return False, "Password cannot be empty"

    if len(password) < 6:
        return False, "Password must be at least 6 characters long"

    return True, "Password meets requirements"


# ====================================================================
# Input Sanitization
# ====================================================================

def sanitize_input(text: Optional[str]) -> str:
    """Sanitize user-supplied text for basic XSS prevention.

    Replaces the five HTML-significant characters with their entity
    equivalents and strips leading/trailing whitespace.

    Args:
        text: The raw user input (may be None).

    Returns:
        str: Sanitized string, or empty string if input is None.
    """
    if text is None:
        return ''

    text = str(text).strip()
    replacements = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
    }
    for char, entity in replacements.items():
        text = text.replace(char, entity)

    return text


# ====================================================================
# Rate Limiting
# ====================================================================

def is_rate_limited(
    key: str,
    max_attempts: int = 5,
    window: int = 300,
) -> bool:
    """Check whether a key has exceeded the allowed request rate.

    Uses an in-memory sliding-window counter. Each call records the
    current timestamp and prunes entries older than *window* seconds.
    Returns True **before** allowing the current attempt if the window
    already contains *max_attempts* entries.

    Args:
        key: Identifier for the rate limit bucket (e.g. IP or username).
        max_attempts: Maximum allowed attempts within the window.
        window: Window size in seconds (default 300 = 5 minutes).

    Returns:
        bool: True if the rate limit has been reached or exceeded.
    """
    now = time.time()

    if key not in _rate_limit_store:
        _rate_limit_store[key] = []

    # Prune expired timestamps
    _rate_limit_store[key] = [
        ts for ts in _rate_limit_store[key] if now - ts < window
    ]

    if len(_rate_limit_store[key]) >= max_attempts:
        return True

    _rate_limit_store[key].append(now)
    return False


def clear_rate_limit(key: str) -> None:
    """Remove all rate-limit records for a given key.

    Args:
        key: The rate limit bucket identifier to clear.
    """
    _rate_limit_store.pop(key, None)


# ====================================================================
# Lightweight Data Encryption (XOR + Base64)
# ====================================================================

def encrypt_data(data: str, key: str) -> str:
    """Encrypt a string using XOR with a SHA-256 derived key.

    This is a lightweight, non-production-grade encryption suitable for
    obfuscating configuration values at rest. For genuine confidentiality
    use a proper library such as ``cryptography.fernet``.

    Args:
        data: The plaintext string to encrypt.
        key: A secret key string used to derive the XOR pad.

    Returns:
        str: Base64-encoded ciphertext.

    Raises:
        ValueError: If data or key is empty.
    """
    if not data or not key:
        raise ValueError("Both data and key must be non-empty")

    key_bytes = hashlib.sha256(key.encode('utf-8')).digest()
    data_bytes = data.encode('utf-8')

    encrypted = bytes(
        b ^ key_bytes[i % len(key_bytes)]
        for i, b in enumerate(data_bytes)
    )
    return base64.b64encode(encrypted).decode('utf-8')


def decrypt_data(encrypted: str, key: str) -> str:
    """Decrypt a string previously encrypted with :func:`encrypt_data`.

    Args:
        encrypted: Base64-encoded ciphertext.
        key: The same secret key used during encryption.

    Returns:
        str: The recovered plaintext string.

    Raises:
        ValueError: If inputs are empty or decryption fails.
    """
    if not encrypted or not key:
        raise ValueError("Both encrypted data and key must be non-empty")

    try:
        key_bytes = hashlib.sha256(key.encode('utf-8')).digest()
        encrypted_bytes = base64.b64decode(encrypted)

        decrypted = bytes(
            b ^ key_bytes[i % len(key_bytes)]
            for i, b in enumerate(encrypted_bytes)
        )
        return decrypted.decode('utf-8')
    except Exception as exc:
        raise ValueError(f"Decryption failed: {exc}") from exc
