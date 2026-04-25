# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Content Claw Package

Core autonomous functionality for the Content Claw:
- Filesystem initialization
- Draft generation
- Brief management
- Platform publishing
- Performance monitoring
- Brand voice system
- Scheduled autonomy
"""

from .content_init import (
    ContentFilesystemInit,
    InitResult,
    ValidationResult,
    ContentOperationalLog,
    LogEntry,
    generate_draft_id,
    generate_brief_id,
    generate_post_id,
)

from .content_generator import (
    ContentGenerator,
    Draft,
    DraftContext,
    ContentPlan,
)

from .brief_manager import (
    BriefManager,
    ContentBrief,
    BriefDeadlineRisk,
    BriefError,
    BriefValidationError,
    BriefAcknowledgmentError,
)

from .approval_handler import (
    ContentApprovalHandler,
    ApprovalResult,
    EditDelta,
    RejectionAlert,
)

from .platform_publisher import (
    PlatformPublisher,
    PlatformCredentials,
    PublishResult,
    EngagementData,
    NotApprovedError,
    PlatformNotSupportedError,
    RetryExhaustedError,
)

from .performance_monitor import (
    PerformanceMonitor,
    PerformanceRecord,
    AnomalyResult,
)

from .publish_scheduler import (
    PublishScheduler,
    ScheduledItem,
    MissedPublish,
)

from .brand_voice import (
    BrandVoiceManager,
    VoiceProfile,
)

from .content_scheduler import ContentScheduler

from .content_claw import ContentClaw

__all__ = [
    "ContentFilesystemInit",
    "InitResult",
    "ValidationResult",
    "ContentOperationalLog",
    "LogEntry",
    "generate_draft_id",
    "generate_brief_id",
    "generate_post_id",
    "ContentGenerator",
    "Draft",
    "DraftContext",
    "ContentPlan",
    "BriefManager",
    "ContentBrief",
    "BriefDeadlineRisk",
    "BriefError",
    "BriefValidationError",
    "BriefAcknowledgmentError",
    "ContentApprovalHandler",
    "ApprovalResult",
    "EditDelta",
    "RejectionAlert",
    "PlatformPublisher",
    "PlatformCredentials",
    "PublishResult",
    "EngagementData",
    "NotApprovedError",
    "PlatformNotSupportedError",
    "RetryExhaustedError",
    "PerformanceMonitor",
    "PerformanceRecord",
    "AnomalyResult",
    "PublishScheduler",
    "ScheduledItem",
    "MissedPublish",
    "BrandVoiceManager",
    "VoiceProfile",
    "ContentScheduler",
    "ContentClaw",
]
