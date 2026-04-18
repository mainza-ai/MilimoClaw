# Evolution Configuration

Global configuration for the self-evolution engine.

## Purpose

Defines parameters for weekly evolution cycles including scheduling, observation windows, pattern detection, tool building, and deployment rules.

## File Location

`milimo-blueprint/evolution_config.yaml`

## Key Sections

### Cycle Scheduling

| Parameter | Default | Description |
|-----------|---------|-------------|
| `cycle_interval_days` | 7 | One evolution cycle per week |
| `cycle_day` | sunday | Day of week to run |
| `cycle_hour` | 3 | Hour (24h) to start (low-activity) |
| `allow_manual_trigger` | true | Allow `milimo evolution --trigger-now` |

### Observation Window

| Parameter | Default | Description |
|-----------|---------|-------------|
| `window_days` | 7 | Days of operation log to review |
| `minimum_actions` | 20 | Min actions to justify a cycle |
| `cross_signal_lookback_days` | 14 | Lookback for cross-claw signals |

### Pattern Detection

| Parameter | Default | Description |
|-----------|---------|-------------|
| `minimum_confidence` | 0.6 | Patterns below ignored |
| `max_patterns_per_cycle` | 5 | Top N patterns to consider |

**Pattern Types:**
- `classifier` — Categorize inputs/outputs
- `optimizer` — Improve timing, format, routing
- `predictor` — Forecast outcomes
- `generator_variant` — Alternative output generation (A/B)
- `anomaly_detector` — Surface unexpected deviations

### Tool Building

| Parameter | Default | Description |
|-----------|---------|-------------|
| `backtest_window_weeks` | 4 | Historical data replay |
| `minimum_improvement_percent` | 5 | Must beat baseline by ≥5% |
| `max_build_attempts` | 3 | Retry generation limit |
| `build_timeout_seconds` | 300 | Max time per build |
| `inference_backend` | local-nim | Always local for code gen |

### Tool Deployment

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_tools_per_claw` | 30 | Hard cap per claw |
| `require_proposal_approval` | false | Proposals to War Room first |
| `auto_disable_on_regression` | true | Disable if performance drops |
| `version_bump_strategy` | patch | patch per tool, minor per month |

### Logging

| Parameter | Default | Description |
|-----------|---------|-------------|
| `log_proposals` | true | Log all proposals including rejected |
| `log_backtests` | true | Log backtest results |
| `notify_war_room` | true | Send evolution events to War Room |

## Relationships

- Used by: [[evolution-cycle]] — Weekly evolution execution
- Used by: [[tool-generation]] — Tool building parameters
- Overrides: Squad configs can override in `squad_state.yaml`

## Source

`milimo-blueprint/evolution_config.yaml`
