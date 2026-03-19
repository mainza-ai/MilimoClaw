# Cryptographic Provenance Verification

**Version:** 1.0
**Date:** March 2026
**Status:** Implemented

---

## Overview

The Milimo Claw provenance system provides cryptographic proof of blueprint operational history. Every blueprint is signed using Ed25519 signatures, creating a verifiable chain from the original template through all evolutions and forks.

---

## Design Goals

1. **Tamper Evidence**: Any modification to a blueprint invalidates its signature
2. **Non-Repudiation**: Sellers cannot deny authorship of their blueprints
3. **Chain of Custody**: Complete history from origin to current version
4. **Privacy Preserving**: No operational data exposed in signatures
5. **Offline Verifiable**: No external service required for verification

---

## Cryptographic Scheme

### Algorithm Selection

| Component | Algorithm | Key Size | Rationale |
|-----------|-----------|----------|-----------|
| Signature | Ed25519 | 256-bit | Fast, secure, widely supported |
| Hash | SHA-256 | 256-bit | Standard, collision-resistant |
| Key Derivation | HKDF-SHA256 | N/A | Secure key expansion |

### Key Management

```
Squad Key Pair
├── Private Key: Ed25519 signing key (never leaves device)
├── Public Key: Published with blueprint
└── Key ID: SHA-256(public_key)[:8] for identification
```

---

## Signature Format

### Blueprint Attestation

```json
{
  "version": "1.0",
  "blueprint_id": "bp_abc123",
  "blueprint_version": "2.3.0",
  "content_hash": "sha256:a1b2c3...",
  "timestamp": "2026-03-18T12:00:00Z",
  "author": {
    "squad_id": "squad_xyz",
    "public_key": "ed25519:MCowBQYDK2VwAy...",
    "key_id": "a1b2c3d4"
  },
  "parent_attestation": "sha256:prev_hash...",
  "evolution_summary": {
    "tools_added": ["tone_classifier_v2"],
    "tools_removed": [],
    "performance_delta": 12.5
  },
  "signature": "ed25519:signature_hex..."
}
```

### Content Hash Calculation

The content hash covers all blueprint components:

```python
def calculate_content_hash(blueprint: BlueprintSnapshot) -> str:
    """
    Calculate SHA-256 hash of blueprint content.
    
    Hashed components:
    - Tool configurations (sorted by name)
    - Policy settings (sorted by key)
    - Evolution parameters
    - Performance baseline
    
    Excludes:
    - Timestamps (signed separately)
    - Metadata (non-functional)
    """
    components = []
    
    # Tools (sorted for deterministic hash)
    for tool in sorted(blueprint.tools, key=lambda t: t.name):
        components.append(f"tool:{tool.name}:{tool.version}:{tool.config_hash}")
    
    # Policies (sorted by key)
    for key in sorted(blueprint.policies.keys()):
        components.append(f"policy:{key}:{blueprint.policies[key]}")
    
    # Evolution settings
    components.append(f"evolution:{blueprint.evolution_config_hash}")
    
    # Performance baseline
    components.append(f"baseline:{blueprint.performance_baseline_hash}")
    
    content = "\n".join(components)
    return hashlib.sha256(content.encode()).hexdigest()
```

---

## Provenance Chain

### Chain Structure

```
Genesis Attestation (v0.1.0)
        │
        ├── Evolution 1 (v1.0.0)
        │       │
        │       ├── Evolution 1.1 (v1.1.0)
        │       │       │
        │       │       └── Current Version (v2.3.0)
        │       │
        │       └── Fork A (published)
        │               │
        │               └── Evolution A.1 (v1.0.1)
        │
        └── Fork B (published)
                │
                └── Evolution B.1
```

### Chain Validation Rules

1. **Genesis Block**: Must be self-signed, no parent
2. **Evolution Block**: Must reference valid parent attestation
3. **Fork Block**: Must reference source blueprint attestation
4. **Version Sequence**: Versions must increase monotonically
5. **Content Integrity**: Content hash must match attestation

---

## Signing Process

### Creating a New Blueprint

