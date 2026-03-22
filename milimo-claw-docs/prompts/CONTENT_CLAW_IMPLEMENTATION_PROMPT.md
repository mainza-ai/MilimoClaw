# MILIMO CLAW — CONTENT CLAW IMPLEMENTATION PROMPT
# ─────────────────────────────────────────────────────────────────────────────
# Attach this prompt alongside:
#   1. CONTENT_CLAW_IMPLEMENTATION_VS_SPEC.md  (the gap analysis)
#   2. MILIMO_CLAW_CONTENT_CLAW_SPEC.md        (the ground truth spec)
#   3. content-claw.yaml                        (role blueprint)
#   4. content-sandbox.yaml                     (sandbox policy)
# Work through phases in strict order. Do not skip ahead.
# ─────────────────────────────────────────────────────────────────────────────

You are an expert TypeScript and Python engineer implementing the core
autonomous functionality of the Content Claw inside Milimo Claw — a
multi-agent autonomous hustle platform built as a plugin on NVIDIA NemoClaw.

The gap analysis document is attached. The spec document is the ground
truth — if code deviates from the spec, the code is wrong.

The Content Claw is approximately 40% complete. The infrastructure is solid:
evolution cycle pipeline, tool registry, privacy router, network policy, and
inter-claw message contracts all exist. What is missing is the core content
business logic — draft generation, publishing, brief management, performance
tracking, and the brand voice system.

Your job is to build exactly what is missing. Nothing more.

---

## CONTEXT — WHAT ALREADY EXISTS (DO NOT REWRITE)

**Infrastructure that works — leave it alone:**
  - Evolution cycle 5-stage pipeline (evolution_cycle.py)
  - Tool registry with provenance signing (tool_registry.py)
  - Privacy router with locked routes (privacy_router.py)
  - Network egress policy enforcement (content-sandbox.yaml)
  - Inter-claw message contract validation (contracts.py, mesh.py)
  - War Room approval engine (warroom/approval.ts)
  - Solo War Room queue (solo_warroom.py — queue_action() exists)
  - Operational log (running at ~/.milimo/logs/{squad_id}/content/)

**What exists but is incomplete:**
  - contracts.py — has brief type but missing 5 message types
  - content-sandbox.yaml — missing graph.facebook.com, trends.google.com,
    api.buzzsumo.com from egress allowlist
  - privacy_router.py — analytics synthesis and voice adapter routes
    are implicit, need explicit definitions
  - solo-founder.yaml — approval modes for content_calendar_update,
    ab_test_variant, trend_reactive_post not configured
  - Evolution thresholds — missing rejected_drafts_min and
    performance_data_weeks_min checks

**Plugin structure:**
  - TypeScript plugin:      milimo/src/
  - Python orchestrator:    milimo-blueprint/orchestrator/
  - Role blueprints:        milimo-blueprint/roles/
  - Sandbox policies:       milimo-blueprint/policies/
  - Operator config:        ~/.milimo/config.json

**Operator:** Mainza Kangombe — senior systems architect, experienced
Python 3.11+ and TypeScript engineer. Production-quality code only.
No placeholder comments. No stubs. No TODOs.

**Standards (non-negotiable):**
  - TypeScript: strict mode, full type annotations, no any
  - Python: 3.11+, full type hints, docstrings, pathlib.Path only
  - YAML: PyYAML safe_load only — never yaml.load()
  - Shell commands: child_process.spawn with array args only
  - Privacy router: every inference call must be routed — never call
    Nemotron directly. Always go through privacy_router.route_inference()
  - Logging: every autonomous action logged to operational.log with
    ISO timestamp, action type, and outcome
  - Tests: pytest for Python, Jest for TypeScript
  - Error handling: never silently drop content — log and escalate
    to War Room on unrecoverable errors

---

## PHASE 1 — FILESYSTEM AND INFRASTRUCTURE FOUNDATIONS
## Must be complete before any content generation can work.

---

### TASK 1.1 — Create Full Filesystem Structure

**File:** `milimo-blueprint/orchestrator/content/content_init.py`

The spec defines a precise filesystem layout under /sandbox/content/.
Nothing in the current implementation creates this structure.

Implement `ContentFilesystemInit` class:

