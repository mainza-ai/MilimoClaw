# Inference Client

**Summary**: NVIDIA NIM API client with fallback chain and category-based model routing.

**Sources**:
- `milimo-blueprint/orchestrator/inference_client.py`

**Last updated**: 2026-04-17

**Tags**: #module #inference #ai #nvidia

---

## Overview

InferenceClient wraps the NVIDIA NIM API (OpenAI-compatible) for all inference needs. Implements fallback chain and category-based model/temperature selection.

---

## Key Class

### `NvidiaInferenceClient`

```python
class NvidiaInferenceClient:
    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        fallback_chain: list[str] | None = None,
    ) -> None:
        ...
```

**Environment Variables**:
- `NVIDIA_API_KEY` — API key for NVIDIA NIM
- `NVIDIA_API_BASE` — Base URL (default: https://integrate.api.nvidia.com/v1)
- `INFERENCE_FALLBACK` — Comma-separated fallback models

---

## Fallback Chain

Default fallback order:
1. `nvidia/nemotron-4-340b-instruct`
2. `meta/llama-3.3-70b-instruct`
3. `mistralai/mixtral-8x22b-instruct-v0.1`

On failure, automatically tries next model in chain.

---

## Category-Based Routing

Different categories use different models and temperatures:

| Category | Model | Temperature |
|----------|-------|-------------|
| `source_code_generation` | nemotron-340b | 0.1 |
| `code_review` | nemotron-340b | 0.1 |
| `pr_description_generation` | nemotron-340b | 0.3 |
| `changelog_generation` | nemotron-340b | 0.7 |
| `content_draft` | nemotron-340b | 0.7 |
| `sentiment_analysis` | nemotron-340b | 0.1 |
| `general` | nemotron-340b | 0.5 |

---

## Data Classes

### `InferenceUsage`

```python
@dataclass
class InferenceUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    model_used: str = ""
    timestamp: str = ""
```

### `InferenceResponse`

```python
@dataclass
class InferenceResponse:
    content: str
    usage: InferenceUsage
    model_used: str
    attempts: int
    success: bool
    error: str | None = None
```

---

## Usage

```python
from orchestrator.inference_client import NvidiaInferenceClient

client = NvidiaInferenceClient()

# Simple completion
response = client.complete(
    prompt="Write a function to sort a list",
    data_type="source_code_generation"
)

# With explicit parameters
response = client.complete(
    prompt="Analyze this code",
    data_type="code_review",
    temperature=0.2,
    max_tokens=2000
)
```

---

## Integration

### With PrivacyRouter

```python
# PrivacyRouter routes based on data sensitivity
router = PrivacyRouter()
response = router.complete(
    prompt=sensitive_data,
    data_type="general"  # Routes to secure backend
)
```

### With ContentGenerator

```python
# Content Claw uses for content generation
response = self._inference.complete(
    prompt=content_prompt,
    data_type="content_draft",
    temperature=0.7
)
```

---

## Cost Tracking

```python
# Get usage statistics
usage = client.get_usage()
print(f"Total cost: ${usage['total_cost_usd']:.2f}")
print(f"Tokens used: {usage['total_tokens']}")
```

---

## Related Pages

- [[privacy-router]] — Inference routing
- [[content-generator]] — Content generation
- [[tool-builder]] — Tool generation
- [[cost-monitor]] — Cost tracking