```python
async def create_blueprint_attestation(
    blueprint: BlueprintSnapshot,
    private_key: Ed25519PrivateKey,
    parent_attestation: Optional[Attestation] = None
) -> Attestation:
    """
    Create a signed attestation for a blueprint.
    """
    # Calculate content hash
    content_hash = calculate_content_hash(blueprint)
    
    # Build attestation
    attestation = Attestation(
        version="1.0",
        blueprint_id=blueprint.id,
        blueprint_version=blueprint.version,
        content_hash=f"sha256:{content_hash}",
        timestamp=datetime.utcnow().isoformat() + "Z",
        author=AuthorInfo(
            squad_id=blueprint.squad_id,
            public_key=f"ed25519:{private_key.public_key().hex()}",
            key_id=private_key.public_key().hex()[:8]
        ),
        parent_attestation=parent_attestation.hash() if parent_attestation else None,
        evolution_summary=extract_evolution_summary(blueprint, parent_attestation)
    )
    
    # Sign attestation
    attestation_bytes = attestation.to_signable_bytes()
    signature = private_key.sign(attestation_bytes)
    attestation.signature = f"ed25519:{signature.hex()}"
    
    return attestation
```

### Verification Process

```python
def verify_attestation(attestation: Attestation) -> ValidationResult:
    """
    Verify a blueprint attestation signature.
    """
    # Extract public key
    public_key = Ed25519PublicKey.from_hex(attestation.author.public_key)
    
    # Verify signature
    attestation_bytes = attestation.to_signable_bytes()
    signature = bytes.fromhex(attestation.signature.replace("ed25519:", ""))
    
    try:
        public_key.verify(signature, attestation_bytes)
    except InvalidSignature:
        return ValidationResult(valid=False, error="Invalid signature")
    
    # Verify content hash
    # (Content hash verification requires blueprint data)
    
    return ValidationResult(valid=True)
```

---

## Security Considerations

### Private Key Protection

1. **Storage**: Keys stored in OS keychain (Keychain on macOS, Credential Manager on Windows)
2. **Access**: Keys only accessible to the squad owner
3. **Backup**: Encrypted backup with recovery phrase
4. **Rotation**: Key rotation supported with attestation re-signing

### Attack Mitigations

| Attack | Mitigation |
|--------|------------|
| Key Compromise | Key rotation, attestation invalidation |
| Replay Attack | Timestamp in attestation, version sequence |
| Content Tampering | Content hash verification |
| Chain Forgery | Parent attestation reference, signature chain |
| Man-in-the-Middle | End-to-end signatures, no intermediaries |

---

## Performance Verification

### Performance Attestation

Sellers can generate signed performance attestations:

```json
{
  "type": "performance_attestation",
  "blueprint_id": "bp_abc123",
  "blueprint_version": "2.3.0",
  "metrics": {
    "baseline_performance": 100,
    "current_performance": 112.5,
    "improvement_percent": 12.5,
    "measurement_period_days": 90,
    "sample_size": 15420
  },
  "verification": {
    "method": "backtest",
    "auditor": null,
    "data_integrity": "sha256:metrics_hash..."
  },
  "attestation_hash": "sha256:attestation_hash...",
  "signature": "ed25519:signature..."
}
```

### Third-Party Verification

Optional auditor verification for high-value blueprints:

```json
{
  "type": "auditor_verification",
  "performance_attestation_id": "pa_xyz",
  "auditor": {
    "name": "Verifier Inc.",
    "public_key": "ed25519:auditor_key...",
    "accreditation": "ISO_27001"
  },
  "verification_result": "passed",
  "verification_date": "2026-03-18",
  "findings": [],
  "signature": "ed25519:auditor_signature..."
}
```

---

## API Endpoints

### CLI Commands

```bash
# Generate key pair for squad
openclaw milimo provenance keygen --squad my-squad

# Sign a blueprint version
openclaw milimo provenance sign --version 2.3.0

# Verify a blueprint
openclaw milimo verify --blueprint bp_abc123

# Show provenance chain
openclaw milimo verify --blueprint bp_abc123 --chain

# Generate performance attestation
openclaw milimo badge --blueprint bp_abc123 --performance

# Request auditor verification
openclaw milimo badge --blueprint bp_abc123 --auditor verify@example.com
```

---

## Implementation Files

| File | Purpose |
|------|---------|
| `provenance_signer.py` | Sign blueprints with Ed25519 |
| `provenance_verifier.py` | Verify blueprint signatures |
| `chain_validator.py` | Validate full provenance chain |
| `verify.ts` | CLI verification command |
| `badge.ts` | Performance attestation command |

---

## References

- [Ed25519](https://ed25519.cr.yp.to/) - High-speed high-security signatures
- [RFC 8032](https://tools.ietf.org/html/rfc8032) - Edwards-Curve Digital Signature Algorithm
- [Keychain Services](https://developer.apple.com/documentation/security/keychain_services) - Secure key storage on macOS
