#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
import time
import sys
import json
import uuid
from pathlib import Path

# Add orchestrator to python path so we can import orchestrator modules
sys.path.insert(0, "/sandbox/.openclaw/milimo/milimo-blueprint/orchestrator")
sys.path.insert(0, "/sandbox/.openclaw/milimo/milimo-blueprint")

from orchestrator.contracts import ClawMessage, ContractValidator
from orchestrator.mesh import MeshCoordinator
from orchestrator.milimo_paths import mesh_dir as milimo_mesh_dir
from orchestrator.assistant.lucy import LucyAssistant

class GatewayAdapterSpy:
    """Mock/spy gateway that matches LucyAssistant's mesh_gateway expected send interface."""
    def __init__(self, mesh: MeshCoordinator, squad_id: str):
        self._mesh = mesh
        self._squad_id = squad_id
        self.sent_messages = []

    def send(
        self,
        message_type: str,
        recipient_role: str,
        sender_role: str,
        payload: dict,
        message_id: str,
        timestamp: str,
    ) -> bool:
        msg = ClawMessage(
            sender_role=sender_role,
            recipient_role=recipient_role,
            message_type=message_type,
            payload=payload,
            squad_id=self._squad_id,
            message_id=message_id,
            timestamp=timestamp,
        )
        self.sent_messages.append(msg)
        result = self._mesh.send_message(msg)
        print(f"  [DEBUG] Spy Gateway Send to {recipient_role}: type={message_type}, delivered={result.delivered}, reason={result.reason}")
        return result.delivered

