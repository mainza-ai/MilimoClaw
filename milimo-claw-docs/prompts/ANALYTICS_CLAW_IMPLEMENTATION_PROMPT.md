# MILIMO CLAW — ANALYTICS CLAW IMPLEMENTATION PROMPT
# ─────────────────────────────────────────────────────────────────────────────
# Attach this prompt alongside:
#   1. ANALYTICS_CLAW_IMPLEMENTATION_AUDIT.md  (the gap analysis)
#   2. MILIMO_CLAW_ANALYTICS_CLAW_SPEC.md      (the ground truth spec)
#   3. analytics-claw.yaml                      (role blueprint — EXISTS)
#   4. analytics-sandbox.yaml                   (sandbox policy — EXISTS)
#   5. contracts.py                             (message types — EXISTS)
# ─────────────────────────────────────────────────────────────────────────────

You are an expert Python engineer building the Analytics Claw for Milimo
Claw — a multi-agent autonomous hustle platform built on NVIDIA NemoClaw.

The audit confirms the Analytics Claw is 0% implemented. The configuration
files exist (analytics-claw.yaml, analytics-sandbox.yaml, contracts.py)
but no Python orchestration code has been written. You are building
everything from scratch.

The spec document is the ground truth. The audit defines what must be built.
This prompt defines exactly how to build it.

---

## CONTEXT — THE SYSTEM YOU ARE BUILDING INTO

The Analytics Claw is the intelligence layer of the Milimo Claw mesh.
It receives data signals from all other claws, synthesizes them into
actionable intelligence, and publishes a weekly report that every other
claw reads. It never publishes, communicates with clients, writes code,
or moves money. It only observes and informs.

**Five claws in the mesh:**
  - Content Claw  — sends performance_signal, queries top formats
  - Ops Claw      — sends client_health_signal, client_onboarded
  - Finance Claw  — sends revenue_summary
  - Build Claw    — sends shipping_summary, queries feature behavior
  - Analytics Claw — THIS IS WHAT YOU ARE BUILDING

**Existing integrations that expect Analytics Claw to exist:**
  - `content_scheduler.py` already sends weekly analytics queries
    via mesh at Monday 06:00 — `_send_weekly_analytics_query()`
  - `performance_monitor.py` already sends `performance_signal`
    messages after every published post — `send_performance_signal()`
  - Content Claw reads analytics intel from:
    `/sandbox/content/intelligence/analytics-feed/latest.json`
    (this is a copy of the shared report — see filesystem note below)

**Shared filesystem mount — the most critical dependency:**
  `/sandbox/analytics/reports/weekly-intelligence.json`
  must be readable by ALL five claws. This is configured in each claw's
  sandbox policy. Verify the mount exists in analytics-sandbox.yaml
  before writing any generation code. If it is missing, add it.

**Plugin structure:**
  - Python orchestrator: `milimo-blueprint/orchestrator/`
  - New Analytics files:  `milimo-blueprint/orchestrator/analytics/`
  - Role blueprint:       `milimo-blueprint/roles/analytics-claw.yaml`
  - Sandbox policy:       `milimo-blueprint/policies/analytics-sandbox.yaml`
  - Operator config:      `~/.milimo/config.json`

**Operator:** Mainza Kangombe — senior systems architect, experienced
Python 3.11+ engineer. Production-quality code only. No stubs. No TODOs.
No placeholder comments. Every function must be complete and runnable.

---

## DEVELOPMENT PHASE CONSTRAINTS

**Inference:** ALL inference routes to cloud (Nemotron 120B via NVIDIA
Cloud API) during development. Do NOT implement local NIM routing.
Do NOT enforce privacy routing. DO log `data_type` as a field on every
inference call so routing can be enforced later with a flag change only.

Example inference call pattern:
```python
response = self.inference_client.complete(
    prompt=prompt,
    data_type="report_narrative_generation",  # ALWAYS LOG THIS
    max_tokens=500
)
```

**Sandbox isolation still applies.** Even in development, the Analytics
Claw must only write to `/sandbox/analytics/` and only receive other
claws' data via typed inter-claw messages. The Landlock filesystem
restriction is enforced at the kernel level regardless of dev/prod mode.

**Standards (non-negotiable):**
  - Python 3.11+, full type hints, docstrings on every class and method
  - pathlib.Path only — never os.path string concatenation
  - PyYAML safe_load only — never yaml.load()
  - Append-only log files using file locking for thread safety
  - Atomic file writes for reports: write to temp file first,
    rename on success — never overwrite a good report with a partial one
  - Never silently swallow exceptions — log and re-raise or return
    typed error results
  - Tests: pytest with full coverage for every class

---

## PHASE 1 — CORE INFRASTRUCTURE
## Build in exact task order. Do not proceed to Phase 2 until all
## Phase 1 tests pass.

---

### TASK 1.1 — Analytics Filesystem Initialization

**New file:** `milimo-blueprint/orchestrator/analytics/analytics_init.py`

