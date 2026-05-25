#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
import time
import sys
import json
import uuid
import os
import shutil
from pathlib import Path

# Add orchestrator to python path so we can import orchestrator modules
sys.path.insert(0, "/sandbox/.openclaw/milimo/milimo-blueprint/orchestrator")
sys.path.insert(0, "/sandbox/.openclaw/milimo/milimo-blueprint")

from orchestrator.contracts import ClawMessage, ContractValidator
from orchestrator.mesh import MeshCoordinator
from orchestrator.milimo_paths import mesh_dir as milimo_mesh_dir
from orchestrator.assistant.lucy import LucyAssistant, ProcessMilestone, ActiveProcessTrack

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
        print(f"  [Spy Send] To {recipient_role}: type={message_type}, payload={payload}")
        return result.delivered

def clean_processed_directories(mesh_dir_path):
    print(">>> Cleaning historical processed message queues for test isolation...")
    for role in ["content", "ops", "analytics", "finance", "build", "assistant"]:
        processed_dir = mesh_dir_path / "inbox" / role / "processed"
        if processed_dir.exists():
            for f in processed_dir.glob("*.json"):
                try:
                    f.unlink()
                except Exception as e:
                    print(f"  Failed to delete {f}: {e}")

    # Clean historical events
    events_dir = Path("/sandbox/.openclaw/milimo/events")
    if events_dir.exists():
        for f in events_dir.glob("action_*.json"):
            try:
                f.unlink()
            except Exception:
                pass