```python
class ContentFilesystemInit:
    """
    Creates and validates the full /sandbox/content/ filesystem structure.
    Called during onboarding and on every claw startup to ensure
    required directories and files exist.
    """

    BASE = Path("/sandbox/content")

    REQUIRED_DIRS = [
        "brand/style-guides",
        "brand/assets",
        "brand/voice-profiles",
        "drafts/pending",
        "drafts/approved",
        "drafts/rejected",
        "drafts/published",
        "briefs/active",
        "briefs/completed",
        "calendar/scheduled",
        "calendar/published",
        "intelligence/analytics-feed",
        "tools/style-descriptor",
        "tools/tone-classifier",
        "tools/approval-predictor",
        "tools/timing-optimizer",
        "tools/ab-variant-engine",
        "tools/platform-calibrator",
        "tools/client-voice-adapter",
        "tools/trend-injector",
        "logs",
    ]

    REQUIRED_LOG_FILES = [
        "logs/operational.log",
        "logs/approvals.log",
        "logs/performance.log",
    ]

    def initialize(self) -> InitResult: ...
    # Creates all directories and log files if they don't exist
    # Never overwrites existing files
    # Returns InitResult with created, already_existed, failed counts

    def validate(self) -> ValidationResult: ...
    # Checks all required paths exist
    # Returns list of missing paths
    # Does not create anything — pure validation

    def get_draft_path(
        self,
        status: Literal["pending", "approved", "rejected", "published"],
        draft_id: str
    ) -> Path: ...

    def get_brief_path(
        self,
        status: Literal["active", "completed"],
        brief_id: str
    ) -> Path: ...
```

Also implement `ContentOperationalLog` class:

```python
@dataclass
class LogEntry:
    timestamp: str          # ISO 8601
    action_type: str        # draft_generated, draft_queued, published, etc.
    entity_id: str          # draft_id, brief_id, post_id
    platform: str | None
    client_id: str | None
    outcome: str            # success, failed, queued, rejected
    details: dict           # action-specific context

class ContentOperationalLog:
    """Append-only structured log for all Content Claw actions."""

    def __init__(self, log_path: Path): ...

    def append(self, entry: LogEntry) -> None: ...
    # Writes JSON line to operational.log
    # Thread-safe — uses file locking

    def read_recent(
        self,
        days: int = 7,
        action_type: str | None = None
    ) -> list[LogEntry]: ...

    def count_by_type(
        self,
        action_type: str,
        days: int = 7
    ) -> int: ...
    # Used by evolution cycle threshold checks
```

Write pytest tests covering: directory creation, idempotent re-run
(no errors on second call), validation pass/fail, log append and read,
thread-safe concurrent writes.

---

### TASK 1.2 — Fix Missing Egress Endpoints

**File:** `milimo-blueprint/policies/content-sandbox.yaml`

Add the three missing endpoints to the network_policies section,
following the exact same structure as existing entries:

  - graph.facebook.com (publishing — write access, ports 443)
  - trends.google.com (read-only — GET only, port 443)
  - api.buzzsumo.com (read-only — GET only, port 443)

Also add api.buffer.com as optional (comment it as optional — same
pattern as api.buffer.com comment in solo-founder.yaml).

Print the complete updated network_policies section of the file.
Do not print the entire file — just the network_policies block.

---

### TASK 1.3 — Fix Explicit Inference Routing Rules

**File:** `milimo-blueprint/roles/content-claw.yaml`

The gap analysis flags three implicit routes that must be made explicit.
Add these entries to the inference_routing section:

  - analytics_report_synthesis → local_nim
    (reason: operational data is proprietary)
  - voice_adapter_calibration → local_nim
    (reason: trained on client data — never cloud)
  - ab_variant_generation → cloud
    (reason: final client-facing variants — quality matters)

Print the complete updated inference_routing section only.

---

### TASK 1.4 — Add Missing Approval Modes

**File:** `milimo-blueprint/templates/solo-founder.yaml`

Add the three missing approval mode entries to the content section
of operator_policy.approval_modes:

  - content_calendar_update: AUTO
  - ab_test_variant: REVIEW
  - trend_reactive_post: REVIEW

Print only the updated content: block within approval_modes.

---

### TASK 1.5 — Fix Evolution Thresholds

**File:** `milimo-blueprint/orchestrator/solo_evolution.py`

Add the two missing minimum threshold checks before the Content Claw's
evolution cycle is allowed to run:

  - rejected_drafts_min: 3
    Read count from performance.log entries where outcome == "rejected"
  - performance_data_weeks_min: 1
    Check if performance.log has any entries older than 7 days

These join the existing approved posts threshold check at line 167.
If any threshold fails: log "evolution skipped — insufficient {data_type}
data (have {count}, need {minimum})" and return without running the cycle.