```python
from pathlib import Path
from dataclasses import dataclass, field
from typing import Literal
import json
import fcntl

BASE = Path("/sandbox/analytics")

REQUIRED_DIRS = [
    "reports/weekly-intelligence-archive",
    "signals/anomalies",
    "signals/opportunities",
    "signals/alerts",
    "data/content-performance",
    "data/client-health",
    "data/revenue",
    "data/delivery-velocity",
    "baselines",
    "tools/engagement-baseline-model",
    "tools/anomaly-detector",
    "tools/opportunity-scorer",
    "tools/retention-correlator",
    "tools/competitor-signal-tracker",
    "tools/forward-projection-engine",
    "logs",
]

REQUIRED_FILES = [
    "logs/operational.log",
    "logs/queries.log",
    "logs/signals.log",
    "reports/opportunity-scores.json",
]

@dataclass
class InitResult:
    created_dirs: list[str] = field(default_factory=list)
    created_files: list[str] = field(default_factory=list)
    already_existed: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.failed) == 0

@dataclass
class ValidationResult:
    missing_dirs: list[str] = field(default_factory=list)
    missing_files: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.missing_dirs and not self.missing_files

class AnalyticsFilesystemInit:
    """
    Creates and validates the full /sandbox/analytics/ filesystem structure.
    Called during onboarding and on every claw startup.
    Idempotent — safe to call multiple times.
    """

    def initialize(self) -> InitResult: ...
    # Create all REQUIRED_DIRS and REQUIRED_FILES
    # Never overwrite existing files
    # Write empty JSON objects to .json files on creation
    # Return InitResult with full accounting

    def validate(self) -> ValidationResult: ...
    # Check all required paths exist
    # Return ValidationResult — never raise, never create

    def get_signal_path(
        self,
        signal_type: Literal["anomalies", "opportunities", "alerts"],
        signal_id: str
    ) -> Path: ...

    def get_data_path(
        self,
        data_type: Literal[
            "content-performance", "client-health",
            "revenue", "delivery-velocity"
        ],
        sub_path: str = ""
    ) -> Path: ...
```

Also implement `AnalyticsOperationalLog`:

```python
@dataclass
class AnalyticsLogEntry:
    timestamp: str        # ISO 8601
    action_type: str      # signal_received, report_generated, query_answered, etc.
    entity_id: str        # signal_id, report_date, query_id
    source_claw: str | None
    outcome: str          # success, failed, partial, skipped
    details: dict

class AnalyticsOperationalLog:
    """Append-only structured log for all Analytics Claw actions."""

    def __init__(self, log_path: Path): ...

    def append(self, entry: AnalyticsLogEntry) -> None: ...
    # Write JSON line — thread-safe file locking

    def read_recent(
        self,
        days: int = 7,
        action_type: str | None = None
    ) -> list[AnalyticsLogEntry]: ...

    def count_by_type(self, action_type: str, days: int = 7) -> int: ...
```

Write pytest tests: directory creation, idempotent re-run, validation
pass/fail cases, log append and read, concurrent write safety.

---

### TASK 1.2 — Signal Processor

**New file:** `milimo-blueprint/orchestrator/analytics/signal_processor.py`

The signal processor is the Analytics Claw's inbound data pipeline.
Every message received from another claw passes through here before
any analysis runs.

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import uuid
from datetime import datetime

@dataclass
class InboundSignal:
    signal_id: str
    message_type: str
    source_claw: str
    received_at: str      # ISO timestamp
    payload: dict
    stored_path: Path

class SignalProcessor:
    """
    Processes and stores all inbound signals from other claws.

    Validates message schema against contracts.py.
    Writes raw signal data to /sandbox/analytics/data/{type}/.
    Triggers anomaly detection on every content performance signal.
    Dispatches client health alerts immediately when score < 6.0.
    Logs every received signal to signals.log.
    """

    def process(self, raw_message: dict) -> InboundSignal: ...
    # 1. Validate message_type exists in contracts
    # 2. Validate sender matches contract sender_roles
    # 3. Validate all required payload fields present
    # 4. Route to correct handler based on message_type
    # 5. Log to signals.log: signal received
    # 6. Return InboundSignal
    # Raise SignalValidationError on schema violation — never silently accept

    def handle_performance_signal(self, signal: InboundSignal) -> None: ...
    # Write to: /sandbox/analytics/data/content-performance/
    #   {platform}/{YYYY-MM}/performance.jsonl (append)
    # Trigger: anomaly_detector.check(signal)
    # Log: action_type="performance_signal_stored"

    def handle_client_health_signal(self, signal: InboundSignal) -> None: ...
    # Write to: /sandbox/analytics/data/client-health/
    #   {client_id}/health-history.jsonl (append)
    # Check: if health_score < 6.0 → dispatch client_health_alert immediately
    # Log: action_type="client_health_stored"

    def handle_client_onboarded(self, signal: InboundSignal) -> None: ...
    # Write to: /sandbox/analytics/data/client-health/
    #   {client_id}/health-history.jsonl (create with onboarding entry)
    # Log: action_type="client_onboarded_stored"

    def handle_revenue_summary(self, signal: InboundSignal) -> None: ...
    # Write to: /sandbox/analytics/data/revenue/weekly-revenue.jsonl (append)
    # Check: anomaly against revenue baseline
    # Log: action_type="revenue_summary_stored"

    def handle_shipping_summary(self, signal: InboundSignal) -> None: ...
    # Write to: /sandbox/analytics/data/delivery-velocity/velocity.jsonl (append)
    # Log: action_type="shipping_summary_stored"

    def _get_jsonl_path(
        self,
        data_type: str,
        sub_keys: list[str]
    ) -> Path: ...
    # Build correct path for JSONL storage
    # Create parent directories if they don't exist

    def _append_jsonl(self, path: Path, record: dict) -> None: ...
    # Thread-safe append to JSONL file
    # Uses file locking
