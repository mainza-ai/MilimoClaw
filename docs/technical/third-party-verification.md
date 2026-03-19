# Third-Party Verification

**Version:** 1.0
**Date:** March 2026
**Status:** Implemented

---

## Overview

Third-party verification allows blueprint sellers to have their performance claims verified by accredited auditors. This provides buyers with higher confidence in the claimed performance metrics.

---

## Verification Levels

| Level | Method | Trust Score | Description |
|-------|--------|-------------|-------------|
| **Self-Attested** | `self_attested` | ⭐⭐ | Seller's own performance claims |
| **Backtest Verified** | `backtest` | ⭐⭐⭐ | Historical data simulation |
| **Live Measurement** | `live_measurement` | ⭐⭐⭐⭐ | Real-time performance tracking |
| **Auditor Verified** | `auditor_verified` | ⭐⭐⭐⭐⭐ | Independent third-party audit |

---

## Auditor Requirements

### Accreditation Standards

Auditors must meet the following requirements:

1. **Technical Competence**
   - Certified in ML/AI systems evaluation
   - Experience with autonomous agent systems
   - Understanding of performance metrics

2. **Independence**
   - No financial interest in the blueprint
   - No relationship with the seller
   - Independent verification infrastructure

3. **Security**
   - Secure data handling procedures
   - Ed25519 key pair for signing
   - Audit trail logging

4. **Professional Standards**
   - ISO 27001 certification (recommended)
   - Signed auditor agreement
   - Conflict of interest disclosure

### Accredited Auditors Registry

```json
{
  "auditors": [
    {
      "id": "aud_01",
      "name": "VerifAI Labs",
      "public_key": "ed25519:a1b2c3...",
      "accreditation": "ISO_27001",
      "website": "https://verifai.example.com",
      "fee_structure": {
        "standard": 50,
        "expedited": 150,
        "currency": "USD"
      }
    }
  ]
}
```

---

## Verification Process

### 1. Seller Request

Seller requests verification:

```bash
openclaw milimo badge --auditor auditor@example.com
```

This creates a verification request:

```json
{
  "request_id": "vr_abc123",
  "blueprint_id": "bp_xyz",
  "blueprint_version": "2.3.0",
  "seller_squad_id": "seller_squad",
  "auditor_id": "aud_01",
  "performance_attestation_id": "pa_xyz",
  "requested_at": "2026-03-18T12:00:00Z",
  "status": "pending",
  "data_access": {
    "type": "encrypted_transfer",
    "expires": "2026-04-18T12:00:00Z"
  }
}
```

### 2. Data Transfer

Seller provides verification data:

```json
{
  "verification_data": {
    "performance_logs": "encrypted_base64...",
    "tool_usage_history": "encrypted_base64...",
    "approval_records": "encrypted_base64...",
    "error_logs": "encrypted_base64...",
    "sample_operations": [
      "operation_id_1",
      "operation_id_2",
      "..."
    ]
  },
  "encryption": {
    "algorithm": "AES-256-GCM",
    "key_exchange": "ECDH-P256",
    "auditor_public_key": "auditor_ephemeral_key..."
  }
}
```

### 3. Auditor Verification

Auditor performs verification:

1. **Data Integrity Check**
   - Verify encrypted data can be decrypted
   - Check data completeness
   - Validate timestamp ranges

2. **Performance Calculation**
   - Recalculate performance metrics
   - Compare with seller's claims
   - Identify any discrepancies

3. **Operational Review**
   - Examine approval patterns
   - Check error handling
   - Verify tool usage statistics

4. **Finding Documentation**
   - Document any issues found
   - Calculate confidence intervals
   - Prepare verification report

### 4. Verification Result

Auditor signs and returns result:

