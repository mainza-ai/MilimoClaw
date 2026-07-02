# Spend Flow Tests

**Summary**: Automated tests for the Stripe Link spend flow robustness fixes — JSON array parsing, daemon-restart state recovery for `SpendApprovalHandler`, and `SpendWarRoomBridge` payload fallback recovery.

**Sources**:
- `milimo-blueprint/tests/test_spend_flow.py`

**Last updated**: 2026-07-03

**Tags**: #development #testing #finance #spend #stripe

---

## Test File

`milimo-blueprint/tests/test_spend_flow.py`

Run in isolation:

```bash
pytest milimo-blueprint/tests/test_spend_flow.py
# Result: 4 passed in 3.05s
```

Run inside the live Hermes sandbox container:

```bash
docker exec -u sandbox <container-id> env PYTHONPATH=/sandbox/.nemoclaw/blueprints/0.1.0 \
  /opt/hermes/.venv/bin/pytest /sandbox/.nemoclaw/blueprints/0.1.0/tests/test_spend_flow.py
# Result: 4 passed in 3.05s
```

Run with the full suite:

```bash
pytest milimo-blueprint/tests
# Result: 1239 passed, 1 skipped in 27.54s
```

The container active code path is typically `/sandbox/.nemoclaw/blueprints/0.1.0/`. If host edits do not appear inside the container, sync with `docker cp` to that path before running tests.

---

## Test Cases

### `test_json_array_parsing_and_status_updates`

Verifies that `handle_hold_release` safely handles `link-cli` JSON array responses.

`link-cli spend-request create --format json` returns an array of objects. The handler must extract the first element before accessing `.get("id")`. This test asserts:

- Array input is unwrapped to the first element
- `.get("id")` resolves the spend request ID correctly
- No `AttributeError` is raised on list payloads

### `test_state_recovery_across_restarts`

Assures `SpendApprovalHandler._get_request()` fully reconstructs a `SpendRequest` from `logs/decisions.log` when the in-memory `self._requests` cache is empty (simulating a daemon restart).

The test:

1. Creates a spend request and advances it through REVIEW → approve → HOLD
2. Clears `handler._requests` to simulate memory loss
3. Calls `_get_request(spend_id)` and asserts the reconstructed request matches the original state
4. Replays `approve`, `block`, `release`, and `cancel` transitions from the log to confirm state continuity

### `test_warroom_bridge_fallback_recovery`

Validates `SpendWarRoomBridge._find_action_payload()` fallback when in-memory `_review_actions` and `_hold_actions` mappings are lost.

The test:

1. Queues a spend review and records the War Room action ID
2. Clears the bridge's internal mappings
3. Calls `approve_review`, `block_review`, `release_hold`, and `cancel_hold`
4. Asserts each method recovers the correct internal spend action ID from the `SoloWarRoom` payload instead of crashing with `KeyError`

### `test_background_polling_and_restart_recovery`

Verifies the non-blocking spend release architecture:

1. Asserts `handle_hold_release` returns without waiting for Link approval (non-blocking)
2. Confirms a background daemon thread is started for polling
3. Simulates polling state transitions (`pending_approval` → `approved` / `denied`)
4. Verifies `_recover_and_resume_polling()` resumes orphaned polling threads on startup for any `hold` + `release` entries in `decisions.log` that never reached a terminal state

Uses class-level patches to safely manage thread lifetimes during test runs.

---

## Related Pages

- [[spend-handler]] — Non-blocking execution, background polling thread, self-healing startup recovery, robust JSON parsing, and `_get_request` state recovery
- [[spend-warroom-bridge]] — `_find_action_payload` fallback recovery
- [[link-cli-setup]] — Stripe Link CLI setup and device auth
- [[war-room]] — War Room TUI and HTMX dashboard
- [[testing]] — General test structure and conventions

---

## See Also

- `milimo-blueprint/tests/test_spend_flow.py` — Test implementation
- `milimo-core/src/milimo_core/finance/spend_handler.py` — Handler under test
- `milimo-blueprint/orchestrator/finance/spend_warroom_bridge.py` — Bridge under test