```

Write pytest tests: each handler stores data correctly, schema
validation rejects malformed messages, health score < 6.0 triggers
immediate alert dispatch (mock the alert sender), JSONL paths correct
per platform and date, concurrent signal handling.

---

### TASK 1.3 — Baseline Manager

**New file:** `milimo-blueprint/orchestrator/analytics/baseline_manager.py`

Baselines are the foundation for anomaly detection. Without calibrated
baselines, anomaly detection produces only noise.

```python
from dataclasses import dataclass
from pathlib import Path
import json
from datetime import datetime, timedelta
from typing import Any

@dataclass
class ContentBaseline:
    platform: str
    content_type: str
    metric: str               # engagement_rate, reach, click_through, etc.
    mean: float
    std_dev: float
    sample_count: int
    window_days: int          # always 30
    calculated_at: str        # ISO timestamp
    upper_anomaly_threshold: float   # mean * 2.0
    lower_anomaly_threshold: float   # mean * 0.5

@dataclass
class RevenueBaseline:
    metric: str               # week_total, invoices_paid, etc.
    mean: float
    std_dev: float
    sample_count: int
    calculated_at: str
    upper_anomaly_threshold: float
    lower_anomaly_threshold: float

@dataclass
class DeliveryBaseline:
    metric: str               # prs_merged, deploys, avg_pr_cycle_hours
    mean: float
    std_dev: float
    sample_count: int
    calculated_at: str
    upper_anomaly_threshold: float
    lower_anomaly_threshold: float

class BaselineManager:
    """
    Calculates and maintains 30-day rolling baselines for all tracked metrics.

    Runs full recalculation every Sunday at 01:00 (before report generation).
    Baselines are required before anomaly detection can produce reliable results.
    Returns None baselines when insufficient data exists — anomaly detection
    must handle None baselines gracefully (skip, do not crash).
    """

    WINDOW_DAYS = 30
    MIN_SAMPLES = 5  # Minimum data points before baseline is valid

    def recalculate_all(self) -> dict[str, Any]: ...
    # Recalculate all baselines from stored JSONL data
    # Write to /sandbox/analytics/baselines/
    # Log: action_type="baselines_recalculated"
    # Return summary: {metric: sample_count} for all baselines

    def recalculate_content_baselines(self) -> list[ContentBaseline]: ...
    # Read all performance.jsonl files in data/content-performance/
    # Filter to last 30 days only
    # Group by platform × content_type × metric
    # Calculate mean, std_dev, thresholds for each group
    # Write to baselines/content-baselines.json
    # Return None for groups with < MIN_SAMPLES

    def recalculate_revenue_baseline(self) -> list[RevenueBaseline]: ...
    # Read data/revenue/weekly-revenue.jsonl
    # Filter to last 30 days
    # Calculate per-metric baselines
    # Write to baselines/revenue-baseline.json

    def recalculate_delivery_baseline(self) -> list[DeliveryBaseline]: ...
    # Read data/delivery-velocity/velocity.jsonl
    # Filter to last 30 days
    # Calculate per-metric baselines
    # Write to baselines/delivery-baseline.json

    def load_content_baselines(self) -> dict[str, ContentBaseline]: ...
    # Read baselines/content-baselines.json
    # Return keyed by "{platform}:{content_type}:{metric}"
    # Return empty dict if file doesn't exist

    def load_revenue_baseline(self) -> dict[str, RevenueBaseline]: ...
    def load_delivery_baseline(self) -> dict[str, DeliveryBaseline]: ...

    def has_sufficient_data(self) -> tuple[bool, str]: ...
    # Returns (True, "") if enough data for meaningful baselines
    # Returns (False, "reason") if insufficient
    # Used by scheduler to skip baseline calc on fresh installs
```

Write pytest tests: recalculation from mock JSONL data, min sample
threshold (fewer than 5 samples returns None baseline), 30-day window
filtering (data older than 30 days excluded), threshold calculation
(2x upper, 0.5x lower), load from file, empty file handling.

---

### TASK 1.4 — Query Handler

**New file:** `milimo-blueprint/orchestrator/analytics/query_handler.py`

The 2-minute query response SLA is the only hard performance requirement
in the Analytics Claw. Every query must get a response — never a timeout.

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import time

@dataclass
class QueryResponse:
    query_id: str
    query_type: str
    responding_to: str        # message_id of original query
    requesting_claw: str
    data_quality: str         # "complete", "partial", "estimated", "insufficient"
    data: dict | None
    generated_at: str         # ISO timestamp
    processing_time_ms: int

class QueryHandler:
    """
    Handles on-demand queries from other claws.

    SLA: 2-minute maximum response time — enforced by timeout wrapper.
    Never returns without a response. If data unavailable, returns
    data_quality="insufficient" with days_collected and days_needed.
    Every query and response logged to queries.log.
    """

    RESPONSE_TIMEOUT_SECONDS = 110  # 110s gives 10s margin under 2-min SLA

    def handle(self, raw_message: dict) -> QueryResponse: ...
    # Route to correct handler by message_type
    # Enforce RESPONSE_TIMEOUT_SECONDS — if processing exceeds this,
    # return best available partial response with data_quality="partial"
    # Log query receipt and response dispatch to queries.log
    # Send response via mesh

    def handle_content_performance_query(
        self,
        query: str,
        lookback_days: int,
        platform: str | None,
        requesting_claw: str,
        query_id: str
    ) -> QueryResponse: ...
    # Read from data/content-performance/ filtered to lookback_days
    # Group by format: calculate avg_engagement per content type
    # Sort descending by avg_engagement
    # Return top 10 formats with engagement data
    # If insufficient data: return data_quality="insufficient" with
    #   days_collected and days_needed fields

    def handle_behavior_query(
        self,
        query: str,
        feature_id: str | None,
        lookback_days: int,
        requesting_claw: str,
        query_id: str
    ) -> QueryResponse: ...
    # Read from data/delivery-velocity/ and data/client-health/
    # Correlate feature shipping dates with client health changes
    # Return feature_adoption_rates, retention_correlation, recommendations
    # If insufficient data: return data_quality="insufficient"

    def _insufficient_response(
        self,
        query_id: str,
        query_type: str,
        requesting_claw: str,
        days_collected: int,
        days_needed: int
    ) -> QueryResponse: ...
    # Standard insufficient data response — reuse this everywhere

    def _count_days_collected(self, data_type: str) -> int: ...
    # Count unique dates in the relevant JSONL file
    # Used for "days_collected" in insufficient responses
```

