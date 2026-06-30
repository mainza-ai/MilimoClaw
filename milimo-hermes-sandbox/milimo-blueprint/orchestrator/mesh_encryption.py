# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Message Encryption

AES-256-GCM encryption for inter-claw messages.
Key derivation uses PBKDF2 with claw-pair salt.
Must be interoperable with TypeScript implementation.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend

    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False


ALGORITHM = "aes-256-gcm"
KEY_LENGTH = 32
IV_LENGTH = 16
AUTH_TAG_LENGTH = 16
PBKDF2_ITERATIONS = 100000
SALT_SEPARATOR = ":"


@dataclass
class EncryptedMessage:
    """Encrypted message container."""

    iv: str
    ciphertext: str
    auth_tag: str
    timestamp: str


class MessageEncryption:
    """
    AES-256-GCM message encryption.

    Key derivation uses PBKDF2 with claw-pair salt.
    Each message gets a unique IV.
    """

    def __init__(self, mesh_secret: str) -> None:
        """
        Initialize encryption with mesh secret.

        Args:
            mesh_secret: Secret key for the mesh
        """
        self.mesh_secret = mesh_secret

        if not HAS_CRYPTOGRAPHY:
            raise RuntimeError(
                "cryptography library not installed. Run: pip install cryptography"
            )

    def encrypt(
        self, plaintext: str, sender_role: str, recipient_role: str
    ) -> EncryptedMessage:
        """
        Encrypt a message.

        Args:
            plaintext: Text to encrypt
            sender_role: Sender claw role
            recipient_role: Recipient claw role

        Returns:
            EncryptedMessage with iv, ciphertext, auth_tag
        """
        key = self._derive_key(sender_role, recipient_role)
        iv = os.urandom(IV_LENGTH)

        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(iv, plaintext.encode("utf-8"), None)

        return EncryptedMessage(
            iv=base64.b64encode(iv).decode("ascii"),
            ciphertext=base64.b64encode(ciphertext[:-AUTH_TAG_LENGTH]).decode("ascii"),
            auth_tag=base64.b64encode(ciphertext[-AUTH_TAG_LENGTH:]).decode("ascii"),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def decrypt(
        self, encrypted: EncryptedMessage, sender_role: str, recipient_role: str
    ) -> str:
        """
        Decrypt a message.

        Args:
            encrypted: Encrypted message
            sender_role: Sender claw role
            recipient_role: Recipient claw role

        Returns:
            Decrypted plaintext
        """
        key = self._derive_key(sender_role, recipient_role)
        iv = base64.b64decode(encrypted.iv)
        ciphertext = base64.b64decode(encrypted.ciphertext)
        auth_tag = base64.b64decode(encrypted.auth_tag)

        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(iv, ciphertext + auth_tag, None)

        return plaintext.decode("utf-8")

    def encrypt_message(
        self, message: dict[str, Any], sender_role: str, recipient_role: str
    ) -> dict[str, Any]:
        """
        Encrypt a JSON message.

        Args:
            message: Message dict to encrypt
            sender_role: Sender claw role
            recipient_role: Recipient claw role

        Returns:
            Encrypted message dict
        """
        plaintext = json.dumps(message)
        encrypted = self.encrypt(plaintext, sender_role, recipient_role)

        return {
            "encrypted": True,
            "sender_role": sender_role,
            "recipient_role": recipient_role,
            "iv": encrypted.iv,
            "ciphertext": encrypted.ciphertext,
            "auth_tag": encrypted.auth_tag,
            "timestamp": encrypted.timestamp,
        }

    def decrypt_message(self, encrypted_message: dict[str, Any]) -> dict[str, Any]:
        """
        Decrypt a JSON message.

        Args:
            encrypted_message: Encrypted message dict

        Returns:
            Decrypted message dict
        """
        if not encrypted_message.get("encrypted"):
            return encrypted_message

        encrypted = EncryptedMessage(
            iv=encrypted_message["iv"],
            ciphertext=encrypted_message["ciphertext"],
            auth_tag=encrypted_message["auth_tag"],
            timestamp=encrypted_message.get("timestamp", ""),
        )

        sender_role = encrypted_message["sender_role"]
        recipient_role = encrypted_message["recipient_role"]

        plaintext = self.decrypt(encrypted, sender_role, recipient_role)
        return json.loads(plaintext)

    def _derive_key(self, sender_role: str, recipient_role: str) -> bytes:
        """
        Derive encryption key from roles and mesh secret.

        Args:
            sender_role: Sender claw role
            recipient_role: Recipient claw role

        Returns:
            32-byte encryption key
        """
        salt = f"{sender_role}{SALT_SEPARATOR}{recipient_role}".encode("utf-8")

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_LENGTH,
            salt=salt,
            iterations=PBKDF2_ITERATIONS,
            backend=default_backend(),
        )

        return kdf.derive(self.mesh_secret.encode("utf-8"))

    @staticmethod
    def hash_for_testing(data: str) -> str:
        """Generate SHA-256 hash for testing."""
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_test_key() -> bytes:
        """Generate random 32-byte key for testing."""
        return os.urandom(KEY_LENGTH)


def create_test_encryption() -> MessageEncryption:
    """Create encryption instance for testing."""
    return MessageEncryption("test-mesh-secret-for-testing-purposes-only")
