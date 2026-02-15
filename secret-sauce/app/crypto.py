"""AES-256-GCM encryption/decryption for Secret Sauce."""

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def generate_key() -> str:
    """Generate a new AES-256 key, returned as base64."""
    return base64.b64encode(os.urandom(32)).decode()


def _get_aesgcm(key_b64: str) -> AESGCM:
    return AESGCM(base64.b64decode(key_b64))


def encrypt(plaintext: str, key_b64: str) -> str:
    """Encrypt plaintext → base64(nonce + ciphertext).

    12-byte random nonce is prepended to the ciphertext.
    """
    nonce = os.urandom(12)
    ct = _get_aesgcm(key_b64).encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ct).decode()


def decrypt(token: str, key_b64: str) -> str:
    """Decrypt base64(nonce + ciphertext) → plaintext."""
    raw = base64.b64decode(token)
    nonce, ct = raw[:12], raw[12:]
    return _get_aesgcm(key_b64).decrypt(nonce, ct, None).decode()