Write pytest tests: content query returns top formats sorted correctly,
behavior query correlates data correctly, timeout enforced (mock slow
aggregation), insufficient data returns correct response shape,
data_quality flags set correctly, query logged to queries.log.

---

## PHASE 2 — INTELLIGENCE GENERATION
## Complete all Phase 1 tests before starting Phase 2.

---

### TASK 2.1 — Anomaly Detector

**New file:** `milimo-blueprint/orchestrator/analytics/anomaly_detector.py`

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
import uuid
from datetime import datetime

@dataclass
class DetectedAnomaly:
    signal_id: str
    anomaly_id: str
    detected_at: str            # ISO timestamp
    metric: str
    current_value: float
    baseline_mean: float
    baseline_std_dev: float
    ratio: float                # current / baseline_mean
    direction: Literal["positive", "negative"]
    severity: Literal["mild", "significant", "extreme"]
    # mild:      1.5x–2x or 0.33x–0.5x
    # significant: 2x–5x or 0.2x–0.33x
    # extreme:   >5x or <0.2x
    requires_attention: bool    # True for negative extreme anomalies only
    target_claw: str            # Which claw should receive the alert

class AnomalyDetector:
    """
    Detects performance anomalies by comparing incoming signals
    against 30-day rolling baselines.

    Triggered on every inbound signal that has a baseline.
    Skips detection gracefully when no baseline exists (fresh install).
    Writes detected anomalies to /sandbox/analytics/signals/anomalies/.
    Dispatches alert messages to target claws immediately.
    Logs all detections to signals.log.
    """

    POSITIVE_THRESHOLD = 2.0    # >2x baseline = positive anomaly
    NEGATIVE_THRESHOLD = 0.5    # <0.5x baseline = negative anomaly

    def check_content_signal(
        self,
        signal: dict,
        baselines: dict
    ) -> DetectedAnomaly | None: ...
    # Compare engagement_rate against content baseline
    # Return None if no baseline exists for this platform/content_type
    # Return None if value is within normal range
    # Return DetectedAnomaly if threshold crossed

    def check_revenue_signal(
        self,
        signal: dict,
        baselines: dict
    ) -> DetectedAnomaly | None: ...
    # Compare week_total against revenue baseline

    def check_delivery_signal(
        self,
        signal: dict,
        baselines: dict
    ) -> DetectedAnomaly | None: ...
    # Compare prs_merged and avg_pr_cycle_hours against delivery baseline

    def _classify_severity(self, ratio: float, direction: str) -> str: ...
    # mild: 1.5x–2x positive or 0.33x–0.5x negative
    # significant: 2x–5x positive or 0.2x–0.33x negative
    # extreme: >5x positive or <0.2x negative

    def _determine_target_claw(self, anomaly_type: str) -> str: ...
    # content anomaly → "content"
    # revenue anomaly → "finance"
    # delivery anomaly → "build"
    # client health anomaly → "ops"

    def save_anomaly(self, anomaly: DetectedAnomaly) -> Path: ...
    # Write to /sandbox/analytics/signals/anomalies/{anomaly_id}.json
    # Log to signals.log

    def dispatch_alert(self, anomaly: DetectedAnomaly) -> None: ...
    # Send appropriate message to target_claw via mesh:
    #   revenue anomaly → revenue_anomaly message to Finance Claw
    #   client health → client_health_alert message to Ops Claw
    #   delivery slow → retention_signals message to Build Claw
    #   content anomaly → performance_intel message to Content Claw
    # Log dispatch to signals.log
