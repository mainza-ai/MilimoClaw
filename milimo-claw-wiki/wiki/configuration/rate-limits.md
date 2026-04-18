# Rate Limits

Auto-approval rate limits by tier.

## Purpose

Defines rate limits for auto-approved actions to encourage tier upgrades. Free tier has strict limits; Pro tier is unlimited.

## File Location

`milimo-blueprint/rate-limits.yaml`

## Tier Definitions

### Free Tier

| Parameter | Value |
|-----------|-------|
| `daily_limit` | 10 |
| `burst_limit` | 3 |
| `burst_window_hours` | 1 |

**Features:**
- Basic squad mesh
- Self-evolution (max 5 tools)
- Blueprint marketplace (view only)

### Pro Tier

| Parameter | Value |
|-----------|-------|
| `daily_limit` | Unlimited |
| `burst_limit` | Unlimited |

**Features:**
- Full squad mesh
- Unlimited self-evolution
- Blueprint marketplace (buy/sell)
- Priority War Room support
- Mobile app access

### University Tier

| Parameter | Value |
|-----------|-------|
| `daily_limit` | 50 |
| `burst_limit` | 10 |
| `burst_window_hours` | 1 |

**Features:**
- Full squad mesh
- Self-evolution (max 30 tools)
- Blueprint marketplace (view only)
- Cohort management

## Always Require Approval

These actions always require manual approval regardless of tier:
- `invoice_over_500` — Invoice >$500
- `client_offboarding` — Client offboarding
- `brand_voice_change` — Brand voice modifications
- `payment_execution` — Payment execution
- `rate_change` — Pricing rate changes
- `external_data_sharing` — Sharing squad data externally

## Auto-Approvable Actions

| Trigger | Description |
|---------|-------------|
| `social_post_draft` | Social media draft |
| `internal_draft` | Internal draft |
| `task_completion` | Task completion |
| `routine_report` | Weekly routine reports |

## Behavior

### On Limit Exceeded

- **Action**: `require_manual_approval`
- **Message**: "Daily auto-approval limit reached. Manual approval required."

### Notifications

- **Warn at remaining**: 3
- **Notify on limit**: true
- **Notify admin**: true

### Reset Schedule

- **Timezone**: UTC
- **Daily reset hour**: 0 (Midnight)

## Monitoring

### Metrics Tracked

- `total_requests`
- `allowed_requests`
- `denied_requests`
- `current_remaining`
- `utilization_percent`

### Alert Thresholds

| Alert | Threshold | Severity |
|-------|-----------|----------|
| High utilization | 80% | warning |
| Limit reached | 100% | info |

## Relationships

- Used by: War Room TUI — Rate limit display
- Used by: Approval system — Limit enforcement

## Source

`milimo-blueprint/rate-limits.yaml`
