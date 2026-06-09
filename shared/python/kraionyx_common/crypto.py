"""AES-256-GCM encryption/decryption compatible with Go crypto/aes + cipher.NewGCM."""

from __future__ import annotations

import base64
import structlog
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = structlog.get_logger(__name__)

_NONCE_SIZE = 12  # 96-bit nonce required by GCM
_KEY_SIZE = 32    # 256-bit key


class AES256GCM:
    """AES-256-GCM encryption/decryption compatible with Go implementation.

    Wire format: base64( nonce‖ciphertext‖tag )
    Go's ``cipher.GCM.Seal`` appends the tag to the ciphertext, so the layout
    is ``nonce (12 B) || ciphertext || tag (16 B)``.  The Python
    ``cryptography`` library produces the same layout when we concatenate
    ``nonce + ct`` where ``ct`` already contains the appended tag.
    """

    def __init__(self, key: bytes) -> None:
        """Initialise with a 32-byte AES-256 key.

        Args:
            key: Exactly 32 bytes of key material.

        Raises:
            ValueError: If the key is not 32 bytes long.
        """
        if len(key) != _KEY_SIZE:
            raise ValueError(
                f"AES-256 key must be exactly {_KEY_SIZE} bytes, got {len(key)}"
            )
        self._aesgcm = AESGCM(key)
        logger.debug("AES-256-GCM cipher initialised (key fingerprint suppressed)")

    def encrypt(self, plaintext: bytes) -> str:
        """Encrypt *plaintext* and return ``base64(nonce || ciphertext || tag)``.

        Args:
            plaintext: Arbitrary bytes to encrypt.

        Returns:
            URL-safe base64-encoded string containing the 12-byte nonce
            prepended to the authenticated ciphertext.
        """
        nonce = os.urandom(_NONCE_SIZE)
        ciphertext_with_tag: bytes = self._aesgcm.encrypt(nonce, plaintext, None)
        combined = nonce + ciphertext_with_tag
        encoded = base64.b64encode(combined).decode("ascii")
        logger.debug(
            "Encrypted %d bytes -> %d base64 chars", len(plaintext), len(encoded)
        )
        return encoded

    def decrypt(self, encoded: str) -> bytes:
        """Decrypt a value previously produced by :meth:`encrypt`.

        Args:
            encoded: base64-encoded string of ``nonce || ciphertext || tag``.

        Returns:
            Original plaintext bytes.

        Raises:
            ValueError: If the encoded blob is too short to contain a nonce.
            cryptography.exceptions.InvalidTag: If decryption or
                authentication fails.
        """
        combined = base64.b64decode(encoded)
        if len(combined) < _NONCE_SIZE:
            raise ValueError(
                f"Ciphertext too short: expected at least {_NONCE_SIZE} bytes "
                f"for the nonce, got {len(combined)}"
            )
        nonce = combined[:_NONCE_SIZE]
        ciphertext_with_tag = combined[_NONCE_SIZE:]
        plaintext: bytes = self._aesgcm.decrypt(nonce, ciphertext_with_tag, None)
        logger.debug("Decrypted %d bytes of ciphertext", len(ciphertext_with_tag))
        return plaintext

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def generate_key() -> bytes:
        """Generate a cryptographically secure random 32-byte key.

        Returns:
            32 random bytes suitable for AES-256.
        """
        return os.urandom(_KEY_SIZE)

    @staticmethod
    def key_from_base64(encoded: str) -> bytes:
        """Decode a base64-encoded key string into raw bytes.

        Args:
            encoded: Standard base64 representation of a 32-byte key.

        Returns:
            The decoded 32-byte key.

        Raises:
            ValueError: If the decoded key is not exactly 32 bytes.
        """
        key = base64.b64decode(encoded)
        if len(key) != _KEY_SIZE:
            raise ValueError(
                f"Decoded key must be {_KEY_SIZE} bytes, got {len(key)}"
            )
        return key
