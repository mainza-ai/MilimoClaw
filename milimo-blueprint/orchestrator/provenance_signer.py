#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Provenance Signer

Signs blueprints with Ed25519 cryptographic signatures to create
verifiable attestations of blueprint authenticity and history.

Usage:
    from provenance_signer import ProvenanceSigner
    
    signer = ProvenanceSigner(squad_id="my-squad")
    attestation = signer.sign_blueprint(blueprint_snapshot)
    signer.verify_attestation(attestation)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
    from cryptography.exceptions import InvalidSignature
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    Ed25519PrivateKey = None
    Ed25519PublicKey = None

logger = logging.getLogger("milimo.provenance_signer")

KEYSTORE_DIR = Path.home() / ".milimo" / "keys"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class AuthorInfo:
    """Author information for attestation."""
    squad_id: str
    public_key: str
    key_id: str


@dataclass
class EvolutionSummary:
    """Summary of changes from parent attestation."""
    tools_added: list[str] = field(default_factory=list)
    tools_removed: list[str] = field(default_factory=list)
    tools_modified: list[str] = field(default_factory=list)
    performance_delta: float = 0.0
    policy_changes: list[str] = field(default_factory=list)


@dataclass
class Attestation:
    """
    Cryptographic attestation of a blueprint.
    
    Contains the signature and metadata needed to verify
    blueprint authenticity and provenance.
    """
    version: str = "1.0"
    blueprint_id: str = ""
    blueprint_version: str = ""
    content_hash: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    author: Optional[AuthorInfo] = None
    parent_attestation: Optional[str] = None
    evolution_summary: Optional[EvolutionSummary] = None
    signature: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        d = {
            "version": self.version,
            "blueprint_id": self.blueprint_id,
            "blueprint_version": self.blueprint_version,
            "content_hash": self.content_hash,
            "timestamp": self.timestamp,
            "author": asdict(self.author) if self.author else None,
            "parent_attestation": self.parent_attestation,
            "evolution_summary": asdict(self.evolution_summary) if self.evolution_summary else None,
            "signature": self.signature,
        }
        return d
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Attestation":
        """Create attestation from dictionary."""
        author_data = data.get("author")
        author = AuthorInfo(**author_data) if author_data else None
        
        evolution_data = data.get("evolution_summary")
        evolution = EvolutionSummary(**evolution_data) if evolution_data else None
        
        return cls(
            version=data.get("version", "1.0"),
            blueprint_id=data.get("blueprint_id", ""),
            blueprint_version=data.get("blueprint_version", ""),
            content_hash=data.get("content_hash", ""),
            timestamp=data.get("timestamp", ""),
            author=author,
            parent_attestation=data.get("parent_attestation"),
            evolution_summary=evolution,
            signature=data.get("signature", ""),
        )
    
    def to_signable_bytes(self) -> bytes:
        """
        Get bytes to be signed.
        
        Excludes the signature field itself.
        """
        data = self.to_dict()
        del data["signature"]
        return json.dumps(data, sort_keys=True).encode("utf-8")
    
    def hash(self) -> str:
        """Get SHA-256 hash of this attestation."""
        data = self.to_dict()
        content = json.dumps(data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Content Hash Calculation
# ---------------------------------------------------------------------------

def calculate_content_hash(
    tools: dict[str, Any],
    policies: dict[str, Any],
    evolution_config: dict[str, Any],
    performance_baseline: dict[str, Any],
) -> str:
    """
    Calculate SHA-256 hash of blueprint content.
    
    Hashed components:
    - Tool configurations (sorted by name)
    - Policy settings (sorted by key)
    - Evolution parameters
    - Performance baseline
    
    Args:
        tools: Tool configurations dictionary
        policies: Policy settings dictionary
        evolution_config: Evolution configuration
        performance_baseline: Performance baseline metrics
    
    Returns:
        Hex-encoded SHA-256 hash
    """
    components = []
    
    # Tools (sorted for deterministic hash)
    for tool_name in sorted(tools.keys()):
        tool = tools[tool_name]
        tool_hash = hashlib.sha256(
            json.dumps(tool, sort_keys=True).encode()
        ).hexdigest()
        components.append(f"tool:{tool_name}:{tool_hash}")
    
    # Policies (sorted by key)
    for key in sorted(policies.keys()):
        value = policies[key]
        if isinstance(value, dict):
            value_hash = hashlib.sha256(
                json.dumps(value, sort_keys=True).encode()
            ).hexdigest()
            components.append(f"policy:{key}:{value_hash}")
        else:
            components.append(f"policy:{key}:{value}")
    
    # Evolution config
    evolution_hash = hashlib.sha256(
        json.dumps(evolution_config, sort_keys=True).encode()
    ).hexdigest()
    components.append(f"evolution:{evolution_hash}")
    
    # Performance baseline
    baseline_hash = hashlib.sha256(
        json.dumps(performance_baseline, sort_keys=True).encode()
    ).hexdigest()
    components.append(f"baseline:{baseline_hash}")
    
    content = "\n".join(components)
    return hashlib.sha256(content.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Key Management
# ---------------------------------------------------------------------------

def generate_key_pair() -> tuple[bytes, bytes]:
    """
    Generate a new Ed25519 key pair.
    
    Returns:
        Tuple of (private_key_bytes, public_key_bytes)
    """
    if not CRYPTO_AVAILABLE:
        # Fallback: generate random bytes for testing
        private_key_bytes = secrets.token_bytes(32)
        public_key_bytes = secrets.token_bytes(32)
        return private_key_bytes, public_key_bytes
    
    private_key = Ed25519PrivateKey.generate()
    private_key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )
    public_key_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    
    return private_key_bytes, public_key_bytes


def save_key_pair(
    squad_id: str,
    private_key_bytes: bytes,
    public_key_bytes: bytes,
) -> Path:
    """
    Save key pair to keystore.
    
    Args:
        squad_id: Squad identifier
        private_key_bytes: Private key bytes
        public_key_bytes: Public key bytes
    
    Returns:
        Path to saved key file
    """
    KEYSTORE_DIR.mkdir(parents=True, exist_ok=True)
    
    key_file = KEYSTORE_DIR / f"{squad_id}.json"
    
    key_data = {
        "squad_id": squad_id,
        "private_key": private_key_bytes.hex(),
        "public_key": public_key_bytes.hex(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "algorithm": "ed25519",
    }
    
    key_file.write_text(json.dumps(key_data, indent=2))
    
    # Restrict permissions on private key file
    os.chmod(key_file, 0o600)
    
    logger.info(f"Saved key pair for squad {squad_id} to {key_file}")
    
    return key_file


def load_key_pair(squad_id: str) -> Optional[tuple[bytes, bytes]]:
    """
    Load key pair from keystore.
    
    Args:
        squad_id: Squad identifier
    
    Returns:
        Tuple of (private_key_bytes, public_key_bytes) or None
    """
    key_file = KEYSTORE_DIR / f"{squad_id}.json"
    
    if not key_file.exists():
        return None
    
    key_data = json.loads(key_file.read_text())
    
    private_key_bytes = bytes.fromhex(key_data["private_key"])
    public_key_bytes = bytes.fromhex(key_data["public_key"])
    
    return private_key_bytes, public_key_bytes


# ---------------------------------------------------------------------------
# Provenance Signer
# ---------------------------------------------------------------------------

class ProvenanceSigner:
    """
    Signs blueprints with Ed25519 signatures.
    
    Creates and verifies attestations for blueprint versions,
    establishing a cryptographic provenance chain.
    """
    
    def __init__(
        self,
        squad_id: str,
        keystore_dir: Optional[Path] = None,
    ):
        """
        Initialize the provenance signer.
        
        Args:
            squad_id: Squad identifier
            keystore_dir: Optional custom keystore directory
        """
        self.squad_id = squad_id
        self.keystore_dir = keystore_dir or KEYSTORE_DIR
        
        self._private_key_bytes: Optional[bytes] = None
        self._public_key_bytes: Optional[bytes] = None
        self._private_key: Optional[Any] = None
        self._public_key: Optional[Any] = None
        
        self._load_or_generate_keys()
    
    def _load_or_generate_keys(self) -> None:
        """Load existing keys or generate new ones."""
        key_file = self.keystore_dir / f"{self.squad_id}.json"
        
        if key_file.exists():
            result = load_key_pair(self.squad_id)
            if result:
                self._private_key_bytes, self._public_key_bytes = result
                self._init_crypto_keys()
                return
        
        # Generate new keys
        self._private_key_bytes, self._public_key_bytes = generate_key_pair()
        save_key_pair(self.squad_id, self._private_key_bytes, self._public_key_bytes)
        self._init_crypto_keys()
    
    def _init_crypto_keys(self) -> None:
        """Initialize cryptography key objects."""
        if CRYPTO_AVAILABLE and self._private_key_bytes:
            self._private_key = Ed25519PrivateKey.from_private_bytes(
                self._private_key_bytes
            )
            self._public_key = self._private_key.public_key()
    
    @property
    def public_key_hex(self) -> str:
        """Get public key as hex string."""
        if self._public_key_bytes:
            return self._public_key_bytes.hex()
        return ""
    
    @property
    def key_id(self) -> str:
        """Get key identifier (first 8 bytes of public key)."""
        if self._public_key_bytes:
            return self._public_key_bytes[:8].hex()
        return ""
    
    def sign_blueprint(
        self,
        blueprint: Any,
        parent_attestation: Optional[Attestation] = None,
        evolution_summary: Optional[EvolutionSummary] = None,
    ) -> Attestation:
        """
        Create a signed attestation for a blueprint.
        
        Args:
            blueprint: BlueprintSnapshot to sign
            parent_attestation: Optional parent attestation for chain
            evolution_summary: Optional summary of changes
        
        Returns:
            Signed attestation
        """
        # Extract content from blueprint
        tools = getattr(blueprint, "tools_inventory", {})
        policies = getattr(blueprint, "policy", {})
        claw_config = getattr(blueprint, "claw_config", {})
        learned_priors = getattr(blueprint, "learned_priors", {})
        
        # Get evolution config
        evolution_config = claw_config.get("evolution", {})
        
        # Get performance baseline
        performance_baseline = learned_priors.get("performance", {})
        
        # Calculate content hash
        content_hash = calculate_content_hash(
            tools=tools,
            policies=policies,
            evolution_config=evolution_config,
            performance_baseline=performance_baseline,
        )
        
        # Build attestation
        attestation = Attestation(
            version="1.0",
            blueprint_id=getattr(blueprint.meta, "squad_id", self.squad_id),
            blueprint_version=getattr(blueprint.meta, "version", "0.1.0"),
            content_hash=f"sha256:{content_hash}",
            author=AuthorInfo(
                squad_id=self.squad_id,
                public_key=f"ed25519:{self.public_key_hex}",
                key_id=self.key_id,
            ),
            parent_attestation=parent_attestation.hash() if parent_attestation else None,
            evolution_summary=evolution_summary,
        )
        
        # Sign attestation
        attestation_bytes = attestation.to_signable_bytes()
        signature = self._sign_bytes(attestation_bytes)
        attestation.signature = f"ed25519:{signature}"
        
        return attestation
    
    def _sign_bytes(self, data: bytes) -> str:
        """Sign bytes with private key."""
        if CRYPTO_AVAILABLE and self._private_key:
            signature = self._private_key.sign(data)
            return signature.hex()
        
        # Fallback: use HMAC-SHA256 for testing
        import hmac
        signature = hmac.new(self._private_key_bytes, data, hashlib.sha256).digest()
        return signature.hex()
    
    def verify_attestation(self, attestation: Attestation) -> bool:
        """
        Verify an attestation signature.
        
        Args:
            attestation: Attestation to verify
        
        Returns:
            True if signature is valid
        """
        if not attestation.author or not attestation.signature:
            return False
        
        # Get public key from attestation
        public_key_hex = attestation.author.public_key.replace("ed25519:", "")
        signature_hex = attestation.signature.replace("ed25519:", "")
        
        attestation_bytes = attestation.to_signable_bytes()
        
        if CRYPTO_AVAILABLE:
            try:
                public_key = Ed25519PublicKey.from_public_bytes(
                    bytes.fromhex(public_key_hex)
                )
                public_key.verify(
                    bytes.fromhex(signature_hex),
                    attestation_bytes
                )
                return True
            except InvalidSignature:
                return False
            except Exception as e:
                logger.error(f"Verification error: {e}")
                return False
        
        # Fallback: HMAC verification
        import hmac
        expected_sig = hmac.new(
            bytes.fromhex(public_key_hex),
            attestation_bytes,
            hashlib.sha256
        ).digest()
        return hmac.compare_digest(expected_sig, bytes.fromhex(signature_hex))
    
    def export_public_key(self) -> dict[str, str]:
        """
        Export public key information.
        
        Returns:
            Dictionary with public key details
        """
        return {
            "squad_id": self.squad_id,
            "public_key": f"ed25519:{self.public_key_hex}",
            "key_id": self.key_id,
            "algorithm": "ed25519",
        }
