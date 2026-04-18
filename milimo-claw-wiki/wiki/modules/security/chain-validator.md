# Chain Validator

**Summary**: Validates complete provenance chains ensuring all attestations form a valid sequence from origin to current version.

**Sources**: `milimo-blueprint/orchestrator/chain_validator.py`

**Last updated**: 2026-04-15

**Tags**: #module #security #provenance #validation

---

## Overview

`ChainValidator` ensures the complete attestation history of a blueprint is valid: connected, monotonically versioned, and properly signed.

**File**: `orchestrator/chain_validator.py`

---

## Key Classes

### `ChainValidationResult`

Result of chain validation.

| Field | Type | Description |
|-------|------|-------------|
| valid | bool | Overall validity |
| chain_length | int | Number of attestations |
| genesis_attestation_id | str | First attestation hash |
| latest_attestation_id | str | Most recent hash |
| author_squad_ids | list | All signing squads |
| version_sequence | list | Version numbers in order |
| forks | list | Detected forks |
| errors | list | Validation errors |
| warnings | list | Non-fatal issues |

---

### `ChainValidator`

Main validator class.

```python
validator = ChainValidator(strict_mode=True, allow_forks=False)
result = validator.validate_chain(attestations)

if result.valid:
    print(f"Chain valid: {result.chain_length} attestations")
    print(f"Versions: {result.version_sequence}")
```

**Methods**:

| Method | Purpose |
|--------|---------|
| `validate_chain()` | Validate complete chain |
| `validate_single_path()` | Validate linear path |
| `find_ancestor()` | Find attestation by version |
| `get_chain_summary()` | Chain summary stats |

---

## Validation Rules

### Connected Chain

Every attestation must reference its parent:

```
genesis → a1 → a2 → a3 (valid)
genesis → a1 → a2 → ??? (invalid - gap)
```

### Monotonic Versions

Versions must increase:

```
v0.1.0 → v0.2.0 → v0.3.0 (valid)
v0.1.0 → v0.2.0 → v0.1.5 (invalid - decreased)
```

### Valid Signatures

Each attestation must have valid Ed25519 signature.

### Timestamp Consistency

Timestamps should be sequential (within tolerance).

---

## Fork Detection

Forks occur when multiple attestations have the same parent:

```
     v0.2.0
       ↓
   v0.3.0-a  ← fork
   v0.3.0-b  ← fork
```

Forks are allowed by default but can be rejected:

```python
validator = ChainValidator(allow_forks=False)
```

---

## Version Comparison

```python
compare_versions("1.2.3", "1.2.4")  # Returns -1
compare_versions("1.2.3", "1.2.3")  # Returns 0
compare_versions("1.2.4", "1.2.3")  # Returns 1
```

---

## Integration Points

- **Input**: Attestations from [[provenance-signing]]
- **Used by**: Blueprint verification, marketplace listings
- **Related**: [[attestation-generator]]

---

## Related Pages

- [[provenance-signing]] — Attestation creation
- [[attestation-generator]] — Performance attestations
- [[tool-generation]] — Evolution system

---

## See Also

- `orchestrator/provenance_signer.py` — Signing
- `orchestrator/provenance_verifier.py` — Single verification
