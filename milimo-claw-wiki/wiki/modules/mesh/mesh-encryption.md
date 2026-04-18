# Mesh Encryption

**Summary**: AES-256-GCM encryption for inter-claw messages.

**Sources**:
- `milimo-blueprint/orchestrator/mesh_encryption.py`

**Last updated**: 2026-04-17

**Tags**: #module #mesh #security #encryption

---

## Overview

MessageEncryption provides AES-256-GCM encryption for inter-claw messages. Key derivation uses PBKDF2 with claw-pair salt. Must be interoperable with TypeScript implementation.

---

## Key Class

### `MessageEncryption`

```python
class MessageEncryption:
    def __init__(self, mesh_secret: str) -> None:
        self.mesh_secret = mesh_secret
```

**Requirements**: `cryptography` library

---

## Data Classes

### `EncryptedMessage`

```python
@dataclass
class EncryptedMessage:
    iv: str           # Initialization vector (base64)
    ciphertext: str   # Encrypted content (base64)
    auth_tag: str     # Authentication tag (base64)
    timestamp: str    # ISO timestamp
```

---

## Constants

```python
ALGORITHM = "aes-256-gcm"
KEY_LENGTH = 32
IV_LENGTH = 16
AUTH_TAG_LENGTH = 16
PBKDF2_ITERATIONS = 100000
```

---

## Methods

### encrypt()

```python
def encrypt(
    self,
    plaintext: str,
    sender_role: str,
    recipient_role: str
) -> EncryptedMessage:
    """Encrypt message with claw-pair derived key."""
```

### decrypt()

```python
def decrypt(
    self,
    encrypted: EncryptedMessage,
    sender_role: str,
    recipient_role: str
) -> str:
    """Decrypt message with claw-pair derived key."""
```

---

## Key Derivation

Keys are derived per sender-recipient pair:

```python
def _derive_key(self, sender: str, recipient: str) -> bytes:
    """Derive encryption key for claw pair."""
    salt = f"{sender}{SALT_SEPARATOR}{recipient}".encode()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
        backend=default_backend()
    )
    return kdf.derive(self.mesh_secret.encode())
```

---

## Integration

### With MeshCoordinator

```python
# Encrypt before sending
encrypted = encryption.encrypt(
    plaintext=json.dumps(message),
    sender_role="content",
    recipient_role="ops"
)
```

### With TypeScript GatewayClient

```typescript
// TypeScript must use same algorithm
import { createCipheriv, createDecipheriv } from "node:crypto";
// AES-256-GCM with PBKDF2 key derivation
```

---

## Related Pages

- [[mesh-coordinator]] — Mesh overview
- [[mesh-gateway-client]] — TypeScript client
- [[mesh-failover]] — Failover handling
- [[mesh-relay]] — Relay server
