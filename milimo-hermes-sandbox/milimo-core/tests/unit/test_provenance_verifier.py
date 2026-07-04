# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for the provenance verifier.
"""

from datetime import datetime, timezone, timedelta
import hmac
import hashlib
from typing import Any
import pytest

from milimo_core.provenance_signer import Attestation, AuthorInfo, EvolutionSummary
from milimo_core.provenance_verifier import (
    ProvenanceVerifier,
    VerificationResult,
    verify_attestation,
    verify_blueprint_signature,
    CRYPTO_AVAILABLE,
)

if CRYPTO_AVAILABLE:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


class MockBlueprint:
    """Mock blueprint class for testing verify_content."""
    def __init__(self):
        self.tools_inventory = {"tool1": "code"}
        self.policy = {"sandbox": "restricted"}
        self.claw_config = {"evolution": {"interval_hours": 24}}
        self.learned_priors = {"performance": {"metric": 0.8}}


@pytest.fixture
def keys():
    """Generate or mock a key pair."""
    if CRYPTO_AVAILABLE:
        private_key = Ed25519PrivateKey.generate()
        public_bytes = private_key.public_key().public_bytes_raw()
        public_key_hex = public_bytes.hex()
        return private_key, public_key_hex
    else:
        # Mock public key for HMAC
        return None, "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff"


@pytest.fixture
def valid_attestation(keys):
    """Create a valid attestation with a correct signature."""
    private_key, public_key_hex = keys
    author = AuthorInfo(
        squad_id="zulu",
        public_key=f"ed25519:{public_key_hex}",
        key_id="key-1",
    )

    # Calculate a valid mock content hash (sha256 of "content")
    content_hash = hashlib.sha256(b"content").hexdigest()

    attestation = Attestation(
        version="1.0",
        blueprint_id="bp-123",
        blueprint_version="0.1.0",
        content_hash=f"sha256:{content_hash}",
        timestamp=datetime.now(timezone.utc).isoformat(),
        author=author,
        parent_attestation=None,
    )

    # Sign signable bytes
    signable = attestation.to_signable_bytes()
    if CRYPTO_AVAILABLE:
        sig_bytes = private_key.sign(signable)
        attestation.signature = f"ed25519:{sig_bytes.hex()}"
    else:
        # Mock HMAC signature
        expected_sig = hmac.new(
            bytes.fromhex(public_key_hex), signable, hashlib.sha256
        ).digest()
        attestation.signature = f"ed25519:{expected_sig.hex()}"

    return attestation


def test_verify_valid_attestation(valid_attestation) -> None:
    """Verify that a valid attestation passes verification."""
    verifier = ProvenanceVerifier()
    res = verifier.verify(valid_attestation)
    assert res.valid is True
    assert res.signature_valid is True
    assert res.timestamp_valid is True
    assert not res.errors
    assert not res.warnings


def test_verify_missing_fields() -> None:
    """Verify that missing fields trigger verification failures."""
    verifier = ProvenanceVerifier()

    # Missing version
    att = Attestation(version="")
    res = verifier.verify(att)
    assert res.valid is False
    assert "Missing attestation version" in res.errors

    # Missing blueprint_id
    att = Attestation(version="1.0", blueprint_id="")
    res = verifier.verify(att)
    assert res.valid is False
    assert "Missing blueprint_id" in res.errors


def test_verify_missing_author() -> None:
    """Verify that missing author information triggers failure."""
    verifier = ProvenanceVerifier()
    att = Attestation(
        version="1.0",
        blueprint_id="bp-123",
        blueprint_version="0.1.0",
        content_hash="sha256:abc",
        timestamp=datetime.now(timezone.utc).isoformat(),
        author=None,
    )
    res = verifier.verify(att)
    assert res.valid is False
    assert "Missing author information" in res.errors


def test_verify_missing_author_fields(keys) -> None:
    """Verify that missing nested author fields trigger failure."""
    verifier = ProvenanceVerifier()
    _, public_key_hex = keys

    # Missing squad_id
    author = AuthorInfo(squad_id="", public_key=f"ed25519:{public_key_hex}", key_id="key-1")
    att = Attestation(
        version="1.0",
        blueprint_id="bp-123",
        blueprint_version="0.1.0",
        content_hash="sha256:abc",
        timestamp=datetime.now(timezone.utc).isoformat(),
        author=author,
    )
    res = verifier.verify(att)
    assert res.valid is False
    assert "Missing author squad_id" in res.errors


def test_verify_invalid_signature(valid_attestation) -> None:
    """Verify that an altered signature fails verification."""
    verifier = ProvenanceVerifier()
    valid_attestation.signature = "ed25519:" + "0" * 128
    res = verifier.verify(valid_attestation)
    assert res.valid is False
    assert res.signature_valid is False
    assert "Invalid signature" in res.errors[0]


def test_verify_future_timestamp(valid_attestation) -> None:
    """Verify that an attestation in the future raises a warning."""
    verifier = ProvenanceVerifier()
    future_time = datetime.now(timezone.utc) + timedelta(minutes=10)
    valid_attestation.timestamp = future_time.isoformat()

    # Re-sign for new timestamp
    # (For simplicity we disable signature checking by making CRYPTO_AVAILABLE false or patching)
    res = verifier.verify(valid_attestation)
    assert res.timestamp_valid is False
    assert any("timestamp is in the future" in w for w in res.warnings)


def test_verify_old_timestamp(valid_attestation) -> None:
    """Verify that an old attestation raises a warning."""
    verifier = ProvenanceVerifier(max_age_days=1)
    old_time = datetime.now(timezone.utc) - timedelta(days=2)
    valid_attestation.timestamp = old_time.isoformat()

    res = verifier.verify(valid_attestation)
    assert res.timestamp_valid is False
    assert any("older than 1 days" in w for w in res.warnings)


def test_strict_mode(valid_attestation) -> None:
    """Verify that strict mode turns warnings into failures."""
    verifier = ProvenanceVerifier(max_age_days=1, strict_mode=True)
    old_time = datetime.now(timezone.utc) - timedelta(days=2)
    valid_attestation.timestamp = old_time.isoformat()

    res = verifier.verify(valid_attestation)
    assert res.valid is False
    assert "Strict mode: warnings treated as errors" in res.errors


def test_verify_content_mismatch(valid_attestation) -> None:
    """Verify verify_content failure when hashes do not match."""
    verifier = ProvenanceVerifier()
    bp = MockBlueprint()

    res = verifier.verify_content(valid_attestation, bp)
    assert res.valid is False
    assert res.expected_hash != res.computed_hash


def test_convenience_verify_attestation(valid_attestation) -> None:
    """Verify convenience verification wrapper."""
    res = verify_attestation(valid_attestation)
    assert res.valid is True


def test_convenience_verify_blueprint_signature_invalid(valid_attestation) -> None:
    """Verify verify_blueprint_signature checks signature first."""
    valid_attestation.signature = ""
    valid, errors = verify_blueprint_signature(valid_attestation, MockBlueprint())
    assert valid is False
    assert "Missing signature" in errors
