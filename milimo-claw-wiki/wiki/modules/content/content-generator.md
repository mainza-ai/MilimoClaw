# content-generator

**Summary**: Core content generation engine using inference.

**Sources**: `milimo-blueprint/orchestrator/content/content_generator.py`

**Last updated**: 2026-04-14

**Tags**: #module #content-claw

---

## Purpose

Generates content (social posts, copy, campaigns) using AI inference. Applies tool pipeline to every draft before surfacing.

## Location

**File**: `milimo-blueprint/orchestrator/content/content_generator.py`

## Key Classes

### ContentGenerator

Main content generation class.

```python
class ContentGenerator:
    def __init__(
        self,
        privacy_router: PrivacyRouter,
        tool_registry: ToolRegistry,
        operational_log: ContentOperationalLog,
        fs: ContentFilesystemInit,
        war_room: WarRoomClient,
    ):
        self._router = privacy_router
        self._tools = tool_registry
        self._log = operational_log
        self._fs = fs

    def generate_draft(self, brief: ProjectBrief) -> Draft:
        """Generate content draft from project brief."""
        pass

    def apply_tools(self, draft: Draft) -> Draft:
        """Apply tool pipeline to draft."""
        pass
```

## Generation Pipeline

1. **Receive brief** — From [[brief-manager]]
2. **Create prompt** — Build inference prompt from brief
3. **Generate content** — Call inference with `data_type`
4. **Apply tools** — Run evolved tool pipeline
5. **Return draft** — Draft ready for War Room

## Tool Pipeline

Tools are applied in order:

```python
def apply_tools(self, draft: Draft) -> Draft:
    for tool in self._tools.get_tools("content"):
        draft = tool.apply(draft)
    return draft
```

Evolution tools emerge over time (see [[content-claw]]).

## Privacy Routing

All inference calls use the privacy router:

```python
response = self._router.complete(
    prompt=prompt,
    data_type="content_generation",  # Required
    max_tokens=2000
)
```

## Dependencies

- [[privacy-router]] — Inference routing
- [[tool-registry]] — Evolved tools
- [[brief-manager]] — Project briefs

## Related Pages

- [[content-claw]] — Parent claw
- [[privacy-router]] — Inference routing
- [[evolution-cycle]] — Tool generation