def main():
    print("======================================================================")
    print("      STARTING COMPLEX MULTI-CLAW INTEGRATION TEST WITH LUCY 🦀      ")
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

    # Register claws
    for role in ["content", "ops", "analytics", "finance", "build", "assistant"]:
        mesh.register_claw(role, address=f"local://{role}")
        mesh.set_status(role, "online")

    # Instantiate spy gateway and Lucy
    spy_gateway = GatewayAdapterSpy(mesh, "zulu")
    inbox_dir = _mesh_dir / "inbox" / "assistant"
    base_path = Path("/sandbox/.openclaw/milimo/claws/assistant")

    lucy = LucyAssistant(
        squad_id="zulu",
        mesh_gateway=spy_gateway,
        inbox_dir=inbox_dir,
        base_path=base_path
    )
    lucy.startup()

    def find_message(inbox_dir, message_type, project_id=None, query_id=None):
        """Helper to scan both active inbox and processed queue for a given message type and id."""
        dirs = [inbox_dir]
        processed = inbox_dir / "processed"
        if processed.exists():
            dirs.append(processed)

        for d in dirs:
            for f in d.glob("*.json"):
                try:
                    data = json.loads(f.read_text())
                    if data.get("message_type") != message_type:
                        continue
                    payload = data.get("payload", {})
                    if project_id:
                        if payload.get("project_id") == project_id or payload.get("query_id") == project_id or data.get("message_id") == project_id:
                            return f, data
                    elif query_id:
                        if data.get("message_id") == query_id or payload.get("query_id") == query_id or payload.get("original_message_id") == query_id:
                            return f, data
                    else:
                        return f, data
                except Exception:
                    pass
        return None, None

    # ----------------------------------------------------------------------
    # SCENARIO A: Operator Message Parsing & Targeted Routing
    # ----------------------------------------------------------------------
    print(">>> [SCENARIO A] Simulating operator message targeted to Ops Claw...")
    operator_text = "@ops create scope for stripe-checkout-flow project"
    print(f"  Operator Input: \"{operator_text}\"")

    query_id = lucy.process_operator_message(operator_text)
    print(f"  ✓ Lucy processed query. Dispatched Query ID: {query_id}")

    # Verify Lucy sent an assistant_task message which lands in Ops Claw's inbox (or is processed immediately)
    print("  Checking Ops Claw inbox or processed queue for the assistant_task message...")
    ops_inbox_dir = _mesh_dir / "inbox" / "ops"
    time.sleep(2)  # Give local file system a brief moment

    task_file, task_data = find_message(ops_inbox_dir, "assistant_task", query_id=query_id)
    if not task_file:
        print("  [ERROR] assistant_task message was not delivered/processed in Ops Claw's queue.")
        sys.exit(1)

    print("  ✓ assistant_task successfully verified in Ops' inbox queue!")
    print(f"    - Sender: {task_data.get('sender_role')}")
    print(f"    - Type: {task_data.get('message_type')}")
    print(f"    - Task Description: {task_data.get('payload', {}).get('task_description')}\n")

    # ----------------------------------------------------------------------
    # SCENARIO B: Ops to Finance Scoping & Pricing Estimate Pipeline
    # ----------------------------------------------------------------------
    print(">>> [SCENARIO B] Simulating Ops Claw sending pricing_query to Finance Claw...")
    pricing_msg = ClawMessage(
        sender_role="ops",
        recipient_role="finance",
        message_type="pricing_query",
        payload={
            "project_id": "proj-100",
            "scope_description": "Scoping out stripe checkout flow and webhook subscriptions",
            "complexity_estimate": "medium",
            "deadline": "2026-06-30T12:00:00Z"
        },
        squad_id="zulu"
    )

    delivery = mesh.send_message(pricing_msg)
    if not delivery.delivered:
        print(f"  [ERROR] pricing_query not delivered: {delivery.reason}")
        sys.exit(1)
    print(f"  ✓ pricing_query {pricing_msg.message_id} delivered to Finance's inbox.")

    print("  Waiting for Finance Claw background runner to process the query (max 15s)...")
    start_time = time.time()
    pricing_response_msg = None

    while time.time() - start_time < 15:
        _, data = find_message(ops_inbox_dir, "pricing_response", project_id="proj-100")
        if data:
            pricing_response_msg = data
            break
        time.sleep(1)

    if not pricing_response_msg:
        print("  [ERROR] Did not receive pricing_response from Finance Claw in time.")
        sys.exit(1)

    print("  ✓ Received pricing_response from Finance Claw!")
    payload = pricing_response_msg["payload"]
    floor = payload.get("floor_price") if payload.get("floor_price") is not None else payload.get("floor")
    ceiling = payload.get("ceiling_price") if payload.get("ceiling_price") is not None else payload.get("ceiling")
    notes = payload.get("scope_notes") or payload.get("notes")
    print(f"    - Floor Price Estimate: ${floor}")
    print(f"    - Ceiling Price Estimate: ${ceiling}")
    print(f"    - Pricing Notes: {notes}\n")

    # ----------------------------------------------------------------------
    # SCENARIO C: Ops to Build Technical Sprint Briefing Pipeline
    # ----------------------------------------------------------------------
    print(">>> [SCENARIO C] Simulating Ops Claw sending feature_brief to Build Claw...")
    feature_msg = ClawMessage(
        sender_role="ops",
        recipient_role="build",
        message_type="feature_brief",
        payload={
            "project_id": "proj-100",
            "feature_name": "stripe-billing",
            "description": "Stripe checkout and billing sync components"
        },
        squad_id="zulu"
    )

    delivery = mesh.send_message(feature_msg)
    if not delivery.delivered:
        print(f"  [ERROR] feature_brief not delivered: {delivery.reason}")
        sys.exit(1)
    print(f"  ✓ feature_brief {feature_msg.message_id} delivered to Build's inbox.")

    print("  Waiting for Build Claw to process and acknowledge the feature brief (max 15s)...")
    start_time = time.time()
    ack_msg = None

    while time.time() - start_time < 15:
        _, data = find_message(ops_inbox_dir, "feature_brief_acknowledged", project_id="proj-100")
        if data:
            ack_msg = data
            break
        time.sleep(1)

    if not ack_msg:
        print("  [ERROR] Did not receive feature_brief_acknowledged from Build Claw in time.")
        sys.exit(1)

    print("  ✓ Received feature_brief_acknowledged from Build Claw!")
    print(f"    - Status: {ack_msg['payload'].get('status')}")
    print(f"    - Message: {ack_msg['payload'].get('message')}\n")

    # ----------------------------------------------------------------------
    # SCENARIO D: Worker Response Harvesting & Consolidation
    # ----------------------------------------------------------------------
    print(">>> [SCENARIO D] Simulating Ops Claw returning assistant_response to Lucy...")

    # Construct assistant_response message from Ops back to Lucy
    response_payload = {
        "original_message_id": query_id,
        "response": {
            "status": "completed",
            "action": "stripe_scoping_complete",
            "project_id": "proj-100",
            "estimated_floor": floor,
            "estimated_ceiling": ceiling,
            "sprint_acknowledged": True,
            "deliverables": ["stripe-checkout-flow", "webhook-listener"]
        }
    }

    response_msg = ClawMessage(
        sender_role="ops",
        recipient_role="assistant",
        message_type="assistant_response",
        payload=response_payload,
        squad_id="zulu"
    )

    # Deliver to Lucy's inbox
    delivery = mesh.send_message(response_msg)
    if not delivery.delivered:
        print(f"  [ERROR] assistant_response not delivered to Lucy's inbox: {delivery.reason}")
        sys.exit(1)
    print("  ✓ assistant_response successfully queued in Lucy's inbox.")

    # Call handle_inbound directly simulating Lucy polling her inbox
    print("  Lucy is harvesting the inbound message...")
    time.sleep(1)

    raw_response = {
        "sender_role": "ops",
        "recipient_role": "assistant",
        "message_type": "assistant_response",
        "payload": response_payload,
        "message_id": response_msg.message_id
    }

    inbound_result = lucy.handle_inbound(raw_response)
    print("  ✓ handle_inbound execution completed.")

    # Verify query status and consolidation
    pending = lucy._pending.get(query_id)
    if not pending:
        print("  [ERROR] Query ID not found in Lucy's pending registry.")
        sys.exit(1)

    print(f"    - Pending Responded State: {pending.responded}")
    print(f"    - Is Complete: {pending.is_complete}")

    consolidated = inbound_result.get("consolidated")
    if not consolidated:
        print("  [ERROR] Lucy did not generate a consolidated digest.")
        sys.exit(1)

    print("\n======================================================================")
    print("                LUCY CONSOLIDATED OPERATOR REPORT                    ")
    print("======================================================================")
    print(f"Query ID: {consolidated.get('query_id')}")
    print(f"Original Text: \"{consolidated.get('original_text')}\"")
    print("Claw Responses:")
    for role, summary in consolidated.get("responses", {}).items():
        print(f"  [{role.upper()}]: {summary}")
    print("======================================================================\n")

    print("======================================================================")
    print("     ALL COMPLEX MULTI-CLAW INTEGRATION TESTS PASSED WITH LUCY 🦀     ")
    print("======================================================================\n")

if __name__ == "__main__":
    main()
