# Pattern Detection

**Summary**: Identifying recurring patterns in claw behavior for tool generation.

**Sources**:
- `raw/AGENTS.md`
- `milimo-blueprint/orchestrator/tool_proposal.py`

**Last updated**: 2026-04-15

**Tags**: #evolution #patterns #detection

---

## Overview

Pattern detection is Stage 2 of the [[evolution-cycle]]. It analyzes operation logs to find recurring behaviors that could be automated with new tools.

---

## Detection Process

### Input

- 7 days of operation logs from all claws
- Error patterns and retry attempts
- Manual interventions via War Room
- Performance metrics from [[metrics-collector]]

### Analysis

The system looks for:

| Pattern Type | Example | Automation Potential |
|--------------|---------|---------------------|
| Repetitive sequences | Same 5 actions every Monday report | High |
| Error retry loops | 3+ retries on API call | High |
| Manual approvals | Same approval type weekly | Medium |
| Cross-claw handoffs | Content → Ops → Analytics flow | Medium |
| Data transformations | CSV → JSON → API format | High |

---

## Pattern Categories

### 1. Data Transformation Patterns

Repeated format conversions suggest tool generation.

**Example**:
```
Detected: Content Claw converting YouTube data 50x/week
Pattern: youtube_csv → internal_json → platform_format
Proposal: youtube-format-converter tool
```

### 2. API Interaction Patterns

Repeated API call sequences.

**Example**:
```
Detected: Finance Claw checking payment status 100x/week
Pattern: stripe.customer.retrieve → invoice.list → balance.get
Proposal: payment-status-check tool
```

### 3. Approval Patterns

Repeated approval types.

**Example**:
```
Detected: 20 approvals/week for "expense categorization"
Pattern: Ops sends expense → Finance categorizes → Approval
Proposal: auto-categorize-small-expenses tool (with threshold)
```

### 4. Cross-Claw Coordination Patterns

Repeated message sequences.

**Example**:
```
Detected: Project kickoff flow executed 10x
Pattern: brief-received → project-created → analytics-alert
Proposal: project-kickoff-automation tool
```

---

## Detection Algorithm

### Step 1: Sequence Mining

```python
def find_repeated_sequences(logs, min_frequency=5, min_length=3):
    """Find action sequences that repeat."""
    sequences = {}
    for window in sliding_window(logs, min_length):
        key = tuple(action.type for action in window)
        sequences[key] = sequences.get(key, 0) + 1

    return {k: v for k, v in sequences.items() if v >= min_frequency}
```

### Step 2: Frequency Analysis

Calculate frequency and time savings:

```
frequency = occurrences_per_week
time_per_occurrence = average_duration
potential_savings = frequency * time_per_occurrence
```

### Step 3: Feasibility Check

Filter patterns by:
- Data sensitivity (privacy routing)
- Error rate of manual execution
- Complexity of automation

---

## Output

Pattern detection produces:

1. **Pattern report**: List of detected patterns with metrics
2. **Priority ranking**: Sorted by time savings potential
3. **Tool proposals**: Draft specifications for top patterns

Output location: `/sandbox/build/evolution/patterns/`

---

## Integration with Tool Generation

See [[tool-generation]] for the full pipeline.

Pattern detection feeds into:
- [[tool-generation#proposal-stage]] — Creates tool proposals
- [[tool-generation#validation-stage]] — Validates feasibility
- [[tool-generation#implementation-stage]] — Generates code

---

## Configuration

See [[evolution-config]] for detection parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min_pattern_frequency` | 5 | Minimum occurrences to consider |
| `min_pattern_length` | 3 | Minimum sequence length |
| `max_pattern_length` | 10 | Maximum sequence length |
| `time_savings_threshold` | 30min/week | Minimum savings to propose |

---

## Related Pages

- [[evolution-cycle]] — Full 5-stage pipeline
- [[tool-generation]] — Tool creation process
- [[metrics-collector]] — Performance data source
- [[operation-log]] — Operation log structure
