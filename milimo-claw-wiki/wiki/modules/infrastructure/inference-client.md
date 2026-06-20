# Inference Client

**Summary**: OpenAI-compatible inference client with fallback chain, category-based model routing, and provider-agnostic model resolution.

**Sources**:
- `milimo-blueprint/orchestrator/inference_client.py`

**Last updated**: 2026-06-19

**Tags**: #module #inference #ai

---

## Overview

The inference client wraps an OpenAI-compatible API for all inference needs across all claws. It implements a fallback chain, category-based model/temperature selection, and cost tracking.

**Key design principle**: No hardcoded model names or providers. The active model is resolved dynamically from the gateway config at runtime.

---

## Model Resolution Chain

The active model is resolved through this priority chain (no hardcoded defaults):

```
1. NEMOCLAW_MODEL env var (set by bootstrapper from gateway config)
2. openclaw.json → models.providers.<any>.models[0].name/.id
3. openclaw.json → agents.defaults.model.primary
4. None (graceful — calls will use fallback chain)
```

The inference base URL resolves through:

```
1. NEMOCLAW_INFERENCE_BASE_URL env var
2. NVIDIA_API_BASE env var
3. openclaw.json → models.providers.<any>.baseUrl
4. https://integrate.api.nvidia.com/v1 (ultimate fallback)
```

The resolution happens at module import time in [[bootstrapper|claw-launcher-bootstrapper]], which reads the gateway config, exports env vars, then launches the claw process. This ensures the model always matches what the gateway is configured to serve, regardless of provider or model name.

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
- `NVIDIA_API_KEY` — API key (injected by sandbox gateway proxy in sandbox mode)
- `NVIDIA_API_BASE` — Base URL override
- `NEMOCLAW_MODEL` — Primary inference model (resolved from gateway config)
- `NEMOCLAW_INFERENCE_BASE_URL` — Proxy-routed inference endpoint (resolved from gateway config)
- `INFERENCE_FALLBACK` — Comma-separated fallback model list (optional override)

---

## Fallback Chain

Default fallback order (primary model from env/config, listed non-primary fallbacks are provider-agnostic placeholders):

1. `NEMOCLAW_MODEL` — Resolved from gateway config or env var
2. `meta/llama-3.3-70b-instruct` — Generic fallback
3. `mistralai/mixtral-8x22b-instruct-v0.1` — Generic fallback

> **Note:** The primary model slot (`NEMOCLAW_MODEL`) has no hardcoded default. If unset and unreadable from the gateway config, it is excluded from the chain entirely (`if m` filter in the chain comprehension). The listed fallbacks are generic model IDs that may or may not be available on the configured endpoint.

On failure, automatically tries next model in chain with exponential backoff (2^attempt seconds).

---

## Category-Based Routing

Different categories use different models and temperatures:

| Category | Model | Temperature |
|----------|-------|-------------|
| `source_code_generation` | NEMOCLAW_MODEL | 0.1 |
| `code_review` | NEMOCLAW_MODEL | 0.1 |
| `pr_description_generation` | NEMOCLAW_MODEL | 0.3 |
| `changelog_generation` | NEMOCLAW_MODEL | 0.7 |
| `content_draft` | NEMOCLAW_MODEL | 0.7 |
| `sentiment_analysis` | NEMOCLAW_MODEL | 0.1 |
| `general` | NEMOCLAW_MODEL | 0.5 |

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