```

Write pytest tests: threshold correctly triggers at 2x and 0.5x,
no detection when no baseline exists (None returned), severity
classification at each boundary, target claw routing correct per
anomaly type, anomaly written to correct path, alert dispatched.

---

### TASK 2.2 — Report Generator

**New file:** `milimo-blueprint/orchestrator/analytics/report_generator.py`

This is the Analytics Claw's primary output. The entire squad depends on
the weekly intelligence report being accurate, complete, and well-formed.

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json
import tempfile
import shutil
from datetime import datetime, timedelta

@dataclass
class WeeklyReport:
    generated_at: str
    week_of: str              # YYYY-MM-DD (Monday of the week)
    squad_id: str
    content_performance: dict
    client_health: dict
    revenue: dict
    delivery: dict
    opportunities: list[dict]
    anomalies: list[dict]
    forward_projections: dict
    summary_narrative: str
    data_quality: dict        # per-section quality flags

class ReportGenerator:
    """
    Generates the weekly intelligence report every Sunday at 02:00.

    ATOMIC WRITE: Always writes to a temp file first, then renames.
    Never overwrites a successful report with a partial or failed one.
    Archives the previous report before writing the new one.
    Surfaces a REVIEW alert in the War Room if generation fails.

    Data sources (all from /sandbox/analytics/data/):
    - content-performance/ JSONL files
    - client-health/ JSONL files
    - revenue/weekly-revenue.jsonl
    - delivery-velocity/velocity.jsonl

    External data (from approved read-only APIs):
    - trends.google.com — trend signals
    - Platform analytics APIs — algorithm change detection
    If external APIs unavailable: generate report without them,
    mark affected sections with data_quality="internal_only"
    """

    REPORT_PATH = Path("/sandbox/analytics/reports/weekly-intelligence.json")
    ARCHIVE_DIR = Path("/sandbox/analytics/reports/weekly-intelligence-archive")

    def generate(self) -> WeeklyReport: ...
    # Full generation sequence:
    # 1. Aggregate content performance for past 7 days
    # 2. Aggregate client health signals for past 7 days
    # 3. Aggregate revenue data for past 7 days
    # 4. Aggregate delivery velocity for past 7 days
    # 5. Pull external trend data (graceful fallback if unavailable)
    # 6. Run anomaly detection pass on all aggregated data
    # 7. Run opportunity scoring pass
    # 8. Generate forward projections (if sufficient history)
    # 9. Generate summary narrative via inference (cloud)
    # 10. Assemble complete WeeklyReport
    # 11. Write atomically (temp → rename)
    # 12. Archive previous report
    # Log: action_type="report_generated"

    def write_atomically(self, report: WeeklyReport) -> None: ...
    # 1. Serialize report to JSON string
    # 2. Write to temp file in same directory as REPORT_PATH
    # 3. Validate JSON is parseable (catch corruption)
    # 4. Archive existing report if present:
    #    copy to ARCHIVE_DIR/{YYYY-MM-DD}.json
    # 5. Rename temp file to REPORT_PATH (atomic on POSIX)
    # 6. Log: action_type="report_written"

    def _aggregate_content_performance(
        self,
        days: int = 7
    ) -> dict: ...
    # Read all performance.jsonl files in data/content-performance/
    # Filter to last `days` days
    # Calculate: top_formats, top_platforms, top_publish_times,
    #   worst_performing per platform
    # Returns content_performance section of report

    def _aggregate_client_health(self, days: int = 7) -> dict: ...
    # Read all health-history.jsonl files in data/client-health/
    # Calculate overall_score (mean of all client scores this week)
    # Identify at_risk_clients (score < 6.0)
    # Identify healthy_clients (score >= 8.0)
    # Returns client_health section

    def _aggregate_revenue(self, days: int = 7) -> dict: ...
    # Read data/revenue/weekly-revenue.jsonl
    # Get latest week entry + previous week for WoW calculation
    # Returns revenue section

    def _aggregate_delivery(self, days: int = 7) -> dict: ...
    # Read data/delivery-velocity/velocity.jsonl
    # Calculate velocity metrics
    # Returns delivery section

    def _generate_narrative(self, report: WeeklyReport) -> str: ...
    # Inference call to cloud Nemotron:
    # data_type="report_narrative_generation"  ← LOG THIS
    # Prompt: structured summary of key metrics
    # Returns: 3-4 sentence plain English narrative
    # Fallback: generate rule-based narrative if inference fails

    def _generate_empty_report(self, reason: str) -> WeeklyReport: ...
    # Returns a valid but empty report when data is insufficient
    # Sets all data_quality flags to "insufficient"
    # summary_narrative = "Insufficient data for analysis. {reason}"
    # Used during first 3 weeks of operation
```

Write pytest tests: atomic write (verify temp file cleaned up on
success and failure), archive creates correct filename, empty report
on insufficient data, all 7 aggregation sections populated from mock
JSONL data, narrative generated via inference (mock the inference call),
valid JSON output always, previous report preserved if new generation fails.

---

### TASK 2.3 — Opportunity Scorer

**New file:** `milimo-blueprint/orchestrator/analytics/opportunity_scorer.py`

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
from datetime import datetime

@dataclass
class ScoredOpportunity:
    opportunity_id: str
    detected_at: str          # ISO timestamp
    type: str                 # content_format, client_segment, product_feature,
                              # platform_timing, pricing_adjustment
    description: str          # plain English, one sentence
    confidence: float         # 0.0 to 1.0
    potential_impact: str     # "low", "medium", "high"
    squad_readiness: float    # 0.0 to 1.0 — can squad act on this now?
    recommended_action: str   # concrete next step, one sentence
    target_claw: str          # which claw should receive this signal
    expires_at: str | None    # Some opportunities are time-sensitive

