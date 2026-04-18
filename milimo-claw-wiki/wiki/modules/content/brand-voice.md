# brand-voice

**Summary**: Brand voice profile management and voice adaptation.

**Sources**: `milimo-blueprint/orchestrator/content/brand_voice.py`

**Last updated**: 2026-04-14

**Tags**: #module #content-claw

---

## Purpose

Manages brand voice profiles and applies client-specific voice adaptation to content drafts.

## Location

**File**: `milimo-blueprint/orchestrator/content/brand_voice.py`

## Key Classes

### BrandVoiceManager

Manages voice profiles and adaptation.

```python
class BrandVoiceManager:
    def __init__(
        self,
        privacy_router: PrivacyRouter,
        fs: ContentFilesystemInit,
    ):
        self._router = privacy_router
        self._fs = fs

    def load_voice_profile(self, client_id: str) -> VoiceProfile:
        """Load brand voice profile for client."""
        pass

    def apply_voice(self, draft: Draft, profile: VoiceProfile) -> Draft:
        """Apply brand voice to draft content."""
        pass

    def analyze_style(self, approved_posts: List[Draft]) -> StyleProfile:
        """Analyze style from approved content."""
        pass
```

## Voice Profile Storage

```
/sandbox/content/brand/
├── style-guides/      # brand voice docs
├── assets/            # approved images, logos
└── voice-profiles/    # per-client voice adapters
    └── {client_id}.json
```

## Privacy Routing

Voice adaptation routes to **Local NIM**:
- Trained on client data
- Never sent to cloud
- `data_type: "style_calibration"`

## Evolution Tools

Client voice adapter evolves at week 24+. See [[evolution-cycle]].

## Dependencies

- [[privacy-router]] — Inference routing
- [[content-generator]] — Draft source

## Related Pages

- [[content-claw]] — Parent claw
- [[privacy-router]] — Inference routing
- [[evolution-cycle]] — Tool generation
