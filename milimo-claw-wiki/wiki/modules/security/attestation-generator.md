# Attestation Generator

**Summary**: Generates signed performance attestations for blueprints, allowing sellers to prove claimed performance metrics.

**Sources**: `milimo-blueprint/orchestrator/attestation_generator.py`

**Last updated**: 2026-04-15

**Tags**: #module #security #provenance #performance

---

## Overview

`AttestationGenerator` creates signed performance attestations that prove a blueprint's claimed metrics. Used in marketplace listings and blueprint sharing.

**File**: `orchestrator/attestation_generator.py`

---

## Key Classes

### `PerformanceMetrics`

Performance metrics for attestation.

| Field | Type | Description |
|-------|------|-------------|
| baseline_performance | float | Starting performance |
| current_performance | float | Current performance |
| improvement_percent | float | Improvement over baseline |
| measurement_period_days | int | Measurement window |
| sample_size | int | Number of samples |
| approval_rate | float | Action approval rate |
| auto_approval_rate | float | Auto-approval rate |
| error_rate | float | Error rate |
| confidence_lower | float | Confidence interval lower |
| confidence_upper | float | Confidence interval upper |

### `PerformanceAttestation`

Signed performance claim.

| Field | Type | Description |
|-------|------|-------------|
| attestation_id | str | Unique ID |
| blueprint_id | str | Blueprint identifier |
| blueprint_version | str | Version |
| metrics | dict | Performance data |
| verification | dict | Verification method |
| signature | str | Ed25519 signature |
| expires_at | str | Expiration timestamp |

---

### `AttestationGenerator`

Main generator class.

```python
generator = AttestationGenerator(squad_id="my-squad")

metrics = PerformanceMetrics(
    baseline_performance=100.0,
    current_performance=115.0,
    improvement_percent=15.0,
    sample_size=1000
)

attestation = generator.generate(blueprint, metrics)
generator.save(attestation)
```

**Methods**:

| Method | Purpose |
|--------|---------|
| `generate()` | Create performance attestation |
| `save()` | Persist to disk |
| `load()` | Load from disk |
| `verify()` | Verify signature |
| `add_auditor_verification()` | Add third-party audit |

---

## Verification Methods

| Method | Description |
|--------|-------------|
| `self_attested` | Squad's own measurement |
| `backtest` | Historical data analysis |
| `live_measurement` | Real-time tracking |
| `auditor_verified` | Third-party audit |

---

## Storage

Attestations stored at: `~/.milimo/attestations/{blueprint_id}.json`

---

## Auditor Verification

```python
generator.add_auditor_verification(
    attestation,
    auditor_name="TrustAudit Inc",
    auditor_public_key="ed25519:...",
    auditor_signature="...",
    accreditation="ISO 27001"
)
```

---

## Related Pages

- [[provenance-signing]] — Blueprint signing
- [[chain-validator]] — Chain validation
- [[evolution-cycle]] — Performance tracking

---

## See Also

- `orchestrator/provenance_signer.py` — Signing infrastructure
- `orchestrator/chain_validator.py` — Chain validation
