# Provenance Signing

**Summary**: Ed25519 cryptographic signing system for blueprints, creating verifiable attestations of authenticity and history.

**Sources**: `milimo-blueprint/orchestrator/provenance_signer.py`, `milimo-blueprint/orchestrator/provenance_verifier.py`

**Last updated**: 2026-04-15

**Tags**: #module #security #provenance #cryptography

---

## Overview

The provenance signing system creates cryptographic attestations for blueprints using Ed25519 signatures. This establishes a verifiable chain of authenticity from genesis to current version.

**File**: `orchestrator/provenance_signer.py`

---

## Key Classes

### `Attestation`

Cryptographic attestation of a blueprint.

| Field | Type | Description |
|-------|------|-------------|
| version | str | Attestation format version |
| blueprint_id | str | Blueprint identifier |
| blueprint_version | str | Semantic version |
| content_hash | str | SHA-256 hash of content |
| timestamp | str | ISO timestamp |
| author | AuthorInfo | Squad that signed |
| parent_attestation | str | Hash of parent (chain) |
| signature | str | Ed25519 signature |

### `ProvenanceSigner`

Main signer class.

```python
signer = ProvenanceSigner(squad_id="my-squad")
attestation = signer.sign_blueprint(blueprint_snapshot)
valid = signer.verify_attestation(attestation)
```

**Methods**:

| Method | Purpose |
|--------|---------|
| `sign_blueprint()` | Create signed attestation |
| `verify_attestation()` | Verify signature validity |
| `export_public_key()` | Export public key info |

---

## Content Hash Calculation

Content hash includes:

```python
calculate_content_hash(
    tools=tools_inventory,
    policies=policy_settings,
    evolution_config=evolution,
    performance_baseline=metrics
)
```

Components are sorted for deterministic hashing.

---

## Key Management

**Keystore**: `~/.milimo/keys/{squad_id}.json`

```python
# Generate new key pair
private_key, public_key = generate_key_pair()

# Save to keystore
save_key_pair(squad_id, private_key, public_key)

# Load from keystore
private_key, public_key = load_key_pair(squad_id)
```

---

## Provenance Verifier

`ProvenanceVerifier` validates attestations:

```python
verifier = ProvenanceVerifier(strict_mode=True)
result = verifier.verify(attestation)

if result.valid:
    print("Signature valid")
    print(f"Blueprint: {result.blueprint_id}")
else:
    print(f"Invalid: {result.errors}")
```

**Verification Checks**:

| Check | Description |
|-------|-------------|
| Required fields | Version, ID, hash, timestamp, author, signature |
| Signature | Ed25519 cryptographic verification |
| Timestamp | Not future-dated, not expired |
| Parent reference | Chain connectivity |

---

## Attestation Chain

```
Genesis Attestation (no parent)
       ↓
v0.1.0 → parent: genesis_hash
       ↓
v0.2.0 → parent: v0.1.0_hash
       ↓
v0.3.0 → parent: v0.2.0_hash
```

---

## Related Pages

- [[chain-validator]] — Chain validation
- [[attestation-generator]] — Performance attestations
- [[tool-generation]] — Evolution system
- [[evolution-cycle]] — Sunday evolution

---

## See Also

- `orchestrator/chain_validator.py` — Chain validation
- `orchestrator/attestation_generator.py` — Performance attestations