class OpportunityScorer:
    """
    Identifies growth opportunities by comparing squad performance
    against external trend signals and internal capability assessment.

    Runs daily at 06:00.
    High-confidence opportunities (>0.85) dispatched immediately.
    All opportunities written to reports/opportunity-scores.json.
    Logged to signals.log.
    """

    IMMEDIATE_DISPATCH_THRESHOLD = 0.85

    def score_all(self) -> list[ScoredOpportunity]: ...
    # Run all scoring passes:
    # 1. content_format_opportunities()
    # 2. platform_timing_opportunities()
    # 3. client_segment_opportunities() — if client health data exists
    # 4. Filter: confidence > 0.3 (below this = noise)
    # 5. Sort: by confidence descending
    # 6. Write to opportunity-scores.json
    # 7. Dispatch any with confidence > IMMEDIATE_DISPATCH_THRESHOLD
    # 8. Log to signals.log

    def content_format_opportunities(self) -> list[ScoredOpportunity]: ...
    # Compare squad's content type distribution against trend data
    # Identify formats with high trend signal that squad uses rarely
    # Use inference to characterize opportunity:
    #   data_type="opportunity_scoring"  ← LOG THIS
    # Example: "Carousel posts trending on LinkedIn — squad not using"

    def platform_timing_opportunities(self) -> list[ScoredOpportunity]: ...
    # Analyze squad's publishing time distribution vs engagement peaks
    # Identify timing gaps where engagement could improve

    def client_segment_opportunities(self) -> list[ScoredOpportunity]: ...
    # Analyze client health distribution
    # Identify segments with strong health scores (potential for expansion)
    # Identify common characteristics of high-value clients

    def dispatch_high_confidence(
        self,
        opportunity: ScoredOpportunity
    ) -> None: ...
    # Send performance_intel to Content Claw if type is content-related
    # Send retention_signals to Build Claw if feature-related
    # Log dispatch to signals.log

    def write_opportunity_scores(
        self,
        opportunities: list[ScoredOpportunity]
    ) -> None: ...
    # Write to reports/opportunity-scores.json
    # Overwrite (not append) — this is the current state
    # Include generated_at timestamp
```

Write pytest tests: high-confidence opportunity dispatched immediately,
low-confidence opportunity not dispatched, opportunity scores written
to correct path, all scoring passes run in score_all(), inference
called with correct data_type, empty result when no data available.

---

### TASK 2.4 — Forward Projector

**New file:** `milimo-blueprint/orchestrator/analytics/forward_projector.py`

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
from datetime import datetime, timedelta

@dataclass
class ForwardProjection:
    metric: str
    projection_weeks: int       # always 4
    point_estimate: float
    confidence_interval_low: float
    confidence_interval_high: float
    confidence_level: float     # 0.0 to 1.0 — based on history length
    data_weeks_used: int        # how many weeks of history used
    risk_flags: list[str]       # plain English risk notes
    generated_at: str

class ForwardProjector:
    """
    Generates 4-week forward projections for key metrics.

    Requires minimum 8 weeks of historical data for reliable projections.
    Returns low-confidence projections with wide intervals when < 8 weeks.
    Never refuses to project — always returns something.
    """

    MIN_WEEKS_FOR_RELIABLE_PROJECTION = 8
    PROJECTION_WEEKS = 4

    def project_all(self) -> dict[str, ForwardProjection]: ...
    # Generate projections for:
    # - revenue.week_total
    # - content.avg_engagement_rate (per platform)
    # - delivery.prs_merged
    # Returns dict keyed by metric name

    def project_revenue(self) -> ForwardProjection: ...
    # Read data/revenue/weekly-revenue.jsonl
    # Simple linear trend + seasonality adjustment if enough data
    # If < MIN_WEEKS: wide confidence interval, low confidence_level
    # Identify risk flags: declining trend, high variance, recent anomaly

    def project_content_engagement(
        self,
        platform: str
    ) -> ForwardProjection: ...
    # Read data/content-performance/{platform}/ aggregated weekly
    # Project average engagement rate for next 4 weeks
    # Flag if platform algorithm signals suggest pending change

    def project_delivery_velocity(self) -> ForwardProjection: ...
    # Read data/delivery-velocity/velocity.jsonl
    # Project PRs merged per week for next 4 weeks

    def _calculate_confidence_level(
        self,
        weeks_available: int
    ) -> float: ...
    # 0–3 weeks: 0.2 (very low)
    # 4–7 weeks: 0.5 (moderate)
    # 8–15 weeks: 0.75 (good)
    # 16+ weeks: 0.90 (high)

    def _calculate_confidence_interval(
        self,
        estimate: float,
        std_dev: float,
        confidence_level: float
    ) -> tuple[float, float]: ...
    # Wider interval for lower confidence levels
    # Returns (low, high)
```

Write pytest tests: projection with < 8 weeks returns low confidence,
projection with 16+ weeks returns high confidence, confidence interval
wider for low confidence, all metrics projected in project_all(),
risk flags identified from declining trends, projection from mock data.

---

## PHASE 3 — SCHEDULING AND INTEGRATION
## Complete all Phase 2 tests before starting Phase 3.

---

### TASK 3.1 — Analytics Scheduler

**New file:** `milimo-blueprint/orchestrator/analytics/analytics_scheduler.py`

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
import threading
import time
import logging
from datetime import datetime, timedelta