Write pytest tests for: all thresholds met (cycle runs), each threshold
failing individually (cycle skips with correct log message), threshold
exactly at minimum (cycle runs — boundary condition).

---

### TASK 1.6 — Add Missing Message Types to contracts.py

**File:** `milimo-blueprint/orchestrator/contracts.py`

Add the five missing message type definitions following the exact same
schema pattern as existing types:

```python
# 1. Content → Analytics
"content_performance_query": {
    "sender": "content",
    "recipients": ["analytics"],
    "payload": {
        "query": str,           # e.g. "top_performing_formats"
        "lookback_days": int,
        "platform": str | None  # None = all platforms
    },
    "frequency": "weekly",
    "schedule": "monday_06:00",
    "priority": "AUTO"
}

# 2. Content → Analytics
"performance_signal": {
    "sender": "content",
    "recipients": ["analytics"],
    "payload": {
        "post_id": str,
        "platform": str,
        "engagement_data": {
            "likes": int,
            "shares": int,
            "reach": int,
            "click_through": int,
            "saves": int | None
        },
        "publish_time": str,    # ISO timestamp
        "content_type": str,    # post, story, reel, article, etc.
        "client_id": str | None
    },
    "frequency": "on_event",
    "priority": "AUTO"
}

# 3. Content → Ops
"brief_acknowledged": {
    "sender": "content",
    "recipients": ["ops"],
    "payload": {
        "project_id": str,
        "estimated_first_draft_time": str,  # ISO timestamp
        "acknowledged_at": str              # ISO timestamp
    },
    "frequency": "on_event",
    "sla_minutes": 5,           # must send within 5 min of receiving brief
    "priority": "REVIEW"
}

# 4. Analytics → Content (INBOUND)
"client_health_signal": {
    "sender": "analytics",
    "recipients": ["content"],
    "payload": {
        "client_id": str,
        "health_score": float,  # 0.0 to 1.0
        "recommended_action": str
    },
    "frequency": "on_event",
    "priority": "REVIEW"
}

# 5. Ops → Content (INBOUND)
"revision_request": {
    "sender": "ops",
    "recipients": ["content"],
    "payload": {
        "project_id": str,
        "draft_id": str,
        "revision_notes": str,
        "deadline": str         # ISO timestamp
    },
    "frequency": "on_event",
    "priority": "REVIEW"
}
```

Also update the existing "brief" message type to match the full spec
payload schema:
  client_id, project_id, brief_text, deadline, tone_requirements,
  platform_targets

Write pytest tests for: all 5 new message types validate correctly,
brief payload schema validates with all required fields, missing required
field raises validation error, sender/recipient enforcement.

---

## PHASE 2 — DRAFT GENERATION ENGINE
## The core of the Content Claw. Complete Phase 1 before starting.

---

### TASK 2.1 — ContentGenerator Class

**New file:** `milimo-blueprint/orchestrator/content/content_generator.py`

This is the core class. It generates content using Nemotron via the
privacy router, applies all active evolution tools in sequence, and
writes processed drafts to the pending directory.