def main():
    print("======================================================================")
    print("    STARTING LUCY ACTIVE PROCESS SUPERVISION INTEGRATION TEST 🦀    ")
    print("======================================================================\n")

    os.environ["MILIMO_TEST_MODE"] = "true"
    os.environ["ANALYTICS_WAIT_SECONDS"] = "1"

    # 1. Initialize mesh
    _mesh_dir = milimo_mesh_dir()

    # Clean processed dirs and events
    clean_processed_directories(_mesh_dir)

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

    # Step 1: Simulate operator message requesting scoping
    print(">>> [STEP 1] Simulating operator message targeted to Ops to create scope...")
    operator_text = "@ops create scope for stripe-billing"
    track_id = lucy.process_operator_message(operator_text)
    print(f"  ✓ Processed message. Spawning Process Track ID: {track_id}")

    # Check that process track is registered
    track = lucy._pending_tracks.get(track_id)
    if not track:
        print("  [ERROR] ActiveProcessTrack not registered in Lucy.")
        sys.exit(1)

    print("  ✓ Track verified!")
    print(f"    - Original Task: \"{track.original_task}\"")
    print(f"    - Milestones: {[m.step_name for m in track.milestones]}")
    print(f"    - Current Milestone: {track.current_milestone.step_name}")

    # Step 2: Transition Milestone 0 ("Ops Task Receipt")
    print("\n>>> [STEP 2] Simulating Ops Claw receiving and processing the task (Milestone 0)...")
    ops_processed_dir = _mesh_dir / "inbox" / "ops" / "processed"
    ops_processed_dir.mkdir(parents=True, exist_ok=True)

    msg_0 = {
        "message_id": track_id,
        "message_type": "assistant_task",
        "sender_role": "assistant",
        "recipient_role": "ops",
        "timestamp": "2026-05-24T21:00:00Z",
        "payload": {
            "task_description": "create scope for stripe-billing",
            "query_id": track_id
        }
    }
    (ops_processed_dir / f"{track_id}.json").write_text(json.dumps(msg_0))

    # Supervise active tracks to transition milestone 0
    lucy.supervise_active_tracks()

    print(f"  Current Milestone after supervision: {track.current_milestone.step_name}")
    if track.milestones[0].status != "completed":
        print("  [ERROR] Milestone 0 did not transition to completed.")
        sys.exit(1)
    print("  ✓ Milestone 0 transition verified!")

    # Step 3: Transition Milestone 1 ("Finance Pricing Query")
    print("\n>>> [STEP 3] Simulating Ops Claw sending pricing_query to Finance (Milestone 1)...")
    finance_processed_dir = _mesh_dir / "inbox" / "finance" / "processed"
    finance_processed_dir.mkdir(parents=True, exist_ok=True)

    msg_1 = {
        "message_id": "pricing_query_" + uuid.uuid4().hex[:6],
        "message_type": "pricing_query",
        "sender_role": "ops",
        "recipient_role": "finance",
        "timestamp": "2026-05-24T21:05:00Z",
        "payload": {
            "query_id": track_id,
            "project_id": track_id
        }
    }
    (finance_processed_dir / f"{msg_1['message_id']}.json").write_text(json.dumps(msg_1))

    # Supervise active tracks to transition milestone 1
    lucy.supervise_active_tracks()

    print(f"  Current Milestone after supervision: {track.current_milestone.step_name}")
    if track.milestones[1].status != "completed":
        print("  [ERROR] Milestone 1 did not transition to completed.")
        sys.exit(1)
    print("  ✓ Milestone 1 transition verified!")

    # Step 4: Simulate a STALL on Milestone 2 ("Finance Pricing Response")
    print("\n>>> [STEP 4] Simulating STALL / Timeout on Milestone 2 (Finance Pricing Response)...")
    track.started_at = time.time() - 100  # Timeout threshold is 15s in test mode
    track.milestones[1].completed_at = time.time() - 100

    # Clean previous log file if it exists to verify new log lines
    supervision_log = base_path / "logs" / "supervision.log"
    if supervision_log.exists():
        supervision_log.unlink()

    # Clear gateway spy sent messages
    spy_gateway.sent_messages.clear()

    # Run supervision which should trigger stall warnings
    lucy.supervise_active_tracks()

    # 1. Assert that Lucy logged/wrote conversational warning to local supervision.log
    if not supervision_log.exists():
        print("  [ERROR] Lucy did not write conversational alert to local supervision.log.")
        sys.exit(1)

    log_content = supervision_log.read_text()
    print("  ✓ supervision.log exists! Content:")
    print("----------------------------------------------------------------------")
    print(log_content.strip())
    print("----------------------------------------------------------------------")

    if "STALL DETECTED" not in log_content:
        print("  [ERROR] 'STALL DETECTED' not found in supervision.log.")
        sys.exit(1)
    print("  ✓ Conversational warning verified in log!")

    # 2. Assert that Lucy dispatched a diagnostic inquiry to the stalled claw (finance)
    diagnostic_inquiries = [msg for msg in spy_gateway.sent_messages if msg.message_type == "assistant_query" and msg.payload.get("query") == "diagnostics"]
    if not diagnostic_inquiries:
        print("  [ERROR] Lucy did not send a diagnostic query to the stalled claw.")
        sys.exit(1)

    print(f"  ✓ Diagnostic query verified in gateway dispatch!")
    print(f"    - Sender: {diagnostic_inquiries[0].sender_role}")
    print(f"    - Recipient: {diagnostic_inquiries[0].recipient_role}")
    print(f"    - Payload: {diagnostic_inquiries[0].payload}")

    # 3. Assert that Lucy injected high-priority HOLD alert into the War Room TUI
    # Let's inspect events dir under /sandbox/.openclaw/milimo/events/ to verify the queued action event
    events_dir = Path("/sandbox/.openclaw/milimo/events")
    if not events_dir.exists():
        events_dir = Path(os.path.expanduser("~/.milimo/events"))

    if not events_dir.exists():
        print(f"  [ERROR] events directory was not created. Checked: {events_dir}")
        sys.exit(1)

    found_stall_event = False
    for f in events_dir.glob("action_*.json"):
        try:
            data = json.loads(f.read_text())
            if data.get("type") == "action_queued" and data.get("data", {}).get("action_type") == "supervision_stall":
                found_stall_event = True
                break
        except Exception:
            pass

    if not found_stall_event:
        print("  [ERROR] 'supervision_stall' action event not found in events directory.")
        sys.exit(1)

    print("  ✓ War Room HOLD alert successfully verified in TUI event database!")

    print("\n======================================================================")
    print("     ALL STATEFUL ACTIVE SUPERVISION TEST CASES PASSED WITH LUCY 🦀     ")
    print("======================================================================\n")

if __name__ == "__main__":
    main()
