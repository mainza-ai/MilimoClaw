#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Provenance Verifier

Verifies blueprint attestations and validates signatures
to ensure blueprint authenticity and integrity.

Usage:
    from provenance_verifier import ProvenanceVerifier
    
    verifier = ProvenanceVerifier()
    result = verifier.verify(attestation)
    if result.valid:
        print("Blueprint is authentic")
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    Ed25519PublicKey = None

from .provenance_signer import Attestation, calculate_content_hash

logger = logging.getLogger("milimo.provenance_verifier")


# ---------------------------------------------------------------------------
# Verification Result
# ---------------------------------------------------------------------------

@dataclass
class VerificationResult:
    """Result of attestation verification."""
    valid: bool
    attestation_id: str = ""
    blueprint_id: str = ""
    blueprint_version: str = ""
    author_squad_id: str = ""
    content_hash_valid: bool = True
    signature_valid: bool = True
    timestamp_valid: bool = True
    parent_referenced: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "attestation_id": self.attestation_id,
            "blueprint_id": self.blueprint_id,
            "blueprint_version": self.blueprint_version,
            "author_squad_id": self.author_squad_id,
            "content_hash_valid": self.content_hash_valid,
            "signature_valid": self.signature_valid,
            "timestamp_valid": self.timestamp_valid,
            "parent_referenced": self.parent_referenced,
            "errors": self.errors,
            "warnings": self.warnings,
        }


@dataclass
class ContentIntegrityResult:
    """Result of content integrity check."""
    valid: bool
    expected_hash: str = ""
    computed_hash: str = ""
    mismatched_components: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Provenance Verifier
# ---------------------------------------------------------------------------