```python
@dataclass
class Draft:
    draft_id: str               # UUID
    platform: str               # twitter, linkedin, instagram, tiktok, email
    client_id: str | None
    project_id: str | None
    content_type: str           # post, story, reel, article, campaign, proposal
    raw_content: str            # Nemotron output before tool processing
    processed_content: str      # After all active tools applied
    tone: str | None            # Set by tone classifier if active
    approval_probability: float # Set by approval predictor if active
    scheduled_time: str | None  # Set by timing optimizer if active
    variant_b: str | None       # Set by A/B engine if active
    voice_profile_used: str | None
    tools_applied: list[str]    # Names of tools applied in sequence
    created_at: str             # ISO timestamp
    status: Literal["pending", "approved", "rejected", "published"]

class ContentGenerator:
    """
    Core draft generation engine for the Content Claw.

    Generates content using Nemotron via privacy router.
    Applies active evolution tools in sequence.
    Writes drafts to /sandbox/content/drafts/pending/.
    Queues drafts in War Room as REVIEW actions.
    """

    def __init__(
        self,
        privacy_router: PrivacyRouter,
        tool_registry: ToolRegistry,
        operational_log: ContentOperationalLog,
        fs: ContentFilesystemInit
    ): ...

    async def generate_draft(
        self,
        platform: str,
        context: DraftContext,    # brief, topic, tone hint, client_id
        content_type: str = "post"
    ) -> Draft: ...
    # 1. Build generation prompt from context
    # 2. Route inference via privacy_router:
    #    - Final drafts → cloud (data_type="client_facing_draft")
    #    - Ideation → local (data_type="internal_ideation")
    # 3. Apply active tools in this exact sequence:
    #    a. tone_classifier (if active)
    #    b. platform_calibrator (if active)
    #    c. client_voice_adapter (if active and client_id provided)
    #    d. approval_predictor (if active)
    #    e. timing_optimizer (if active)
    #    f. ab_variant_engine (if active — generates variant_b)
    # 4. Write draft JSON to /sandbox/content/drafts/pending/{draft_id}.json
    # 5. Log to operational.log: action_type="draft_generated"
    # 6. Return Draft object

    async def generate_from_brief(
        self,
        brief_id: str
    ) -> Draft: ...
    # Reads brief from /sandbox/content/briefs/active/{brief_id}.json
    # Calls generate_draft() with brief as context
    # Sends brief_acknowledged message via mesh

    async def generate_daily_plan(self) -> ContentPlan: ...
    # Called at 06:00 daily
    # Reads all active briefs from /sandbox/content/briefs/active/
    # Reads latest analytics intelligence report
    # Generates plan: which platforms, formats, clients, estimated times
    # Writes plan to /sandbox/content/calendar/scheduled/plan_{date}.json
    # Returns ContentPlan

    def _build_prompt(
        self,
        platform: str,
        context: DraftContext,
        style_guide: str | None = None
    ) -> str: ...
    # Constructs structured generation prompt
    # Includes: platform-specific instructions, tone guidance,
    # client voice notes if available, style guide excerpts if provided,
    # recent performance patterns from analytics feed

    def _apply_tool(
        self,
        tool_name: str,
        draft: Draft
    ) -> Draft: ...
    # Loads tool from tool registry
    # Applies tool to draft content
    # Records tool name in draft.tools_applied
    # Logs tool application to operational.log
    # Returns updated draft
    # Never crashes on tool failure — logs error, skips tool, continues
```

Write pytest tests covering: successful draft generation, tool pipeline
applied in correct order, tool failure skipped gracefully, brief-to-draft
flow, privacy router called with correct data_type per content type,
draft written to correct filesystem path, operational.log entry created.

---

### TASK 2.2 — Brief Management System

**New file:** `milimo-blueprint/orchestrator/content/brief_manager.py`

```python
@dataclass
class ContentBrief:
    brief_id: str
    project_id: str
    client_id: str
    brief_text: str
    deadline: str               # ISO timestamp
    tone_requirements: str
    platform_targets: list[str]
    received_at: str            # ISO timestamp
    acknowledged_at: str | None
    status: Literal["active", "completed", "expired"]
    drafts_generated: list[str] # draft_ids

class BriefManager:
    """
    Manages the lifecycle of project briefs received from Ops Claw.

    Handles: receipt, acknowledgment, draft association, completion.
    """

    def receive_brief(self, message: dict) -> ContentBrief: ...
    # Parses incoming project_brief message from Ops Claw
    # Validates all required payload fields
    # Writes brief JSON to /sandbox/content/briefs/active/{brief_id}.json
    # Schedules brief_acknowledged message (must send within 5 minutes)
    # Logs receipt to operational.log
    # Returns ContentBrief

    def acknowledge_brief(self, brief_id: str) -> None: ...
    # Sends brief_acknowledged message via mesh
    # Includes estimated_first_draft_time (now + 2 hours default)
    # Updates brief JSON with acknowledged_at timestamp
    # Logs acknowledgment to operational.log
    # Raises BriefAcknowledgmentError if called > 5 minutes after receipt

    def handle_revision_request(self, message: dict) -> None: ...
    # Parses incoming revision_request message from Ops Claw
    # Loads original draft from approved/ directory
    # Creates revision context for ContentGenerator
    # Queues regeneration task
    # Logs to operational.log: action_type="revision_requested"

    def complete_brief(self, brief_id: str, published_urls: list[str]) -> None: ...
    # Moves brief from active/ to completed/
    # Writes completion record with published URLs
    # Sends deliverable_complete message to Ops Claw
    # Logs completion to operational.log

    def get_active_briefs(self) -> list[ContentBrief]: ...

    def check_deadline_risks(self) -> list[BriefDeadlineRisk]: ...
    # Returns briefs where deadline is within 24 hours and no draft exists
```

