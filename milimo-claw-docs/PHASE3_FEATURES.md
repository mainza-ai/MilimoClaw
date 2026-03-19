# Phase 3 Features — Production Hardening

> Detailed documentation for features introduced in Phase 3.

---

## Overview

Phase 3 introduces production-hardening features that enable Milimo Claw to scale from development to real-world deployment:

1. **OpenShell Gateway Integration** — True inter-sandbox communication
2. **Tool Code Generation** — LLM-based tool generation
3. **Tool Security Validation** — AST-based code analysis
4. **Tool Sandbox** — Isolated execution environment
5. **Rate Limiting** — Tier-based auto-approval limits

---

## OpenShell Gateway Integration

### Architecture

The Gateway Adapter provides a unified interface for inter-sandbox communication:

```
┌─────────────────────────────────────────────────────────────────┐
│ Mesh Coordinator                                                │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Gateway Adapter (Abstract)                               │   │
│  │                                                          │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐   │   │
│  │  │ Unix Socket │ │ WebSocket   │ │ File-based      │   │   │
│  │  │ Gateway     │ │ Gateway     │ │ Gateway         │   │   │
│  │  │ (single)    │ │ (multi)     │ │ (fallback)      │   │   │
│  │  └─────────────┘ └─────────────┘ └─────────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Transport Modes

| Mode | Endpoint Format | Use Case |
|------|-----------------|----------|
| Unix Socket | `unix:///path/to/socket` | Single machine, same host |
| WebSocket | `tcp://host:port` or `ws://host:port` | Distributed across machines |
| File-based | Empty or `file://` | Development, testing, fallback |

### Configuration

```yaml
# mesh_config.yaml
mesh_version: "0.1.0"
gateway_endpoint: "unix:///var/run/openshell/gateway.sock"
mesh_secret: "squad-secret-abc123"
timeout_ms: 5000

message_matrix:
  content:
    ops: [deliverable]
    # ... (see mesh_config.yaml)
```

### Python Usage

```python
from orchestrator.gateway_adapter import create_gateway, GatewayConfig
from orchestrator.mesh import MeshCoordinator

# Create mesh with gateway
mesh = MeshCoordinator.from_config_file(
    "mesh_config.yaml",
    squad_id="my-squad",
)

# Connect to gateway
mesh.connect_gateway(role="content")

# Send message
from orchestrator.contracts import ClawMessage

msg = ClawMessage(
    sender_role="content",
    recipient_role="ops",
    message_type="deliverable",
    payload={"draft": "..."},
    squad_id="my-squad",
)

result = mesh.send_message(msg)
```

---

## Tool Code Generation

### Tool Types

| Type | Description | Output Schema |
|------|-------------|---------------|
| `classifier` | Categorizes inputs into classes | `{predicted_class, confidence, reasoning}` |
| `predictor` | Predicts continuous values | `{predicted_value, confidence_interval, confidence}` |
| `optimizer` | Suggests optimal parameters | `{recommended_params, expected_improvement, confidence}` |
| `detector` | Identifies anomalies/risks | `{detected, severity, confidence, indicators}` |
| `generator` | Produces content variants | `{variants, scores, selected_index}` |

### Tool Specification Schema

Tools are defined using JSON Schema:

```json
{
  "name": "tone_classifier",
  "version": "0.1.0",
  "tool_type": "classifier",
  "description": "Classifies content tone",
  "inputs": {
    "schema": {
      "type": "object",
      "properties": {
        "text": {"type": "string"}
      },
      "required": ["text"]
    }
  },
  "outputs": {
    "schema": {
      "type": "object",
      "properties": {
        "predicted_class": {"type": "string"},
        "confidence": {"type": "number"},
        "reasoning": {"type": "string"}
      }
    }
  },
  "permissions": {
    "filesystem": {"read": [], "write": []},
    "network": {"egress": []}
  },
  "metadata": {
    "created_at": "2026-03-18T00:00:00Z",
    "claw_role": "content",
    "evolution_cycle": "cycle-001"
  }
}
```

### Prompt Templates

Prompt templates are located in `milimo-blueprint/prompts/tool-generation/`:

| Template | Tool Type |
|----------|-----------|
| `classifier.txt` | Classification tools |
| `predictor.txt` | Prediction tools |
| `optimizer.txt` | Optimization tools |
| `detector.txt` | Anomaly/risk detection |
| `generator.txt` | Content generation |

### Generation Workflow

```python
from tool_generator import ToolGenerator, ToolSpec

generator = ToolGenerator(template_dir="prompts/tool-generation")

spec = ToolSpec(
    name="deadline_predictor",
    tool_type="predictor",
    description="Predicts deadline risk",
    input_schema={...},
    output_schema={...},
    pattern_description="Recurring deadline misses observed",
    frequency=45,
    test_cases=[
        {"input": {"days_remaining": 3}, "expected_output": {"risk": "high"}}
    ],
)

result = generator.generate(spec)

if result.success:
    print(result.code)  # Generated Python code
    print(result.validation_passed)  # True if security checks pass
```

---

## Tool Security Validation

### Validation Rules

The validator checks for:

| Check | Severity | Description |
|-------|----------|-------------|
| Forbidden imports | CRITICAL | `subprocess`, `socket`, `urllib`, `requests`, etc. |
| Dangerous builtins | CRITICAL | `eval`, `exec`, `compile`, `__import__` |
| OS functions | CRITICAL | `os.system`, `os.popen`, `os.spawn` |
| File write | ERROR | Write operations not allowed |
| Dynamic imports | WARNING | `__import__` usage |
| Missing type hints | WARNING | Function should have type annotations |
| Missing docstrings | WARNING | Function should be documented |
| High complexity | WARNING | Cyclomatic complexity threshold |

