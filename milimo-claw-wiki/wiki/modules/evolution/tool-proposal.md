# Tool Proposal

**Summary**: Schema and validation for evolved tool proposals.

**Sources**:
- `milimo-blueprint/orchestrator/tool_proposal.py`

**Last updated**: 2026-04-17

**Tags**: #module #evolution #proposal

---

## Overview

ToolProposal defines the schema for new tool proposals, validates permissions against sandbox policy, and generates proposals from detected patterns.

---

## Key Class

### `ToolProposal`

```python
@dataclass
class ToolProposal:
    tool_name: str
    tool_type: str  # classifier | optimizer | predictor | generator_variant | anomaly_detector
    trigger_pattern: EvolutionPattern
    metric_target: str
    data_sources_required: list[str] = field(default_factory=list)
    estimated_improvement: float = 0.0
    status: str = "proposed"
    proposal_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    claw_role: str = ""
    squad_id: str = ""
    created_at: str = field(default_factory=...)
    rejection_reason: str = ""
```

---

## Tool Types

| Type | Purpose | Example |
|------|---------|---------|
| `classifier` | Categorize inputs | Content type classifier |
| `optimizer` | Improve performance | Timing optimizer |
| `predictor` | Predict outcomes | Payment risk predictor |
| `generator_variant` | Content generation | Email template variant |
| `anomaly_detector` | Detect anomalies | Cost spike detector |

---

## Proposal States

```
proposed → approved → building → testing → deployed
    ↓          ↓          ↓
 rejected   rejected   failed
```

---

## Key Functions

### `generate_proposal()`

```python
def generate_proposal(
    pattern: EvolutionPattern,
    claw_role: str,
) -> ToolProposal:
    """Generate proposal from detected pattern."""
```

### `validate_permissions()`

```python
def validate_permissions(
    proposal: ToolProposal,
    sandbox_policy: dict[str, Any],
) -> bool:
    """Validate proposal stays within policy boundaries."""
```

---

## Integration

### With PatternDetector

```python
# Pattern detected
patterns = pattern_detector.detect(logs)
for pattern in patterns:
    proposal = generate_proposal(pattern, claw_role)
```

### With EvolutionCycle

```python
# Stage 1: Generate proposals
proposals = [
    generate_proposal(p, claw_role)
    for p in detected_patterns
]

# Stage 2: Validate permissions
valid_proposals = [
    p for p in proposals
    if validate_permissions(p, sandbox_policy)
]
```

---

## Storage

| Path | Purpose |
|------|---------|
| `/sandbox/build/evolution/proposals/{id}.yaml` | Proposal files |
| `/sandbox/build/evolution/proposals/rejected/` | Rejected proposals |

---

## Related Pages

- [[pattern-detector]] — Pattern detection
- [[tool-builder]] — Building tools
- [[tool-validator]] — Validation
- [[evolution-cycle]] — Full pipeline