```json
{
  "type": "auditor_verification",
  "verification_request_id": "vr_abc123",
  "performance_attestation_id": "pa_xyz",
  "auditor": {
    "id": "aud_01",
    "name": "VerifAI Labs",
    "public_key": "ed25519:a1b2c3...",
    "accreditation": "ISO_27001"
  },
  "verification_result": "passed",
  "verification_date": "2026-03-20T14:30:00Z",
  "findings": [],
  "verified_metrics": {
    "improvement_percent": 12.3,
    "confidence_interval": {
      "lower": 10.8,
      "upper": 13.8,
      "confidence_level": 0.95
    }
  },
  "limitations": [
    "Data limited to 90-day period",
    "Single squad deployment"
  ],
  "signature": "ed25518:auditor_signature...",
  "expires_at": "2027-03-20T14:30:00Z"
}
```

---

## Fee Structure

### Standard Fees

| Service | Fee | Turnaround |
|---------|-----|------------|
| Basic Verification | $50 | 5-7 days |
| Expedited | $150 | 2-3 days |
| Premium (Real-time) | $500 | 24 hours |
| Re-verification | $25 | 3-5 days |

### Payment Process

1. Seller pays verification fee through platform
2. Platform holds payment in escrow
3. Auditor completes verification
4. Payment released to auditor upon completion

---

## Verification Badge Display

### Marketplace Display

When a blueprint has auditor verification:

```
┌─────────────────────────────────────────┐
│ 🥈 Silver Performance Badge             │
│ +12.3% improvement (auditor verified)   │
│ ✅ Verified by VerifAI Labs             │
│ 📊 95% confidence: 10.8% - 13.8%       │
└─────────────────────────────────────────┘
```

### CLI Display

```bash
$ openclaw milimo badge --verify bp_xyz

  🔍 Verification Status: ✅ VERIFIED

  Auditor: VerifAI Labs (ISO 27001)
  Verified: 2026-03-20
  Expires: 2027-03-20

  Performance: +12.3% (±1.5% at 95% confidence)
  Method: Live measurement + backtest

  Limitations:
    - Data limited to 90-day period
    - Single squad deployment
```

---

## Dispute Resolution

### Contesting Verification

If seller disagrees with findings:

1. Seller submits dispute with evidence
2. Auditor reviews new information
3. Either updated verification or confirmation issued
4. Platform mediates if no resolution

### Verification Revocation

Auditors may revoke verification if:

- Fraudulent data discovered
- Blueprint modified significantly
- Performance claims become inaccurate
- Conflict of interest discovered

---

## Implementation Files

| File | Purpose |
|------|---------|
| `badge.ts` | CLI for verification requests |
| `performance-attestation.json` | Attestation schema |
| `provenance_signer.py` | Sign verification results |
| `provenance_verifier.py` | Verify auditor signatures |

---

## API Endpoints

### Request Verification

```http
POST /api/verification/request
Content-Type: application/json

{
  "blueprint_id": "bp_xyz",
  "attestation_id": "pa_abc",
  "auditor_id": "aud_01",
  "expedited": false
}
```

### Check Verification Status

```http
GET /api/verification/{request_id}
```

### Submit Verification Data

```http
POST /api/verification/{request_id}/data
Content-Type: application/json

{
  "encrypted_data": "...",
  "key_package": "..."
}
```

---

## Security Considerations

### Data Protection

- All verification data encrypted end-to-end
- Auditor cannot see raw operational data
- Data expires after verification complete
- Seller controls data access window

### Auditor Security

- Auditors use hardware security modules for signing keys
- Multi-signature required for high-value blueprints
- Audit trail of all verification actions
- Regular security audits of auditor infrastructure

---

## References

- [ISO/IEC 27001](https://www.iso.org/isoiec-27001-information-security.html) - Information Security Management
- [Ed25519](https://ed25519.cr.yp.to/) - Digital Signatures
- [ECDH](https://en.wikipedia.org/wiki/Elliptic-curve_Diffie%E2%80%93Hellman) - Key Exchange
