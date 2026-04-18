# platform-publisher

**Summary**: Publishes approved content to social platforms via approved APIs.

**Sources**: `milimo-blueprint/orchestrator/content/platform_publisher.py`

**Last updated**: 2026-04-14

**Tags**: #module #content-claw

---

## Purpose

Publishes approved content to social media platforms using approved egress endpoints.

## Location

**File**: `milimo-blueprint/orchestrator/content/platform_publisher.py`

## Key Classes

### PlatformPublisher

Handles publishing to social platforms.

```python
class PlatformPublisher:
    def __init__(
        self,
        fs: ContentFilesystemInit,
        war_room: WarRoomClient,
    ):
        self._fs = fs
        self._war_room = war_room

    def publish(self, draft: Draft, platform: str) -> PublishResult:
        """Publish draft to specified platform."""
        pass

    def schedule(self, draft: Draft, publish_time: datetime) -> None:
        """Schedule draft for future publication."""
        pass
```

## Approved Platforms

| Platform | API Endpoint |
|----------|--------------|
| Twitter/X | `api.twitter.com` |
| Facebook/Instagram | `graph.facebook.com` |
| Instagram | `api.instagram.com` |
| LinkedIn | `api.linkedin.com` |
| TikTok | `api.tiktok.com` |

## Publishing Flow

1. **Receive** approved draft from calendar
2. **Call** platform API with OAuth credentials
3. **Log** result to operational.log
4. **Move** draft to published/
5. **Send** `performance_signal` to Analytics Claw

## Egress Policy

Publishing is **outbound only**:
- Cannot read DMs or private messages
- Cannot access follower data
- See [[network-egress]] for full policy

## Error Handling

If platform unavailable:
- Retry every 15 minutes for 2 hours
- Escalate to War Room after 2 hours
- Never silently drop content

## Dependencies

- [[content-scheduler]] — Schedule source
- [[privacy-router]] — Not used for publishing

## Related Pages

- [[content-claw]] — Parent claw
- [[network-egress]] — Egress policy
- [[content-scheduler]] — Scheduling