Write pytest tests covering: brief receipt and write, 5-minute
acknowledgment window enforcement (on time / too late), revision request
handling, brief completion and move, deadline risk detection.

---

### TASK 2.3 — War Room Draft Queuing

**File:** `milimo-blueprint/orchestrator/content/content_generator.py`
**File:** `milimo-blueprint/orchestrator/solo_warroom.py`

After a draft is generated and written to pending/, it must appear in
the War Room queue as a REVIEW action with the correct card format.

Add `queue_draft_for_review()` method to ContentGenerator:

```python
async def queue_draft_for_review(self, draft: Draft) -> str:
    """
    Queue a generated draft in the War Room as a REVIEW action.

    Returns action_id for tracking.

    War Room card must show:
      - Claw: CONTENT CLAW
      - Mode: REVIEW
      - Summary: "Draft ready: {platform} {content_type} for {client_id or 'own content'}"
      - Metadata: platform, tone, approval_probability, scheduled_time
      - Actions: [View Draft] [APPROVE] [EDIT] [BLOCK]
      - If variant_b exists: [Compare A/B] link
    """
```

Update `solo_warroom.py` to handle content draft REVIEW actions:
  - Display draft content inline in War Room (not just a filename)
  - Show approval_probability as a percentage badge
  - Show scheduled_time if set by timing optimizer
  - Show "Variant B available" indicator if draft.variant_b is not None
  - On APPROVE: call content_approval_handler (Task 2.4)
  - On EDIT: call content_edit_handler (Task 2.4)
  - On BLOCK: call content_rejection_handler (Task 2.4)

---

### TASK 2.4 — Approval Flow Handlers

**New file:** `milimo-blueprint/orchestrator/content/approval_handler.py`

```python
class ContentApprovalHandler:
    """
    Handles all three operator decisions on content drafts.
    Implements the spec approval flow exactly.
    """

    def handle_approve(self, draft_id: str, action_id: str) -> None: ...
    # 1. Move draft file: pending/ → approved/
    # 2. If scheduled_time is set: write to calendar/scheduled/
    # 3. Log to approvals.log: APPROVED with timestamp and action_id
    # 4. Log to operational.log: action_type="draft_approved"
    # 5. If publish_immediately=True: trigger platform publisher (Task 3.1)
    # 6. If scheduled: add to publishing queue at scheduled_time

    def handle_edit(
        self,
        draft_id: str,
        edited_content: str,
        action_id: str
    ) -> None: ...
    # 1. Load original draft from pending/
    # 2. Save ORIGINAL as: pending/{draft_id}_original.json (preserve for learning)
    # 3. Update draft with edited_content
    # 4. Save edited version as new pending draft
    # 5. Calculate edit delta: what changed (for training signal)
    # 6. Write edit signal to operational.log:
    #    action_type="draft_edited", details={original, edited, delta}
    # 7. If significant changes (>20% content changed): re-queue for review
    # 8. If minor edit (<20%): auto-approve edited version

    def handle_block(
        self,
        draft_id: str,
        reason: str | None,
        action_id: str
    ) -> None: ...
    # 1. Move draft: pending/ → rejected/
    # 2. Log to approvals.log: BLOCKED with reason and action_id
    # 3. Log to operational.log: action_type="draft_rejected", details={reason}
    # 4. Write rejection signal (strong negative training data)
    # 5. If same brief has 3+ rejections: flag War Room alert
    #    "Repeated rejections on brief {brief_id} — may need clarification"

    def _calculate_edit_delta(
        self,
        original: str,
        edited: str
    ) -> float: ...
    # Returns ratio of changed characters to total characters
    # Used to determine re-review threshold
```

Write pytest tests covering: approve moves file and logs correctly,
edit below threshold auto-approves, edit above threshold re-queues,
block moves to rejected/ with reason, third rejection triggers alert,
edit delta calculation accuracy.

---

## PHASE 3 — PLATFORM PUBLISHING
## Complete Phase 2 before starting.

---

### TASK 3.1 — Platform Publisher

**New file:** `milimo-blueprint/orchestrator/content/platform_publisher.py`