class AnalyticsScheduler:
    """
    Orchestrates all scheduled autonomous actions for the Analytics Claw.

    Schedule (all local time):
      Sunday 01:00 — Baseline recalculation
      Sunday 02:00 — Weekly intelligence report generation
      Daily  06:00 — Opportunity scoring

    Uses threading.Timer with recalculated delay to next occurrence.
    No cron dependency. No APScheduler. Only stdlib.

    On startup: checks if any scheduled jobs were missed during downtime
    (e.g. if claw was offline during Sunday 02:00). If missed, runs
    the job immediately and logs "missed job recovered".
    """

    def __init__(
        self,
        baseline_manager,
        report_generator,
        opportunity_scorer,
        operational_log
    ): ...

    def start(self) -> None: ...
    # Initialize all scheduled jobs
    # Check for missed jobs since last shutdown
    # Log: action_type="scheduler_started"

    def stop(self) -> None: ...
    # Cancel all pending timers cleanly
    # Log: action_type="scheduler_stopped"

    def _schedule_next(
        self,
        job_name: str,
        job_fn: Callable,
        target_hour: int,
        target_minute: int,
        target_weekday: int | None = None   # 0=Monday, 6=Sunday. None=daily
    ) -> None: ...
    # Calculate seconds until next occurrence of target time
    # Schedule with threading.Timer
    # After execution: schedule next occurrence (self-rescheduling)

    def _run_baseline_recalculation(self) -> None: ...
    # Sunday 01:00
    # Run baseline_manager.recalculate_all()
    # Log timing and result

    def _run_weekly_report(self) -> None: ...
    # Sunday 02:00
    # Run report_generator.generate()
    # Send performance_intel to Content Claw after generation
    # Send retention_signals to Build Claw after generation
    # Log timing and result
    # If fails: surface REVIEW alert in War Room

    def _run_opportunity_scoring(self) -> None: ...
    # Daily 06:00
    # Run opportunity_scorer.score_all()
    # Log timing and result

    def _check_missed_jobs(self) -> None: ...
    # Read last_run timestamps from operational.log
    # If Sunday report last ran > 8 days ago: run immediately
    # If baselines last recalculated > 8 days ago: run immediately
    # Log any recovered jobs

    def _seconds_until(
        self,
        target_hour: int,
        target_minute: int,
        target_weekday: int | None = None
    ) -> float: ...
    # Calculate precise seconds until next occurrence
```

Write pytest tests: scheduler starts and stops cleanly, _seconds_until
returns positive value for any future target, missed job recovery
triggered when last run > 8 days ago, each scheduled job calls correct
function, self-rescheduling verified (timer re-registers after execution).

---

### TASK 3.2 — Outbound Signal Dispatcher

**New file:** `milimo-blueprint/orchestrator/analytics/signal_dispatcher.py`

```python
from dataclasses import dataclass
from typing import Any

class SignalDispatcher:
    """
    Sends all outbound messages from the Analytics Claw to other claws.

    All sends go through the inter-claw mesh gateway.
    Every dispatch logged to signals.log.
    Never raises on dispatch failure — logs and continues.
    """

    def send_performance_intel(
        self,
        top_formats: list[dict],
        top_times: list[dict],
        engagement_trends: list[dict],
        audience_signals: list[dict]
    ) -> None: ...
    # Send performance_intel to Content Claw
    # Triggered after weekly report generation
    # and immediately on high-confidence content opportunity

    def send_retention_signals(
        self,
        feature_adoption_rates: list[dict],
        churn_correlation: list[dict],
        recommended_features: list[dict]
    ) -> None: ...
    # Send retention_signals to Build Claw
    # Triggered after weekly report generation
    # and on churn anomaly detection

    def send_client_health_alert(
        self,
        client_id: str,
        health_score: float,
        risk_factors: list[str],
        recommended_action: str
    ) -> None: ...
    # Send client_health_alert to Ops Claw
    # Triggered IMMEDIATELY when health score < 6.0
    # Does not wait for weekly report

    def send_revenue_anomaly(
        self,
        anomaly_type: str,
        current_value: float,
        baseline_value: float,
        severity: str
    ) -> None: ...
    # Send revenue_anomaly to Finance Claw
    # Triggered IMMEDIATELY on anomaly detection

    def send_content_performance_response(
        self,
        query_id: str,
        requesting_claw: str,
        response_data: dict
    ) -> None: ...

    def send_behavior_query_response(
        self,
        query_id: str,
        requesting_claw: str,
        response_data: dict
    ) -> None: ...

    def _send(
        self,
        message_type: str,
        recipient_role: str,
        payload: dict
    ) -> None: ...
    # Core send via mesh gateway
    # Includes message_id (UUID), timestamp, sender_role="analytics"
    # Log to signals.log: action_type="signal_dispatched"
    # On exception: log error, do not raise
```

Write pytest tests: each send method calls _send with correct
message_type and recipient, payload structure matches contracts.py
schema, dispatch failure logged but not raised, signals.log entry
created for every dispatch.

---

## PHASE 4 — WIRE EVERYTHING TOGETHER
## Complete all Phase 3 tests before starting Phase 4.

---

### TASK 4.1 — Analytics Claw Main Entry Point

**New file:** `milimo-blueprint/orchestrator/analytics/analytics_claw.py`

```python
class AnalyticsClaw:
    """
    Main entry point for the Analytics Claw.
    Initializes all components, wires them together, and starts the scheduler.
    Called by the NemoClaw blueprint orchestrator on sandbox startup.
    """

    def __init__(self, squad_id: str, inference_client: Any): ...

    def startup(self) -> None: ...
    # 1. Run filesystem init — validate structure
    # 2. Log startup to operational.log
    # 3. Initialize all components with shared dependencies
    # 4. Register inbound message handlers with mesh router:
    #    - performance_signal → signal_processor.handle_performance_signal
    #    - client_health_signal → signal_processor.handle_client_health_signal
    #    - client_onboarded → signal_processor.handle_client_onboarded
    #    - revenue_summary → signal_processor.handle_revenue_summary
    #    - shipping_summary → signal_processor.handle_shipping_summary
    #    - content_performance_query → query_handler.handle
    #    - behavior_query → query_handler.handle
    # 5. Start analytics_scheduler
    # 6. Log: action_type="claw_started"

    def shutdown(self) -> None: ...
    # Stop scheduler cleanly
    # Log: action_type="claw_stopped"

    def handle_inbound(self, raw_message: dict) -> None: ...
    # Route inbound message to correct handler
    # Log receipt to operational.log
    # Catch all exceptions — never crash on bad input
