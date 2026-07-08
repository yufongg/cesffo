"""
PII encryption helpers.

One master key (from .env) is run through HKDF to derive separate purpose-bound
keys: a data key for AES-256-GCM encryption and an index key for blind indexing.
A fresh random nonce per encryption means the same plaintext never produces the
same ciphertext twice. GCM gives us Confidentiality and Authenticity (the C and
A of CIA) — tampered ciphertext fails to decrypt.
"""

import base64
import hashlib
import hmac
import os
import secrets

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

_APP_ENV = os.getenv("APP_ENV", "development")

# Ciphertext token layout:  version(1) || nonce(12) || aes-gcm(ct+tag), base64url.
# The version byte lets us change algorithm/key in future without ambiguity.
_VERSION = b"\x01"
_NONCE_BYTES = 12  # AES-GCM standard / recommended nonce size

# HKDF "info" labels give each derived key a distinct purpose. Bump the version
# suffix here (and add migration handling) if you ever rotate the scheme.
_INFO_DATA = b"cesffo/pii/aes-256-gcm/v1"
_INFO_INDEX = b"cesffo/pii/blind-index/v1"

# Dev-only fallback so encrypted values survive a reload locally. The production
# guard below makes this impossible to reach with APP_ENV=production.
_DEV_FALLBACK_KEY = "dev-only-insecure-master-key-change-me"


def _load_master_key() -> bytes:
    """Load the master secret from MASTER_KEY (base64 or raw text).

    Fails closed in production: the app refuses to start without a real key,
    mirroring the JWT_SECRET_KEY handling in user/auth.py.
    """
    raw = os.getenv("MASTER_KEY")
    if not raw:
        if _APP_ENV == "production":
            raise RuntimeError("MASTER_KEY must be set in production")
        raw = _DEV_FALLBACK_KEY

    # Prefer a base64-encoded key (the documented way to ship >=32 random bytes);
    # fall back to treating the value as raw UTF-8 key material.
    try:
        key = base64.b64decode(raw, validate=True)
    except (ValueError, base64.binascii.Error):
        key = raw.encode("utf-8")

    if len(key) < 32 and _APP_ENV == "production":
        raise RuntimeError("MASTER_KEY must provide at least 32 bytes of entropy")
    return key


def _derive(master: bytes, info: bytes, length: int = 32) -> bytes:
    # HKDF is the correct KDF here: the input is already high-entropy key
    # material (a master key), not a low-entropy password (which would call for
    # Argon2/scrypt). salt=None is acceptable for a single random master secret.
    return HKDF(
        algorithm=hashes.SHA256(),
        length=length,
        salt=None,
        info=info,
    ).derive(master)


_MASTER = _load_master_key()
_DATA_KEY = _derive(_MASTER, _INFO_DATA)
_INDEX_KEY = _derive(_MASTER, _INFO_INDEX)


def encrypt(plaintext):
    """AES-256-GCM encrypt a string. Returns a base64url token, or None for None."""
    if plaintext is None:
        return None
    if not isinstance(plaintext, str):
        raise TypeError("encrypt expects str or None")

    #! Fresh random nonce every call — reusing a nonce with the same key breaks GCM entirely.
    nonce = secrets.token_bytes(_NONCE_BYTES)
    ciphertext = AESGCM(_DATA_KEY).encrypt(nonce, plaintext.encode("utf-8"), None)
    token = _VERSION + nonce + ciphertext
    return base64.urlsafe_b64encode(token).decode("ascii")


def decrypt(token):
    """Reverse encrypt(). Raises if the token is malformed or tampered with."""
    if token is None:
        return None

    raw = base64.urlsafe_b64decode(token.encode("ascii"))
    version, body = raw[:1], raw[1:]
    if version != _VERSION:
        raise ValueError("Unsupported ciphertext version")

    nonce, ciphertext = body[:_NONCE_BYTES], body[_NONCE_BYTES:]
    # GCM verifies the auth tag here; tampering raises InvalidTag.
    plaintext = AESGCM(_DATA_KEY).decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")


def blind_index(value):
    """Deterministic keyed HMAC-SHA256 of a value, for equality lookups.

    Callers must pass the *normalized* value (e.g. email lowercased/trimmed) so
    that lookups and inserts agree. Returns a 64-char hex digest, or None.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("blind_index expects str or None")
    return hmac.new(_INDEX_KEY, value.encode("utf-8"), hashlib.sha256).hexdigest()