```python
class PlatformPublisher:
    """
    Publishes approved content to social platforms via egress policy APIs.

    Critical rules:
    - Never publishes without approved draft status
    - Never publishes to an endpoint not in the egress allowlist
    - On failure: retries every 15 minutes for 2 hours
    - After 2 hours: escalates to War Room — never silently drops
    - All publish attempts logged to operational.log
    """

    SUPPORTED_PLATFORMS = {
        "twitter": TwitterPublisher,
        "linkedin": LinkedInPublisher,
        "instagram": InstagramPublisher,
        "tiktok": TikTokPublisher,
        "facebook": FacebookPublisher,
    }

    def publish(
        self,
        draft: Draft,
        credentials: PlatformCredentials
    ) -> PublishResult: ...
    # Validates draft.status == "approved" — raises if not
    # Selects platform-specific publisher
    # Attempts publish
    # On success:
    #   - Moves draft: approved/ → published/
    #   - Writes publish record to calendar/published/
    #   - Logs to operational.log: action_type="published"
    #   - Returns PublishResult with post_id and url
    # On failure:
    #   - Logs failure with error details
    #   - Schedules retry (15 min interval, max 2 hours)
    #   - Raises PublishError after exhausted retries

    def schedule_publish(
        self,
        draft: Draft,
        publish_time: str,
        credentials: PlatformCredentials
    ) -> str: ...
    # Writes scheduled publish entry to calendar/scheduled/
    # Returns schedule_id
    # Scheduler will call publish() at the correct time

    def _retry_with_backoff(
        self,
        draft: Draft,
        credentials: PlatformCredentials,
        max_retries: int = 8,
        interval_minutes: int = 15
    ) -> PublishResult: ...
```

Implement each platform publisher as a separate class:

```python
class TwitterPublisher:
    endpoint = "https://api.twitter.com/2/tweets"

    def publish(self, content: str, credentials: dict) -> PublishResult: ...
    # POST to Twitter API v2
    # Returns post_id and url

class LinkedInPublisher:
    endpoint = "https://api.linkedin.com/v2/ugcPosts"

    def publish(self, content: str, credentials: dict) -> PublishResult: ...

class InstagramPublisher:
    endpoint = "https://graph.instagram.com/me/media"

    def publish(self, content: str, media_url: str | None,
                credentials: dict) -> PublishResult: ...

class TikTokPublisher:
    endpoint = "https://api.tiktok.com/v1.3/post/publish/"

    def publish(self, content: str, video_url: str | None,
                credentials: dict) -> PublishResult: ...

class FacebookPublisher:
    endpoint = "https://graph.facebook.com/me/feed"

    def publish(self, content: str, credentials: dict) -> PublishResult: ...
```

Write pytest tests covering: successful publish moves draft to published/,
publish without approved status raises error, retry on failure (mock API),
escalation to War Room after 2-hour retry exhaustion, publish record
written to calendar/published/.

---

### TASK 3.2 — Performance Monitor

**New file:** `milimo-blueprint/orchestrator/content/performance_monitor.py`

```python
class PerformanceMonitor:
    """
    Monitors published content performance across platforms.

    Polls analytics endpoints (read-only) for engagement data.
    Writes results to performance.log.
    Sends performance_signal messages to Analytics Claw.
    Detects anomalies and flags them in War Room.
    """

    # Poll for performance data 1 hour after publish,
    # then again at 24 hours, then at 7 days

    def monitor_post(
        self,
        post_id: str,
        platform: str,
        publish_time: str
    ) -> None: ...
    # Schedules 3-point performance collection:
    # T+1hr, T+24hr, T+7days

    def collect_performance(
        self,
        post_id: str,
        platform: str,
        credentials: PlatformCredentials
    ) -> EngagementData: ...
    # Fetches engagement data from platform analytics API
    # Returns EngagementData: likes, shares, reach, click_through, saves

    def record_performance(
        self,
        post_id: str,
        data: EngagementData
    ) -> None: ...
    # Appends JSON line to /sandbox/content/logs/performance.log
    # Format: { post_id, platform, collected_at, engagement_data,
    #           content_type, client_id, publish_time }

    def send_performance_signal(
        self,
        post_id: str,
        data: EngagementData
    ) -> None: ...
    # Sends performance_signal message to Analytics Claw via mesh
    # Includes full engagement data and content metadata

    def detect_anomaly(
        self,
        post_id: str,
        data: EngagementData
    ) -> AnomalyResult | None: ...
    # Compares against 30-day baseline for this platform and content type
    # Anomaly threshold: >2x or <0.5x baseline engagement
    # Returns AnomalyResult if anomaly detected, None otherwise

    def flag_anomaly_in_war_room(
        self,
        anomaly: AnomalyResult
    ) -> None: ...
    # Queues anomaly as AUTO action in War Room evolution log
    # Message: "{platform} post {post_id} {outperformed/underperformed}
    #           baseline by {pct}% — flagged for evolution signal"
```