### Validation Example

```python
from tool_validator import ToolValidator, PolicyConstraints

validator = ToolValidator(PolicyConstraints(
    allow_network=False,
    allow_filesystem_write=False,
    max_code_length=10000,
    max_complexity=20,
))

code = """
def run(input_data):
    # Generated tool code
    return {"result": "ok"}
"""

result = validator.validate(code)

print(result.passed)  # True if valid
print(result.score)   # 0-100 security score
print(result.issues)  # List of ValidationIssue
print(result.safe_to_deploy)  # True if no errors/critical issues
```

---

## Tool Sandbox

### Execution Environment

The sandbox provides:

- **Process isolation** — Code runs in subprocess, not main process
- **Memory limits** — Configurable memory ceiling (default: 200MB)
- **Time limits** — Execution timeout (default: 5 seconds)
- **Import blocking** — Forbidden modules blocked at import time
- **Output limits** — Maximum output size (default: 1MB)

### Usage

```python
from tool_sandbox import ToolSandbox, SandboxConfig

sandbox = ToolSandbox(SandboxConfig(
    max_execution_time_ms=5000,
    max_memory_mb=200,
    enable_network=False,
))

# Test generated code
test_cases = [
    {"input": {"text": "urgent deadline"}, "expected_output": {"tone": "urgent"}},
    {"input": {"text": "friendly reminder"}, "expected_output": {"tone": "normal"}},
]

result = sandbox.test(generated_code, test_cases)

print(result.passed)  # True if all tests pass
print(result.passed_tests)  # Number of passed tests
print(result.failed_tests)  # Number of failed tests

for case in result.results:
    print(f"{case['name']}: {'PASS' if case['passed'] else 'FAIL'}")
```

### Benchmarking

```python
# Run performance benchmarks
benchmark = sandbox.benchmark(
    code=generated_code,
    input_data={"text": "sample"},
    iterations=100,
)

print(f"Min: {benchmark['min']:.2f}ms")
print(f"Max: {benchmark['max']:.2f}ms")
print(f"Avg: {benchmark['avg']:.2f}ms")
print(f"P95: {benchmark['p95']:.2f}ms")
print(f"P99: {benchmark['p99']:.2f}ms")
```

---

## Rate Limiting

### Tier Configuration

```yaml
# rate-limits.yaml
tiers:
  free:
    auto_approvals:
      daily_limit: 10
      burst_limit: 3
      burst_window_hours: 1

  pro:
    auto_approvals:
      daily_limit: null  # Unlimited
      burst_limit: null
```

### Token Bucket Algorithm

Rate limiting uses a token bucket:

- **Daily bucket** — Refills at midnight UTC
- **Burst bucket** — Refills after burst window (1 hour)
- **Pro tier** — Unlimited tokens

### TypeScript Usage

```typescript
import { RateLimiter, Tier } from "./rate-limiter";

const limiter = new RateLimiter(Tier.FREE);

// Check status
const status = limiter.getStatus();
console.log(`Remaining: ${status.dailyRemaining}/${status.dailyLimit}`);

// Try to consume a token
const result = limiter.tryConsume();
if (result.allowed) {
  // Proceed with auto-approval
} else {
  // Require manual approval
  console.log(`Rate limited: ${result.reason}`);
  console.log(`Resets at: ${result.resetAt}`);
}
```

### Integration with Approval Engine

```typescript
import { ApprovalEngine } from "./approval";

// Pass tier during construction
const engine = new ApprovalEngine("my-squad", "free");

// Get rate limit status for display
const limits = engine.getRateLimitStatus();

// Auto-process with rate limiting built-in
engine.autoProcessEligible();
```

### Metrics

```typescript
import { RateLimitMetricsTracker } from "./rate-limiter";

const tracker = new RateLimitMetricsTracker(limiter);
tracker.start(60000);  // Record every minute

// Get metrics
const metrics = limiter.getMetrics();
console.log(`Total requests: ${metrics.totalRequests}`);
console.log(`Allowed: ${metrics.allowedRequests}`);
console.log(`Denied: ${metrics.deniedRequests}`);

// Get utilization percentage
console.log(`Utilization: ${tracker.getUtilization()}%`);
```

---

## Integration Tests

### Test Harness

The integration test harness provides utilities for testing the TypeScript ↔ Python boundary:

```javascript
const { IntegrationTestHarness } = require("./harness");

describe("My integration test", async () => {
  let harness;

  beforeEach(async () => {
    harness = new IntegrationTestHarness();
    await harness.setup();
  });

  afterEach(async () => {
    await harness.teardown();
  });

  it("should run Python code", async () => {
    const result = await harness.runPython("-c", "print('hello')");
    console.log(result.stdout);  // "hello"
  });
});
```

### Running Tests

```bash
# All integration tests
node --test test/integration/*.test.js

# Specific test file
node --test test/integration/mesh-coordinator.test.js

# Via npm script
npm run test:integration
```

---

## Documentation Index

| Document | Description |
|----------|-------------|
| [Technical: OpenShell IPC](../docs/technical/openshell-ipc.md) | Gateway protocol specification |
| [Implementation Plan](../MILIMO_CLAW_IMPLEMENTATION_PLAN.md) | Phase 3 implementation details |
| [Status Report](../PHASE3_STATUS_REPORT.md) | Completion status |

---

## Author

**Mainza Kangombe** — [LinkedIn](https://www.linkedin.com/in/mainza-kangombe-6214295)
