# Timing Optimizer

**Summary**: Evolved tool that optimizes content posting times based on engagement patterns.

**Sources**:
- `milimo-blueprint/orchestrator/content/content_generator.py`
- `milimo-blueprint/orchestrator/tool_proposal.py`

**Last updated**: 2026-04-15

**Tags**: #module #content #tools #evolution

---

## Overview

Timing Optimizer is an evolved tool that analyzes engagement data to determine optimal posting times. It's generated through the [[evolution-cycle]] when timing patterns are detected.

---

## Tool Type

This is an **evolved tool** — not a static module. Generated when:

1. [[pattern-detector]] finds timing-related patterns
2. Engagement varies significantly by time of day/week
3. [[tool-generation]] creates optimization tool

---

## Functionality

### Analyze Engagement Patterns

```python
def analyze_timing_patterns(self, posts: list) -> dict:
    """Analyze when posts perform best.

    Returns:
        optimal_times: Dict of platform → best posting times
        peak_windows: Dict of day → engagement peaks
    """
```

### Suggest Optimal Times

```python
def suggest_posting_time(self, platform: str, content_type: str) -> datetime:
    """Suggest optimal posting time.

    Factors:
    - Historical engagement by hour
    - Platform-specific patterns
    - Content type performance
    """
```

---

## Integration

### With ContentGenerator

```python
# In content_generator.py
elif tool_name == "timing_optimizer":
    timing = self._tools.get("timing_optimizer")
    if timing:
        optimal_time = timing.suggest_posting_time(platform, content_type)
        post["scheduled_time"] = optimal_time
```

### With ContentScheduler

```python
# Timing optimizer outputs feed into scheduler
timing_suggestions = timing_optimizer.analyze_timing_patterns(posts)
scheduler.update_optimal_times(timing_suggestions)
```

---

## Generation Trigger

Pattern detector identifies timing patterns:

```
Detected: Post engagement varies 3x by posting time
Pattern: Posts at 9am outperform 2pm by 200%
Proposal: timing_optimizer tool
```

---

## Storage

| Path | Purpose |
|------|---------|
| `~/.milimo/tools/<squad>/content/tools/timing-optimizer/` | Tool code |
| `/sandbox/content/analytics/timing-patterns.json` | Engagement data |

---

## Related Pages

- [[content-generator]] — Uses timing optimizer
- [[content-scheduler]] — Receives timing suggestions
- [[tool-generation]] — Creates this tool
- [[pattern-detector]] — Detects timing patterns
- [[evolution-cycle]] — Evolution pipeline