class ProvenanceVerifier:
    """
    Verifies blueprint attestations.
    
    Validates signatures, content hashes, and attestation structure
    to ensure blueprint authenticity.
    """
    
    # Maximum age for attestations (default: 2 years)
    MAX_ATTESTATION_AGE_DAYS = 730
    
    # Minimum attestation age check (prevent future timestamps)
    MAX_FUTURE_SECONDS = 300  # 5 minutes tolerance for clock skew
    
    def __init__(
        self,
        max_age_days: Optional[int] = None,
        strict_mode: bool = False,
    ):
        """
        Initialize the provenance verifier.
        
        Args:
            max_age_days: Maximum attestation age in days
            strict_mode: Enable strict verification (fail on warnings)
        """
        self.max_age_days = max_age_days or self.MAX_ATTESTATION_AGE_DAYS
        self.strict_mode = strict_mode
    
    def verify(self, attestation: Attestation) -> VerificationResult:
        """
        Verify an attestation.
        
        Args:
            attestation: Attestation to verify
        
        Returns:
            VerificationResult with validity status
        """
        result = VerificationResult(
            valid=True,
            attestation_id=attestation.hash(),
            blueprint_id=attestation.blueprint_id,
            blueprint_version=attestation.blueprint_version,
            author_squad_id=attestation.author.squad_id if attestation.author else "",
        )
        
        # Check required fields
        self._check_required_fields(attestation, result)
        if not result.valid:
            return result
        
        # Verify signature
        self._verify_signature(attestation, result)
        
        # Verify timestamp
        self._verify_timestamp(attestation, result)
        
        # Check parent reference
        self._check_parent_reference(attestation, result)
        
        # Finalize result
        if self.strict_mode and result.warnings:
            result.valid = False
            result.errors.append("Strict mode: warnings treated as errors")
        
        return result
    
    def verify_content(
        self,
        attestation: Attestation,
        blueprint: Any,
    ) -> ContentIntegrityResult:
        """
        Verify content hash matches attestation.
        
        Args:
            attestation: Attestation to verify against
            blueprint: Blueprint to verify
        
        Returns:
            ContentIntegrityResult with hash comparison
        """
        # Extract content from blueprint
        tools = getattr(blueprint, "tools_inventory", {})
        policies = getattr(blueprint, "policy", {})
        claw_config = getattr(blueprint, "claw_config", {})
        learned_priors = getattr(blueprint, "learned_priors", {})
        
        evolution_config = claw_config.get("evolution", {})
        performance_baseline = learned_priors.get("performance", {})
        
        # Calculate content hash
        computed_hash = calculate_content_hash(
            tools=tools,
            policies=policies,
            evolution_config=evolution_config,
            performance_baseline=performance_baseline,
        )
        
        # Extract expected hash from attestation
        expected_hash = attestation.content_hash.replace("sha256:", "")
        
        valid = computed_hash == expected_hash
        
        result = ContentIntegrityResult(
            valid=valid,
            expected_hash=expected_hash,
            computed_hash=computed_hash,
        )
        
        if not valid:
            result.mismatched_components = self._find_mismatched_components(
                attestation, blueprint
            )
        
        return result
    
    def _check_required_fields(
        self,
        attestation: Attestation,
        result: VerificationResult,
    ) -> None:
        """Check that required fields are present."""
        if not attestation.version:
            result.valid = False
            result.errors.append("Missing attestation version")
        
        if not attestation.blueprint_id:
            result.valid = False
            result.errors.append("Missing blueprint_id")
        
        if not attestation.blueprint_version:
            result.valid = False
            result.errors.append("Missing blueprint_version")
        
        if not attestation.content_hash:
            result.valid = False
            result.errors.append("Missing content_hash")
        
        if not attestation.timestamp:
            result.valid = False
            result.errors.append("Missing timestamp")
        
        if not attestation.author:
            result.valid = False
            result.errors.append("Missing author information")
        else:
            if not attestation.author.squad_id:
                result.valid = False
                result.errors.append("Missing author squad_id")
            
            if not attestation.author.public_key:
                result.valid = False
                result.errors.append("Missing author public_key")
        
        if not attestation.signature:
            result.valid = False
            result.errors.append("Missing signature")
    
    def _verify_signature(
        self,
        attestation: Attestation,
        result: VerificationResult,
    ) -> None:
        """Verify the attestation signature."""
        if not attestation.author or not attestation.signature:
            result.signature_valid = False
            result.valid = False
            return
        
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
                result.signature_valid = True
            except InvalidSignature:
                result.signature_valid = False
                result.valid = False
                result.errors.append("Invalid signature")
            except Exception as e:
                result.signature_valid = False
                result.valid = False
                result.errors.append(f"Signature verification error: {e}")
        else:
            # Fallback: HMAC verification (for testing)
            import hmac
            expected_sig = hmac.new(
                bytes.fromhex(public_key_hex),
                attestation_bytes,
                hashlib.sha256
            ).digest()
            
            if hmac.compare_digest(expected_sig, bytes.fromhex(signature_hex)):
                result.signature_valid = True
            else:
                result.signature_valid = False
                result.valid = False
                result.errors.append("Invalid signature (HMAC)")
    
    def _verify_timestamp(
        self,
        attestation: Attestation,
        result: VerificationResult,
    ) -> None:
        """Verify the attestation timestamp."""
        try:
            timestamp = datetime.fromisoformat(attestation.timestamp.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            
            # Check for future timestamp
            future_limit = now + timedelta(seconds=self.MAX_FUTURE_SECONDS)
            if timestamp > future_limit:
                result.timestamp_valid = False
                result.warnings.append("Attestation timestamp is in the future")
            
            # Check age
            age = now - timestamp
            if age > timedelta(days=self.max_age_days):
                result.timestamp_valid = False
                result.warnings.append(f"Attestation is older than {self.max_age_days} days")
            
        except Exception as e:
            result.timestamp_valid = False
            result.warnings.append(f"Could not parse timestamp: {e}")
    
    def _check_parent_reference(
        self,
        attestation: Attestation,
        result: VerificationResult,
    ) -> None:
        """Check parent attestation reference."""
        if attestation.parent_attestation:
            # Parent reference exists, mark as referenced
            result.parent_referenced = True
        else:
            # Genesis attestation (no parent) is valid
            result.parent_referenced = True
    
    def _find_mismatched_components(
        self,
        attestation: Attestation,
        blueprint: Any,
    ) -> list[str]:
        """Find which components have mismatched hashes."""
        mismatched = []
        
        # This would require more detailed comparison
        # For now, return empty list
        
        return mismatched


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def verify_attestation(attestation: Attestation) -> VerificationResult:
    """
    Convenience function to verify an attestation.
    
    Args:
        attestation: Attestation to verify
    
    Returns:
        VerificationResult
    """
    verifier = ProvenanceVerifier()
    return verifier.verify(attestation)


def verify_blueprint_signature(
    attestation: Attestation,
    blueprint: Any,
) -> tuple[bool, list[str]]:
    """
    Verify both signature and content of an attestation.
    
    Args:
        attestation: Attestation to verify
        blueprint: Blueprint to verify against
    
    Returns:
        Tuple of (is_valid, list of errors)
    """
    verifier = ProvenanceVerifier()
    
    errors = []
    
    # Verify attestation
    result = verifier.verify(attestation)
    if not result.valid:
        errors.extend(result.errors)
        return False, errors
    
    # Verify content
    content_result = verifier.verify_content(attestation, blueprint)
    if not content_result.valid:
        errors.append(
            f"Content hash mismatch: expected {content_result.expected_hash[:16]}..., "
            f"got {content_result.computed_hash[:16]}..."
        )
        errors.extend(content_result.mismatched_components)
        return False, errors
    
    return True, []
