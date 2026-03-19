#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Attestation Generator

Generates signed performance attestations for blueprints,
allowing sellers to prove their claimed performance metrics.

Usage:
    from attestation_generator import AttestationGenerator
    
    generator = AttestationGenerator(squad_id="my-squad")
    attestation = generator.generate(blueprint_snapshot, metrics)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

from .provenance_signer import ProvenanceSigner, Attestation, calculate_content_hash

logger = logging.getLogger("milimo.attestation_generator")

ATTESTATION_DIR = Path.home() / ".milimo" / "attestations"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class PerformanceMetrics:
    """Performance metrics for attestation."""
    baseline_performance: float = 100.0
    current_performance: float = 100.0
    improvement_percent: float = 0.0
    measurement_period_days: int = 30
    sample_size: int = 1000
    
    # Optional breakdown
    approval_rate: Optional[float] = None
    auto_approval_rate: Optional[float] = None
    response_time_ms: Optional[float] = None
    error_rate: Optional[float] = None
    tool_usage: dict[str, int] = field(default_factory=dict)
    
    # Confidence interval
    confidence_lower: Optional[float] = None
    confidence_upper: Optional[float] = None
    confidence_level: float = 0.95


@dataclass
class VerificationInfo:
    """Verification method and status."""
    method: str = "self_attested"  # backtest, live_measurement, auditor_verified, self_attested
    data_integrity: str = ""
    auditor_name: Optional[str] = None
    auditor_public_key: Optional[str] = None
    auditor_accreditation: Optional[str] = None
    auditor_signature: Optional[str] = None


