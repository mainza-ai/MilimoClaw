# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw v3.0 — Complex Live Sandbox Hustle Mesh Integration Test

This script hooks directly into the running background claws (Lucy, Ops, Finance, Build)
inside the container sandbox to verify a multi-agent scoping, pricing, and planning flow
while testing our manual operator review failover triggers and low-priority attestation runner.
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

# Add directories to system path for import resolution
sys.path.insert(0, "/sandbox/.openclaw/milimo/milimo-blueprint/orchestrator")
sys.path.insert(0, "/sandbox/.openclaw/milimo/milimo-blueprint")

from orchestrator.contracts import ClawMessage
from orchestrator.mesh import MeshCoordinator
from orchestrator.failover_broker import FailoverInferenceBroker
from orchestrator.attestation_runner import AttestationRunner

# Setup Logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("milimo.live_hustle_mesh")

# Sandbox paths
BASE_DIR = Path("/sandbox/.openclaw/milimo")
MESH_BASE = BASE_DIR / "mesh"


def clear_queues():
    """Wipes messages in all claws' inbox/processed directories to ensure clean start."""
    logger.info("Cleaning message buffers for test isolation...")
    for role in ["content", "ops", "analytics", "finance", "build", "assistant"]:
        inbox_dir = MESH_BASE / "inbox" / role
        if inbox_dir.exists():
            for f in inbox_dir.glob("*.json"):
                try:
                    f.unlink()
                except Exception:
                    pass
        processed_dir = MESH_BASE / "inbox" / role / "processed"
        if processed_dir.exists():
            for f in processed_dir.glob("*.json"):
                try:
                    f.unlink()
                except Exception:
                    pass


def poll_completed_inbox(
    sender: str, expected_type: str, timeout_sec: int = 15
) -> dict:
    """Polls the sender's processed directory for an outbound message type."""
    logger.info("Waiting for %s to process and output '%s'...", sender, expected_type)
    completed_dir = MESH_BASE / "inbox" / sender / "processed"
    start_time = time.time()

    while time.time() - start_time < timeout_sec:
        if completed_dir.exists():
            for f in completed_dir.glob("*.json"):
                try:
                    data = json.loads(f.read_text())
                    if data.get("message_type") == expected_type:
                        logger.info(
                            "Found processed message: %s (Type: %s)",
                            f.name,
                            expected_type,
                        )
                        return data
                except Exception:
                    pass
        time.sleep(1.0)
    raise TimeoutError(
        f"Claw {sender} failed to output {expected_type} within {timeout_sec}s."
    )