Write pytest tests covering: performance collection scheduling,
data written to performance.log correctly, performance_signal message
sent after collection, anomaly detection at threshold boundaries,
War Room anomaly flag queued.

---

### TASK 3.3 — Publishing Scheduler

**New file:** `milimo-blueprint/orchestrator/content/publish_scheduler.py`

```python
class PublishScheduler:
    """
    Reads calendar/scheduled/ and publishes content at the correct times.

    Runs continuously. Checks for due items every 60 seconds.
    Never misses a scheduled publish — handles restart recovery
    by checking calendar/scheduled/ on every startup.
    """

    def start(self) -> None: ...
    # Begin continuous scheduling loop

    def stop(self) -> None: ...

    def check_due_items(self) -> list[ScheduledItem]: ...
    # Reads all files in calendar/scheduled/
    # Returns items where publish_time <= now

    def recover_missed_publishes(self) -> list[ScheduledItem]: ...
    # Called on startup
    # Returns scheduled items with publish_time in the past
    # that have no corresponding entry in calendar/published/
    # These are "missed" — escalate to War Room for operator decision:
    # "Missed scheduled publish for {client_id} on {platform} — publish now?"
```

---

## PHASE 4 — BRAND VOICE SYSTEM
## Complete Phase 3 before starting.

---

### TASK 4.1 — Brand Voice Manager

**New file:** `milimo-blueprint/orchestrator/content/brand_voice.py`

```python
@dataclass
class VoiceProfile:
    profile_id: str
    client_id: str
    profile_name: str
    tone_descriptors: list[str]     # e.g. ["professional", "warm", "direct"]
    vocabulary_preferences: dict    # words to use / avoid
    sentence_length: str            # short / medium / long
    example_approved_posts: list[str]
    example_rejected_posts: list[str]
    created_at: str
    last_updated: str

class BrandVoiceManager:
    """
    Manages brand voice profiles for the squad and its clients.

    Voice profiles are stored in /sandbox/content/brand/voice-profiles/.
    They are built from approved post history and updated on every edit.
    Style calibration inference always routes to Local NIM.
    """

    def load_profile(self, client_id: str) -> VoiceProfile | None: ...
    # Reads profile JSON from voice-profiles/{client_id}.json
    # Returns None if no profile exists yet

    def create_profile(
        self,
        client_id: str,
        brief_tone_requirements: str
    ) -> VoiceProfile: ...
    # Creates initial profile from brief tone requirements
    # Augments with inference call to Local NIM:
    #   "Given these tone requirements, describe this brand's voice
    #    as a structured profile: tone_descriptors, vocabulary, sentence style"
    # Routes: data_type="voice_adapter_calibration" → local NIM (locked)
    # Writes profile to voice-profiles/{client_id}.json

    def update_profile_from_approval(
        self,
        client_id: str,
        approved_post: str
    ) -> VoiceProfile: ...
    # Adds approved post to example_approved_posts (max 20, FIFO)
    # Re-calibrates profile via Local NIM inference
    # Updates profile JSON

    def update_profile_from_rejection(
        self,
        client_id: str,
        rejected_post: str,
        reason: str | None
    ) -> VoiceProfile: ...
    # Adds to example_rejected_posts (max 10, FIFO)
    # Re-calibrates profile

    def apply_voice(
        self,
        content: str,
        client_id: str
    ) -> str: ...
    # Applies client voice profile to content via Local NIM
    # Routes: data_type="voice_adapter_calibration" → local NIM (locked)
    # Returns rewritten content in client's voice
    # Returns original content unchanged if no profile exists

    def load_style_guide(self, client_id: str | None = None) -> str | None: ...
    # Reads from brand/style-guides/{client_id}.md or brand/style-guides/default.md
    # Returns None if no style guide exists
```

Write pytest tests covering: profile creation from brief, profile update
from approval (FIFO list management), rejection update, apply_voice routing
to local NIM (never cloud), style guide loading, missing profile returns None.

---

## PHASE 5 — SCHEDULED AUTONOMY
## Complete Phase 4 before starting.

---

### TASK 5.1 — Daily Content Scheduler

**New file:** `milimo-blueprint/orchestrator/content/content_scheduler.py`