```

---

### TASK 4.2 — Verify Shared Filesystem Mount

**BEFORE ANY OTHER INTEGRATION WORK:**

Check `analytics-sandbox.yaml` for the shared mount configuration.
The file at `/sandbox/analytics/reports/weekly-intelligence.json` must
be readable by all other claws.

Add or verify this entry exists in analytics-sandbox.yaml:
```yaml
filesystem:
  primary: "/sandbox/analytics"
  shared_exports:
    - path: "/sandbox/analytics/reports/weekly-intelligence.json"
      readable_by: ["content", "ops", "finance", "build"]
      writable_by: []   # analytics only writes this — others read only
```

Also verify in each other claw's sandbox policy that they mount this
path as read-only. If any claw policy is missing this mount, add it.

This is the highest-priority integration verification step.

---

### TASK 4.3 — Integration Test Suite

**New file:** `milimo-blueprint/tests/test_analytics_integration.py`

Implement the 11-step minimum viable first run sequence from the spec:

```python
def test_mvr_step_01_performance_signal_stored():
    """Inject mock performance_signal — confirm stored in data/."""

def test_mvr_step_02_data_written_to_correct_path():
    """Confirm JSONL written to data/content-performance/{platform}/."""

def test_mvr_step_03_query_received():
    """Inject mock content_performance_query — confirm received."""

def test_mvr_step_04_query_response_within_sla():
    """Confirm response dispatched within 2 minutes (120 seconds)."""

def test_mvr_step_05_seven_days_of_signals():
    """Inject 7 days of mock signals — all stored correctly."""

def test_mvr_step_06_manual_report_generation():
    """Trigger report generation manually — confirm no exceptions."""

def test_mvr_step_07_report_file_written():
    """Confirm weekly-intelligence.json exists and is valid JSON."""

def test_mvr_step_08_content_claw_can_read_report():
    """Simulate Content Claw file read — confirm access."""

def test_mvr_step_09_ops_claw_can_read_report():
    """Simulate Ops Claw file read — confirm access."""

def test_mvr_step_10_health_signal_below_threshold():
    """Inject client_health_signal with score 5.0."""

def test_mvr_step_11_health_alert_dispatched_immediately():
    """Confirm client_health_alert sent to Ops Claw (do not await weekly)."""
```

All 11 tests must pass before the claw is considered minimally functional.

---

## FINAL VERIFICATION CHECKLIST

After completing all phases, confirm every item:

□ /sandbox/analytics/ full directory structure created on analytics_init
□ operational.log, queries.log, signals.log created on init
□ filesystem init is idempotent — no errors on repeated calls
□ performance_signal stored to correct platform/date path
□ client_health_signal score < 6.0 triggers immediate client_health_alert
□ client_health_signal score >= 6.0 stored only — no immediate alert
□ revenue_summary stored to revenue/weekly-revenue.jsonl
□ shipping_summary stored to delivery-velocity/velocity.jsonl
□ Baseline recalculation reads last 30 days only — older data excluded
□ Baselines return None when < 5 samples — no false anomalies on fresh install
□ Anomaly detection triggers at exactly 2.0x threshold (positive)
□ Anomaly detection triggers at exactly 0.5x threshold (negative)
□ No anomaly detection when no baseline exists (graceful skip)
□ content_performance_query response within 2 minutes
□ behavior_query response within 2 minutes
□ Query response returns data_quality="insufficient" when < 3 days data
□ Weekly report written atomically — temp file never left on disk
□ Previous report archived to weekly-intelligence-archive/{date}.json
□ Report generation fails gracefully — previous report preserved
□ Report with no data returns valid JSON with empty sections
□ Opportunity scoring runs daily and writes to opportunity-scores.json
□ Opportunity with confidence > 0.85 dispatched immediately
□ Forward projections include confidence intervals
□ Forward projection confidence low (0.2) when < 8 weeks of history
□ Scheduler starts without cron or APScheduler
□ Missed jobs detected on startup and run immediately
□ Scheduler self-reschedules after each execution
□ Shared mount verified: all claws can read weekly-intelligence.json
□ All inbound message types wired to correct handlers
□ All outbound dispatch methods log to signals.log
□ Dispatch failure logged but never raises
□ data_type logged on every inference call (cloud during dev)
□ All 11 MVR integration tests pass
□ All unit tests pass: pytest milimo-blueprint/orchestrator/analytics/

---

## OUTPUT FORMAT

For each task:

  --- TASK N.N: [Title] ---
  File: [exact path — NEW]
  Summary: [one sentence]

  [complete implementation — no TODOs, no stubs, no placeholders]

  Tests: [complete pytest file immediately after]
  -----------------------------------------

Begin with Task 1.1. Do not proceed to 1.2 until 1.1 tests pass.
The spec is ground truth. If this prompt conflicts with the spec, the spec wins.
All inference to cloud. Log data_type on every call. No local NIM routing.
