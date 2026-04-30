# Privacy Router

**Summary**: Routes inference calls based on data sensitivity classification.

**Sources**:
- `milimo-blueprint/orchestrator/privacy_router.py`
- `raw/AGENTS.md`

**Last updated**: 2026-04-29

**Tags**: #architecture #privacy #inference #routing

---

> **NemoClaw Compliance Notice:** This page describes MilimoClaw's application-level privacy routing layer. The underlying inference transport is handled entirely by OpenShell. The sandbox never sees real API keys; credentials are substituted at egress by the OpenShell L7 proxy.

## Overview

The Privacy Router intercepts **every inference call** in MilimoClaw. It determines whether the data is sensitive and routes accordingly — sensitive data stays local, non-sensitive goes to cloud APIs.

> **Important:** In the NemoClaw sandbox, the agent talks to `https://inference.local/v1` inside the sandbox. The OpenShell gateway intercepts this on the host and forwards to the actual provider. The sandbox **never** sees the real API key — OpenShell's L7 proxy substitutes credentials at egress. Local inference (Ollama/vLLM) uses provider-specific tokens, **not** `OPENAI_API_KEY`. The `NEMOCLAW_MODEL` env var determines which model is used; switching models uses `openshell inference set --provider nvidia-nim --model <model>` (or the alias `nemoclaw <name> inference-switch`). Experimental providers require `NEMOCLAW_EXPERIMENTAL=1`. Provider trust tiers (official, community, experimental) govern which providers are available without the experimental flag.

## Purpose

- **Protect sensitive data** — Never send to cloud APIs
- **Optimize cost** — Use cheaper cloud APIs when possible
- **Enable auditing** — Log all inference calls with data types
- **Support compliance** — Data residency and privacy requirements

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                      PRIVACY ROUTER                            │
│                                                                │
│  Inference Request                                             │
│       │                                                        │
│       ▼                                                        │
│  ┌──────────────┐                                             │
│  │  Sensitivity │                                             │
│  │  Classifier  │                                             │
│  └──────┬───────┘                                             │
│         │                                                      │
│         ▼                                                      │
│  ┌──────────────┐      ┌──────────────┐                       │
│  │  Sensitive?  │──No──►│  Cloud API   │                       │
│  └──────┬───────┘      │ (NVIDIA NIM) │                       │
│         │              └──────────────┘                       │
│        Yes                                                    │
│         │                                                      │
│         ▼                                                      │
│  ┌──────────────┐                                             │
│ │ Local NIM │ │
│ │ (on-device) │ │
│  └──────────────┘                                             │
└────────────────────────────────────────────────────────────────┘
```

## Data Type Classification

### Required Pattern

Every inference call must include `data_type`:

```python
response = inference_client.complete(
    prompt=prompt,
    data_type="scope_cost_estimation",  # ALWAYS INCLUDE
    max_tokens=800
)
```

### Sensitive Data Types

By claw:

| Claw | Sensitive Data Types |
|------|---------------------|
| Content | Internal ideation, draft iterations, voice adapter calibration |
| Ops | Contract review, internal summaries, scope analysis |
| Analytics | Performance synthesis, predictive models, opportunity scoring |
| Finance | **ALL financial data** — locked, no exceptions in production |
| Build | Source code, API keys, architecture decisions, code review |
| Assistant | Conversation context, user preferences, dispatch routing logic |

### Routing Rules

```python
SENSITIVE_TYPES = {
    # Finance - all financial data
    "pricing_query",
    "invoice_generation",
    "payment_status",
    "revenue_analysis",

    # Build - code and secrets
    "code_generation",
    "code_review",
    "api_key_handling",

    # Content - internal creative
    "draft_iteration",
    "voice_calibration",

    # Ops - contracts
    "contract_review",
    "scope_analysis",
}

def route_inference(data_type: str) -> str:
    if data_type in SENSITIVE_TYPES:
        return "local_nim"
    else:
        return "cloud_api"
```

## Development Mode

During development, **all inference routes to cloud** (NVIDIA NIM API).

The `data_type` field is still required and logged, enabling future NIM routing without changing call sites.

```python
# Development routing
def route_inference_dev(data_type: str) -> str:
    # Log the data type for future routing
    logger.debug(f"Inference call: data_type={data_type}")
    return "cloud_api"  # Always cloud in dev
```

## Production Routing

In production, the privacy router enforces local NIM for sensitive data:

```python
def route_inference_prod(data_type: str) -> str:
    if data_type in SENSITIVE_TYPES:
        logger.info(f"Routing sensitive data to local NIM: {data_type}")
        return "local_nim"
    return "cloud_api"
