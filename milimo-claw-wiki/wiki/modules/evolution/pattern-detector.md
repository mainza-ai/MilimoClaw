# Pattern Detector

**Summary**: Core detection engine for identifying recurring patterns in operation logs.

**Sources**:
- `milimo-blueprint/orchestrator/tool_proposal.py`

**Last updated**: 2026-04-15

**Tags**: #module #evolution #patterns

---

## Overview

Pattern Detector is the detection component of the [[evolution-cycle]]. It analyzes operation logs to find recurring behaviors suitable for tool automation.

---

## Key Functionality

### Detect Patterns

```python
patterns = pattern_detector.analyze(
    logs=operation_logs,
    min_frequency=5,
    min_length=3,
    max_length=10,
)
```

### Pattern Types Detected

| Type | Detection Method | Automation Potential |
|------|------------------|---------------------|
| Sequence | Sliding window frequency | High |
| Error retry | Error log clustering | High |
| Cross-claw | Message trace analysis | Medium |
| Data transform | Input/output comparison | High |

---

## Detection Algorithm

### 1. Sequence Mining

```python
def find_repeated_sequences(logs, min_freq):
    sequences = {}
    for window in sliding_window(logs):
        key = tuple(action.type for action in window)
        sequences[key] = sequences.get(key, 0) + 1
    return filter_by_frequency(sequences, min_freq)
```

### 2. Frequency Analysis

```python
def calculate_savings(pattern):
    frequency = pattern.occurrences_per_week
    time_per = pattern.average_duration
    return frequency * time_per
```

### 3. Feasibility Check

Filters patterns by:
- Data sensitivity (privacy class)
- Error rate history
- Automation complexity

---

## Integration

### With EvolutionCycle

```python
# Stage 2 of evolution
patterns = pattern_detector.detect(logs)
proposals = [create_proposal(p) for p in patterns if p.savings > threshold]
```

### With MetricsCollector

```python
# Uses metrics for time analysis
time_metrics = metrics_collector.get_action_durations()
pattern_detector.set_baselines(time_metrics)
```

---

## Output

Produces pattern reports at:
```
/sandbox/build/evolution/patterns/report.json
```

Report structure:
```json
{
  "patterns": [
    {
      "sequence": ["action_a", "action_b", "action_c"],
      "frequency": 25,
      "time_savings_min": 150,
      "automation_feasibility": "high"
    }
  ]
}
```

---

## Related Pages

- [[pattern-detection]] — Overview documentation
- [[evolution-cycle]] — Full pipeline
- [[tool-generation]] — Tool creation
- [[metrics-collector]] — Time metrics source