```python
class ContentScheduler:
    """
    Runs the scheduled autonomous actions defined in the spec.

    Morning planning: 06:00 daily
    Weekly analytics query: Monday 06:00
    Evolution cycle: handled by evolution_cycle.py (do not duplicate)
    """

    def start(
        self,
        generator: ContentGenerator,
        brief_manager: BriefManager,
        performance_monitor: PerformanceMonitor,
        mesh: MeshCoordinator
    ) -> None: ...
    # Schedules all recurring tasks using setTimeout approach
    # No cron, no new dependencies

    def _morning_planning(self) -> None: ...
    # Runs at 06:00 daily:
    # 1. Read all active briefs from brief_manager
    # 2. Read latest analytics intel from /intelligence/analytics-feed/
    # 3. Query Analytics Claw if Monday: send content_performance_query
    # 4. Generate daily content plan via generator.generate_daily_plan()
    # 5. Begin draft generation for highest-priority briefs
    # 6. Log to operational.log: action_type="morning_planning"

    def _send_weekly_analytics_query(self) -> None: ...
    # Runs Monday 06:00:
    # Send content_performance_query via mesh:
    #   query: "top_performing_formats", lookback_days: 7
    # Log to operational.log: action_type="analytics_query_sent"

    def _handle_analytics_intel(self, message: dict) -> None: ...
    # Handler for incoming performance_intel messages from Analytics Claw
    # Writes to /intelligence/analytics-feed/latest.json
    # Logs to operational.log: action_type="intel_received"
```

---

## FINAL VERIFICATION CHECKLIST

After completing all phases, confirm every item:

□ /sandbox/content/ full directory structure created on init
□ operational.log, approvals.log, performance.log created on init
□ Filesystem init is idempotent — no errors on repeat runs
□ graph.facebook.com, trends.google.com, api.buzzsumo.com in egress policy
□ analytics_synthesis, voice_adapter_calibration, ab_variant_generation
  have explicit inference routing entries in content-claw.yaml
□ content_calendar_update: AUTO, ab_test_variant: REVIEW,
  trend_reactive_post: REVIEW in solo-founder.yaml approval modes
□ Evolution cycle skips with correct log if rejected_drafts < 3
□ Evolution cycle skips with correct log if performance data < 1 week
□ All 5 new message types validate correctly in contracts.py
□ brief payload schema updated with all required fields
□ ContentGenerator.generate_draft() produces Draft with all fields set
□ Active tools applied in correct sequence: tone → platform → voice →
  predictor → timing → ab
□ Tool failure does not crash draft generation — skipped with log entry
□ Final drafts routed to cloud, ideation to local — verified by test
□ Voice adapter always routes to local NIM — PrivacyPolicyViolationError
  raised if cloud routing attempted
□ Brief received, written to active/, brief_acknowledged sent within 5 min
□ BriefManager.acknowledge_brief() raises after 5-minute SLA window
□ 3+ rejections on same brief triggers War Room alert
□ Approved draft moves to approved/ and calendar/scheduled/ if timed
□ Edited draft: minor edit auto-approves, major edit re-queues
□ Blocked draft moves to rejected/ with reason logged
□ Platform publishers post to correct endpoint for each platform
□ Publish failure retries every 15 min for max 2 hours
□ After 2-hour exhaustion: War Room escalation (never silent drop)
□ Publish confirmation written to calendar/published/
□ Performance collected at T+1hr, T+24hr, T+7days post-publish
□ performance_signal sent to Analytics Claw after each collection
□ Anomaly detected at >2x or <0.5x baseline — flagged in War Room
□ Missed publishes detected on scheduler restart and escalated
□ Voice profile created from brief tone requirements
□ Voice profile updates from approvals (max 20 examples, FIFO)
□ Voice profile updates from rejections (max 10 examples, FIFO)
□ apply_voice() never routes to cloud — test asserts local NIM always
□ Morning planning runs at 06:00 daily
□ Weekly analytics query sends Monday 06:00
□ Performance intel from Analytics Claw written to analytics-feed/
□ All pytest tests pass in milimo-blueprint/
□ All Jest tests pass in milimo/

---

## OUTPUT FORMAT

For each task:

  --- TASK N.N: [Title] ---
  Files: [exact paths — NEW or UPDATE]
  Summary: [one sentence — what this implements]

  [complete implementation — no TODOs, no stubs, no placeholders]

  Tests: [complete test file immediately after implementation]
  -----------------------------------------

Begin with Task 1.1. Do not proceed to 1.2 until 1.1 is complete
with tests passing.

The spec is the ground truth. If this prompt conflicts with the spec,
the spec wins.
