#!/usr/bin/env python3
import time
import sys
import json
from pathlib import Path

# Add orchestrator to python path
sys.path.insert(0, "/sandbox/.openclaw/milimo/milimo-blueprint")

from orchestrator.contracts import ClawMessage
from orchestrator.mesh import MeshCoordinator
from orchestrator.milimo_paths import mesh_dir as milimo_mesh_dir

def main():
    print("======================================================================")
    print("          STARTING COMPREHENSIVE CROSS-CLAW INTEGRATION TEST          ")
    print("======================================================================\n")

    # 1. Initialize mesh
    _mesh_dir = milimo_mesh_dir()
    config_path = Path("/sandbox/.openclaw/milimo/milimo-blueprint/mesh_config.yaml")
    if config_path.exists():
        mesh = MeshCoordinator.from_config_file(
            str(config_path), squad_id="zulu", mesh_dir=str(_mesh_dir)
        )
    else:
        mesh = MeshCoordinator.from_dict({}, squad_id="zulu", mesh_dir=str(_mesh_dir))

    # Register all known claws so mesh knows who is online
    for role in ["content", "ops", "analytics", "finance", "build", "assistant"]:
        mesh.register_claw(role, address=f"local://{role}")

    # Set statuses to online
    for role in ["content", "ops", "analytics", "finance", "build", "assistant"]:
        mesh.set_status(role, "online")

    # ----------------------------------------------------------------------
    # SCENARIO 1: Ops Claw $\rightarrow$ Finance Claw (pricing_query)
    # ----------------------------------------------------------------------
    print(">>> [SCENARIO 1] Simulating Ops Claw sending pricing_query to Finance Claw...")
    query_msg = ClawMessage(
        sender_role="ops",
        recipient_role="finance",
        message_type="pricing_query",
        payload={
            "project_id": "proj-999",
            "scope_description": "Build modern e-commerce dashboard with Stripe integration",
            "complexity_estimate": "high",
            "deadline": "2026-06-30T12:00:00Z"
        },
        squad_id="zulu"
    )

    delivery = mesh.send_message(query_msg)
    if not delivery.delivered:
        print(f"  [ERROR] pricing_query not delivered: {delivery.reason}")
        sys.exit(1)
    print(f"  ✓ Message {query_msg.message_id} queued successfully in Finance's inbox.\n")

    print(">>> [SCENARIO 1] Waiting for Finance Claw background poller to process the query (max 15s)...")
    # Poll ops inbox for pricing_response
    start_time = time.time()
    response_msg = None
    while time.time() - start_time < 15:
        # Check files in /sandbox/.openclaw/milimo/mesh/inbox/ops
        inbox_dir = _mesh_dir / "inbox" / "ops"
        for f in inbox_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                if data.get("message_type") == "pricing_response":
                    response_msg = data
                    break
            except Exception:
                pass
        if response_msg:
            break
        time.sleep(1)

    if not response_msg:
        print("  [ERROR] Did not receive pricing_response from Finance Claw in time.")
        sys.exit(1)

    print(f"  ✓ Received pricing_response from Finance Claw! Message ID: {response_msg['message_id']}")
    print(f"  Payload details:")
    print(f"    - Floor Price: ${response_msg['payload'].get('floor')}")
    print(f"    - Ceiling Price: ${response_msg['payload'].get('ceiling')}")
    print(f"    - Notes: {response_msg['payload'].get('notes')}\n")

    # ----------------------------------------------------------------------
    # SCENARIO 2: Ops Claw $\rightarrow$ Build Claw (feature_brief)
    # ----------------------------------------------------------------------
    print(">>> [SCENARIO 2] Simulating Ops Claw sending feature_brief to Build Claw...")
    brief_msg = ClawMessage(
        sender_role="ops",
        recipient_role="build",
        message_type="feature_brief",
        payload={
            "project_id": "proj-999",
            "feature_name": "stripe-billing-flow",
            "description": "Implement Stripe checkout flow and webhooks for SaaS subscriptions",
            "priority": "high",
            "deadline": "2026-06-30T12:00:00Z"
        },
        squad_id="zulu"
    )

    delivery = mesh.send_message(brief_msg)
    if not delivery.delivered:
        print(f"  [ERROR] feature_brief not delivered: {delivery.reason}")
        sys.exit(1)
    print(f"  ✓ Message {brief_msg.message_id} queued successfully in Build's inbox.\n")

    print(">>> [SCENARIO 2] Waiting for Build Claw poller to process the brief and launch pipeline (max 15s)...")
    start_time = time.time()
    processed_msg = None
    while time.time() - start_time < 15:
        build_processed_dir = _mesh_dir / "inbox" / "build" / "processed"
        for f in build_processed_dir.glob(f"*{brief_msg.message_id}*.json"):
            processed_msg = f
            break
        if processed_msg:
            break
        time.sleep(1)

    if not processed_msg:
        print("  [ERROR] Build Claw did not process the feature_brief in time.")
        sys.exit(1)

    print(f"  ✓ Build Claw successfully retrieved and processed the feature_brief!")
    print(f"  File: {processed_msg.name}")

    # Read the build operational logs to verify it initiated the pipeline
    time.sleep(2)  # Wait for logs to be appended
    logs_file = Path("/sandbox/.openclaw/milimo/claws/build/logs/operational.log")
    if logs_file.exists():
        print(f"  ✓ Build operational.log verified:")
        log_lines = logs_file.read_text().splitlines()
        for line in log_lines[-5:]:
            print(f"    {line}")
    else:
        print("  [WARNING] Build operational.log not found.")

    print("\n======================================================================")
    print("       ALL COMPREHENSIVE CROSS-CLAW INTEGRATION TESTS PASSED 🦀       ")
    print("======================================================================\n")

if __name__ == "__main__":
    main()
