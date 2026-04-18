# Baseline Manager

Calculates and maintains 30-day rolling baselines for all tracked metrics.

## Purpose

Enables anomaly detection by providing statistical baselines. Runs full recalculation every Sunday at 01:00 (before report generation).

## Key Behaviors

- **WINDOW_DAYS = 30** — Rolling 30-day calculation window
- **MIN_SAMPLES = 5** — Minimum samples required for valid baseline
- Returns `None` baselines when insufficient data exists
- Calculates mean, std_dev, upper/lower anomaly thresholds

## Data Classes

### ContentBaseline

Baseline for content performance metrics:
- `platform`, `content_type`, `metric` — Identifiers
- `mean`, `std_dev` — Statistics
- `sample_count`, `window_days` — Metadata
- `upper_anomaly_threshold`, `lower_anomaly_threshold` — Detection bounds

### RevenueBaseline

Baseline for revenue metrics:
- `metric` — "week_total", "invoices_paid", "invoices_pending"
- Same statistical fields as ContentBaseline

### DeliveryBaseline

Baseline for delivery velocity metrics:
- `metric` — "prs_merged", "deploys", "avg_pr_cycle_hours"
- Same statistical fields

## Methods

| Method | Purpose |
|--------|---------|
| `recalculate_all()` | Full recalculation of all baselines |
| `recalculate_content_baselines()` | Content performance baselines |
| `recalculate_revenue_baseline()` | Revenue baselines |
| `recalculate_delivery_baseline()` | Delivery velocity baselines |
| `load_content_baselines()` | Load from `baselines/content.json` |
| `load_revenue_baseline()` | Load from `baselines/revenue.json` |
| `load_delivery_baseline()` | Load from `baselines/delivery.json` |
| `has_sufficient_data()` | Check if enough data exists |

## File Locations

```
/sandbox/analytics/
├── baselines/
│   ├── content.json      # Content baseline data
│   ├── revenue.json      # Revenue baseline data
│   └── delivery.json     # Delivery baseline data
└── data/
    ├── content-performance/
    ├── revenue/weekly-revenue.jsonl
    └── delivery-velocity/velocity.jsonl
```

## Threshold Calculation

```python
upper_anomaly_threshold = mean * 2.0
lower_anomaly_threshold = mean * 0.5
```

## Relationships

- Used by: [[anomaly-detector]] — Compares current values against baselines
- Depends on: `AnalyticsFilesystemInit` — Filesystem abstraction
- Logs to: `AnalyticsOperationalLog` — Action logging

## Source

`milimo-blueprint/orchestrator/analytics/baseline_manager.py`