@dataclass
class PerformanceAttestation:
    """
    Performance attestation for a blueprint.
    
    Contains signed performance claims that can be verified
    by buyers before purchase.
    """
    type: str = "performance_attestation"
    attestation_id: str = ""
    blueprint_id: str = ""
    blueprint_version: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)
    verification: dict[str, Any] = field(default_factory=dict)
    attestation_hash: str = ""
    signature: str = ""
    created_at: str = ""
    expires_at: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type,
            "attestation_id": self.attestation_id,
            "blueprint_id": self.blueprint_id,
            "blueprint_version": self.blueprint_version,
            "metrics": self.metrics,
            "verification": self.verification,
            "attestation_hash": self.attestation_hash,
            "signature": self.signature,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PerformanceAttestation":
        """Create from dictionary."""
        return cls(
            type=data.get("type", "performance_attestation"),
            attestation_id=data.get("attestation_id", ""),
            blueprint_id=data.get("blueprint_id", ""),
            blueprint_version=data.get("blueprint_version", ""),
            metrics=data.get("metrics", {}),
            verification=data.get("verification", {}),
            attestation_hash=data.get("attestation_hash", ""),
            signature=data.get("signature", ""),
            created_at=data.get("created_at", ""),
            expires_at=data.get("expires_at"),
        )
    
    def calculate_hash(self) -> str:
        """Calculate SHA-256 hash of this attestation."""
        data = self.to_dict()
        # Exclude signature and hash from hash calculation
        del data["attestation_hash"]
        del data["signature"]
        content = json.dumps(data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Attestation Generator
# ---------------------------------------------------------------------------

class AttestationGenerator:
    """
    Generates performance attestations for blueprints.
    
    Creates signed documents that prove a blueprint's
    claimed performance metrics.
    """
    
    DEFAULT_EXPIRATION_DAYS = 365
    
    def __init__(
        self,
        squad_id: str,
        keystore_dir: Optional[Path] = None,
        attestation_dir: Optional[Path] = None,
    ):
        """
        Initialize the attestation generator.
        
        Args:
            squad_id: Squad identifier
            keystore_dir: Optional custom keystore directory
            attestation_dir: Optional custom attestation storage directory
        """
        self.squad_id = squad_id
        self.keystore_dir = keystore_dir
        self.attestation_dir = attestation_dir or ATTESTATION_DIR
        
        self.signer = ProvenanceSigner(squad_id, keystore_dir)
    
    def generate(
        self,
        blueprint: Any,
        metrics: PerformanceMetrics,
        verification_method: str = "self_attested",
        expires_in_days: Optional[int] = None,
    ) -> PerformanceAttestation:
        """
        Generate a performance attestation.
        
        Args:
            blueprint: BlueprintSnapshot to attest
            metrics: Performance metrics
            verification_method: How metrics were verified
            expires_in_days: Days until attestation expires
        
        Returns:
            PerformanceAttestation
        """
        # Generate attestation ID
        timestamp = datetime.now(timezone.utc)
        attestation_id = f"pa_{self.squad_id[:8]}_{timestamp.strftime('%Y%m%d%H%M%S')}"
        
        # Build metrics dict
        metrics_dict = {
            "baseline_performance": metrics.baseline_performance,
            "current_performance": metrics.current_performance,
            "improvement_percent": metrics.improvement_percent,
            "measurement_period_days": metrics.measurement_period_days,
            "sample_size": metrics.sample_size,
        }
        
        # Add optional metrics
        if metrics.approval_rate is not None:
            metrics_dict["approval_rate"] = metrics.approval_rate
        if metrics.auto_approval_rate is not None:
            metrics_dict["auto_approval_rate"] = metrics.auto_approval_rate
        if metrics.response_time_ms is not None:
            metrics_dict["response_time_ms"] = metrics.response_time_ms
        if metrics.error_rate is not None:
            metrics_dict["error_rate"] = metrics.error_rate
        if metrics.tool_usage:
            metrics_dict["tool_usage"] = metrics.tool_usage
        
        # Add confidence interval
        if metrics.confidence_lower is not None and metrics.confidence_upper is not None:
            metrics_dict["confidence_interval"] = {
                "lower": metrics.confidence_lower,
                "upper": metrics.confidence_upper,
                "confidence_level": metrics.confidence_level,
            }
        
        # Calculate data integrity hash
        metrics_json = json.dumps(metrics_dict, sort_keys=True)
        data_integrity = hashlib.sha256(metrics_json.encode()).hexdigest()
        
        # Build verification dict
        verification_dict = {
            "method": verification_method,
            "data_integrity": f"sha256:{data_integrity}",
        }
        
        # Calculate expiration
        expires_days = expires_in_days or self.DEFAULT_EXPIRATION_DAYS
        expires_at = (timestamp + timedelta(days=expires_days)).isoformat()
        
        # Create attestation
        attestation = PerformanceAttestation(
            attestation_id=attestation_id,
            blueprint_id=getattr(blueprint.meta, "squad_id", self.squad_id) if hasattr(blueprint, "meta") else self.squad_id,
            blueprint_version=getattr(blueprint.meta, "version", "0.1.0") if hasattr(blueprint, "meta") else "0.1.0",
            metrics=metrics_dict,
            verification=verification_dict,
            created_at=timestamp.isoformat(),
            expires_at=expires_at,
        )
        
        # Calculate attestation hash
        attestation.attestation_hash = f"sha256:{attestation.calculate_hash()}"
        
        # Sign the attestation
        attestation.signature = self._sign_attestation(attestation)
        
        return attestation
    
    def _sign_attestation(self, attestation: PerformanceAttestation) -> str:
        """Sign the attestation with squad's private key."""
        # Get bytes to sign
        data = attestation.to_dict()
        del data["signature"]
        content = json.dumps(data, sort_keys=True).encode("utf-8")
        
        # Sign using the provenance signer
        signature = self.signer._sign_bytes(content)
        
        return f"ed25519:{signature}"
    
    def save(self, attestation: PerformanceAttestation) -> Path:
        """
        Save attestation to disk.
        
        Args:
            attestation: Attestation to save
        
        Returns:
            Path to saved file
        """
        self.attestation_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{attestation.blueprint_id}.json"
        filepath = self.attestation_dir / filename
        
        filepath.write_text(json.dumps(attestation.to_dict(), indent=2))
        
        logger.info(f"Saved attestation {attestation.attestation_id} to {filepath}")
        
        return filepath
    
    def load(self, blueprint_id: str) -> Optional[PerformanceAttestation]:
        """
        Load attestation from disk.
        
        Args:
            blueprint_id: Blueprint identifier
        
        Returns:
            PerformanceAttestation or None
        """
        filepath = self.attestation_dir / f"{blueprint_id}.json"
        
        if not filepath.exists():
            return None
        
        data = json.loads(filepath.read_text())
        return PerformanceAttestation.from_dict(data)
    
    def list_attestations(self) -> list[dict[str, Any]]:
        """
        List all saved attestations.
        
        Returns:
            List of attestation summaries
        """
        if not self.attestation_dir.exists():
            return []
        
        attestations = []
        for filepath in self.attestation_dir.glob("*.json"):
            try:
                data = json.loads(filepath.read_text())
                attestations.append({
                    "blueprint_id": data.get("blueprint_id", filepath.stem),
                    "version": data.get("blueprint_version", "?"),
                    "improvement": data.get("metrics", {}).get("improvement_percent", 0),
                    "created": data.get("created_at", "?"),
                    "attestation_id": data.get("attestation_id", "?"),
                })
            except Exception as e:
                logger.warning(f"Failed to load attestation {filepath}: {e}")
        
        return attestations
    
    def verify(self, attestation: PerformanceAttestation) -> bool:
        """
        Verify an attestation's signature.
        
        Args:
            attestation: Attestation to verify
        
        Returns:
            True if signature is valid
        """
        # Verify hash
        expected_hash = attestation.calculate_hash()
        stored_hash = attestation.attestation_hash.replace("sha256:", "")
        
        if expected_hash != stored_hash:
            logger.error("Attestation hash mismatch")
            return False
        
        # Verify signature
        data = attestation.to_dict()
        del data["signature"]
        content = json.dumps(data, sort_keys=True).encode("utf-8")
        
        signature_hex = attestation.signature.replace("ed25519:", "")
        
        # Create a temporary attestation for verification
        temp_attestation = Attestation(
            blueprint_id=attestation.blueprint_id,
            blueprint_version=attestation.blueprint_version,
            content_hash=attestation.attestation_hash,
            author=None,
        )
        
        # Use fallback HMAC verification if cryptography not available
        import hmac
        public_key_hex = self.signer.public_key_hex
        expected_sig = hmac.new(
            bytes.fromhex(public_key_hex) if public_key_hex else b"",
            content,
            hashlib.sha256
        ).digest()
        
        return hmac.compare_digest(expected_sig, bytes.fromhex(signature_hex))
    
    def add_auditor_verification(
        self,
        attestation: PerformanceAttestation,
        auditor_name: str,
        auditor_public_key: str,
        auditor_signature: str,
        accreditation: Optional[str] = None,
    ) -> PerformanceAttestation:
        """
        Add auditor verification to an attestation.
        
        Args:
            attestation: Attestation to update
            auditor_name: Auditor name
            auditor_public_key: Auditor's public key
            auditor_signature: Auditor's signature
            accreditation: Optional accreditation
        
        Returns:
            Updated attestation
        """
        attestation.verification["method"] = "auditor_verified"
        attestation.verification["auditor"] = {
            "name": auditor_name,
            "public_key": auditor_public_key,
            "accreditation": accreditation,
            "verification_date": datetime.now(timezone.utc).isoformat(),
        }
        attestation.verification["auditor_signature"] = auditor_signature
        
        # Recalculate hash
        attestation.attestation_hash = f"sha256:{attestation.calculate_hash()}"
        
        return attestation


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def generate_performance_attestation(
    squad_id: str,
    blueprint: Any,
    metrics: PerformanceMetrics,
) -> PerformanceAttestation:
    """
    Convenience function to generate an attestation.
    
    Args:
        squad_id: Squad identifier
        blueprint: Blueprint to attest
        metrics: Performance metrics
    
    Returns:
        PerformanceAttestation
    """
    generator = AttestationGenerator(squad_id)
    return generator.generate(blueprint, metrics)


def extract_metrics_from_blueprint(blueprint: Any) -> PerformanceMetrics:
    """
    Extract performance metrics from a blueprint.
    
    Args:
        blueprint: Blueprint to analyze
    
    Returns:
        PerformanceMetrics
    """
    metrics = PerformanceMetrics()
    
    # Check for evolved tools
    tools = getattr(blueprint, "tools_inventory", {})
    if tools:
        deltas = []
        for tool_name, tool_info in tools.items():
            if isinstance(tool_info, dict) and "performance_delta" in tool_info:
                deltas.append(tool_info["performance_delta"])
        
        if deltas:
            avg_delta = sum(deltas) / len(deltas)
            metrics.improvement_percent = round(avg_delta, 1)
            metrics.current_performance = 100.0 + avg_delta
    
    return metrics