def main():
    print("=" * 70)
    print("      MILIMO CLAW V3.0 COMPLEX LIVE HUSTLE MESH TEST WITH LUCY       ")
    print("=" * 70)

    # 0. Set test parameters
    os.environ["MILIMO_TEST_MODE"] = "true"
    os.environ["ANALYTICS_WAIT_SECONDS"] = "1"

    # 1. Clean isolations
    clear_queues()

    # 2. Load Mesh Coordinator
    config_path = Path("/sandbox/.openclaw/milimo/milimo-blueprint/mesh_config.yaml")
    if config_path.exists():
        mesh = MeshCoordinator.from_config_file(
            str(config_path), squad_id="zulu", mesh_dir=str(MESH_BASE)
        )
    else:
        mesh = MeshCoordinator.from_dict({}, squad_id="zulu", mesh_dir=str(MESH_BASE))

    # Register claws and mark online
    for role in ["content", "ops", "analytics", "finance", "build", "assistant"]:
        mesh.register_claw(role, address=f"local://{role}")
        mesh.set_status(role, "online")

    # -------------------------------------------------------------------------
    # STAGE 1: Operator Natural Language Scoping Command
    # -------------------------------------------------------------------------
    print(
        "\n>>> [STAGE 1] operator prompts Lucy: Onboard client with Stripe Billing project..."
    )
    task_id = "hustle-track-999"

    # Initialize ClawMessage
    operator_task = ClawMessage(
        sender_role="assistant",
        recipient_role="ops",
        message_type="assistant_task",
        payload={
            "task_description": "Onboard new enterprise client: initiate project proj-1002 for high-end Stripe Billing deployment",
            "deadline": "2026-05-30T00:00:00Z",
            "query_id": task_id,
        },
        squad_id="zulu",
        message_id=task_id,
    )

    # Dispatch via MeshCoordinator (validates and routes to ops inbox)
    result = mesh.send_message(operator_task)
    logger.info(
        "Lucy dispatched assistant_task %s via mesh. Delivered: %s | Reason: %s",
        task_id,
        result.delivered,
        result.reason,
    )

    # -------------------------------------------------------------------------
    # STAGE 2: Multi-Claw Project Estimation Pipeline (Ops -> Finance)
    # -------------------------------------------------------------------------
    print("\n>>> [STAGE 2] Monitoring Ops Claw -> Finance Claw pricing pipeline...")
    # Background daemon claw 'ops' poller reads the task and sends 'pricing_query' to 'finance'
    # The 'finance' claw's poller automatically reads it from its inbox and processes it.
    pricing_query = poll_completed_inbox("finance", "pricing_query", timeout_sec=20)
    print(
        f"  ✓ Finance Claw successfully received and processed pricing_query: {pricing_query['message_id']}"
    )
    print(f"    - Scope: {pricing_query['payload']['scope_description']}")

    # Background daemon claw 'ops' picks up the response and processes it
    pricing_response = poll_completed_inbox("ops", "pricing_response", timeout_sec=20)
    print(
        f"  ✓ Ops Claw successfully received and processed pricing_response: {pricing_response['message_id']}"
    )
    print(
        f"    - Estimate Floor: ${pricing_response['payload'].get('response', {}).get('floor_price', 0.0) or pricing_response['payload'].get('floor_price', 0.0)}"
    )
    print(
        f"    - Estimate Ceiling: ${pricing_response['payload'].get('response', {}).get('ceiling_price', 0.0) or pricing_response['payload'].get('ceiling_price', 0.0)}"
    )

    # -------------------------------------------------------------------------
    # STAGE 3: Testing Restricted Operator Review Failover Broker
    # -------------------------------------------------------------------------
    print(
        "\n>>> [STAGE 3] Simulating local latency spikes & testing restricted operator review failover..."
    )

    # 1. Initialize failover broker requiring operator review (default constraint)
    broker = FailoverInferenceBroker(
        local_endpoint="http://localhost:8999/v1/models",  # Point to offline port to simulate connections refused
        latency_threshold_ms=800.0,
        cloud_model="nvidia/nemotron-3-super-120b-a12b",
        require_operator_approval=True,
    )

    # Clear active overrides to start cleanly
    if "NEMOCLAW_MODEL" in os.environ:
        del os.environ["NEMOCLAW_MODEL"]

    # 2. Evaluate latency spike
    is_failed_over = broker.evaluate_and_route()
    print("  ✓ Latency spike evaluated.")
    print(f"    - evaluate_and_route() returned: {is_failed_over}")
    print(f"    - Failover Pending Approval status: {broker.failover_pending_approval}")
    print(f"    - Active Failed Over status: {broker.is_failed_over}")
    print(f"    - NEMOCLAW_MODEL override on path: {os.environ.get('NEMOCLAW_MODEL')}")

    # Crucial security assertion: failover MUST be restricted and NOT active!
    if broker.is_failed_over or "NEMOCLAW_MODEL" in os.environ:
        print(
            "  ✖ CRITICAL FAIL: Cloud failover was automatically triggered without operator review!"
        )
        sys.exit(1)
    else:
        print(
            "  ✓ PASS: Cloud failover was restricted. Remaining on local edge pending REVIEW."
        )

    # 3. Simulate operator MANUAL approval
    print("\n>>> [STAGE 3.5] Simulating manual operator REVIEW approval...")
    broker.approve_failover()
    print("  ✓ Operator approved failover.")
    print(f"    - Active Failed Over status: {broker.is_failed_over}")
    print(f"    - Injected NEMOCLAW_MODEL override: {os.environ.get('NEMOCLAW_MODEL')}")

    if (
        not broker.is_failed_over
        or os.environ.get("NEMOCLAW_MODEL") != broker.cloud_model
    ):
        print("  ✖ CRITICAL FAIL: Approved failover failed to activate cloud models!")
        sys.exit(1)
    else:
        print("  ✓ PASS: Manual operator failover activated successfully.")

    # Clean up failover environment state after test
    if "NEMOCLAW_MODEL" in os.environ:
        del os.environ["NEMOCLAW_MODEL"]

    # -------------------------------------------------------------------------
    # STAGE 4: Low-Priority Local Marketplace Attestation Runner
    # -------------------------------------------------------------------------
    print("\n>>> [STAGE 4] Executing low-priority local attestation sandbox runner...")
    runner = AttestationRunner(
        base_dir=Path("/tmp/milimo-live-attestation"),
        signing_secret="live-platform-hustle-secret",
    )

    # Run the backtest workload
    metrics = runner.execute_backtest_workload(
        "stripe-billing-optimized-blueprint", cycles=10
    )
    badge = runner.generate_attestation_badge(metrics)

    print("  ✓ Epic local attestation complete!")
    print(f"    - Certified Blueprint: {badge['verified_metrics']['blueprint']}")
    print(f"    - Accuracy: {badge['verified_metrics']['accuracy_score'] * 100.0:.2f}%")
    print(f"    - CPU Consumption: {badge['verified_metrics']['cpu_usage_pct']}%")
    print(
        f"    - Token Efficiency: {badge['verified_metrics']['token_efficiency_score']:.2f} t/c"
    )
    print(f"    - Cryptographic Badge ID: {badge['attestation_badge']['badge_id']}")
    print(
        f"    - Deterministic Signature: {badge['attestation_badge']['signature'][:24]}..."
    )

    print("\n" + "=" * 70)
    print("   ALL COMPLEX LIVE SANDBOX HUSTLE TESTS COMPLETED SUCCESSFULLY! 🎉   ")
    print("=" * 70)


if __name__ == "__main__":
    main()