```

## Configuration

### Environment Variables

```bash
# Model selection (determines which model the sandbox proxy uses)
NEMOCLAW_MODEL=nvidia/nemotron-3-super-120b-a12b

# Preferred API protocol (new in v0.0.29)
NEMOCLAW_PREFERRED_API=openai-responses

# Cross-provider switching (requires sandbox recreation)
NEMOCLAW_MODEL_OVERRIDE=openai/gpt-5.4
NEMOCLAW_INFERENCE_API_OVERRIDE=openai-completions

# Experimental providers (required to use community/experimental providers)
NEMOCLAW_EXPERIMENTAL=1

# Inference endpoint inside the sandbox (agent-facing, not the real provider)
# The agent calls https://inference.local/v1
# OpenShell gateway intercepts and routes to the real provider

# Real API keys are NEVER in the sandbox environment.
# They are stored in the OpenShell gateway and substituted at egress.
# For local inference (Ollama/vLLM), provider-specific tokens are used — NOT OPENAI_API_KEY.
```

### Switching Models

**Same provider** — no sandbox restart needed:

```bash
openshell inference set --provider nvidia-nim --model nvidia/nemotron-3-super-120b-a12b
# Or via nemoclaw alias:
nemoclaw <name> inference-switch --model nvidia/nemotron-3-super-120b-a12b
```

**Cross-provider switch** (e.g., NVIDIA → OpenAI) — requires sandbox recreation:

```bash
NEMOCLAW_MODEL_OVERRIDE=openai/gpt-5.4 \
NEMOCLAW_INFERENCE_API_OVERRIDE=openai-completions \
nemoclaw onboard --resume --recreate-sandbox
```

Valid `NEMOCLAW_INFERENCE_API_OVERRIDE` values: `openai-completions`, `anthropic-messages`.

### Provider Trust Tiers

| Tier | Providers | Behavior |
|------|-----------|----------|
| **Tested** | NVIDIA Endpoints, OpenAI, Anthropic, Google Gemini | Fully supported, tested during onboarding |
| **Compatible** | Other OpenAI-compatible, Other Anthropic-compatible | User-supplied base URL and model |
| **Local** | Ollama, NVIDIA NIM, vLLM | Self-hosted; NIM and vLLM require `NEMOCLAW_EXPERIMENTAL=1` |

### Privacy Policy File

Location: `milimo-blueprint/privacy_policy.yaml`

```yaml
version: 1

sensitive_types:
  finance:
    - pricing_query
    - invoice_generation
    - payment_status
    - revenue_analysis
  build:
    - code_generation
    - code_review
    - api_key_handling
  content:
    - draft_iteration
    - voice_calibration
  ops:
    - contract_review
    - scope_analysis

routing:
  sensitive: local_nim
  non_sensitive: cloud_api

  fallback:
  - cloud_api # Fallback if local NIM unavailable
```

## Auditing

### Inference Log

Every inference call is logged:

```json
{
    "timestamp": "2026-04-14T12:00:00Z",
    "claw": "finance",
    "data_type": "pricing_query",
    "route": "local_nim",
    "tokens_used": 450,
    "latency_ms": 120
}
```

### Compliance Reports

Weekly reports include:
- Total inference calls by data type
- Sensitive data routing verification
- Fallback usage statistics
- Token usage by route

## Error Handling

### Local NIM Unavailable

```python
def handle_nim_unavailable(prompt, data_type):
    """Fallback when local NIM is down."""
    if data_type in SENSITIVE_TYPES:
        # Block rather than send to cloud
        raise PrivacyError(f"Cannot route sensitive data to cloud: {data_type}")
    else:
        # Use cloud as fallback
        return cloud_api.complete(prompt)
```

### Cost Guard

Daily cloud token budget with fallback. OpenShell provides inference cost controls at the gateway level; the privacy router's cost guard is an application-level complement:

```python
DAILY_TOKEN_BUDGET = 50000
FALLBACK_STRATEGY = "lighter_prompt" # Reduce tokens by 50%

def check_budget():
if daily_tokens_used > DAILY_TOKEN_BUDGET * 0.8:
alert("Approaching token budget limit")
if daily_tokens_used > DAILY_TOKEN_BUDGET:
return FALLBACK_STRATEGY
return "normal"
```

## Related Pages

- [[sandbox-isolation]] — Overall isolation model
- [[workspace-files]] — Workspace persistence and rebuild behavior
- [[content-claw]] — Content Claw sensitive types
- [[finance-claw]] — Finance Claw (all sensitive)
- [[build-claw]] — Build Claw sensitive types
- [[evolution-cycle]] — Evolution inference routing
- [[assistant-lucy]] — Assistant Claw sensitive types
