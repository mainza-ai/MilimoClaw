# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for the Milimo Claw v3.0 Attestation Sandbox Orchestrator.
"""

import sys
import unittest
from pathlib import Path

# Add parent directory to path so we can import the orchestrator
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.attestation_runner import AttestationRunner


class TestAttestationRunner(unittest.TestCase):
    """Test suite for the ephemeral sandbox runner and attestation badges."""

    def setUp(self) -> None:
        self.runner = AttestationRunner(
            base_dir=Path("/tmp/milimo-attestation-test"),
            signing_secret="test-platform-secret",
        )

    def test_spawn_ephemeral_sandbox(self) -> None:
        """Verifies sandbox creation parameters and Landlock/preflight statuses."""
        sandbox = self.runner.spawn_ephemeral_sandbox("ops-optimized-blueprint")

        self.assertIsNotNone(sandbox["sandbox_name"])
        self.assertIn("attestation-sandbox-", sandbox["sandbox_name"])
        self.assertTrue(sandbox["landlock_enforced"])
        self.assertEqual(sandbox["cgroup_mode"], "host")

    def test_execute_backtest_workload(self) -> None:
        """Verifies that E2E workload simulation records accuracy and latency metrics."""
        metrics = self.runner.execute_backtest_workload(
            "ops-optimized-blueprint", cycles=50
        )

        self.assertEqual(metrics["blueprint"], "ops-optimized-blueprint")
        self.assertEqual(metrics["cycles_total"], 50)
        self.assertGreater(metrics["cycles_successful"], 0)
        self.assertLessEqual(metrics["cycles_successful"], 50)
        self.assertGreater(metrics["accuracy_score"], 0.80)
        self.assertGreater(metrics["token_efficiency_score"], 0.0)
        self.assertGreater(metrics["cpu_usage_pct"], 0.0)

    def test_generate_attestation_badge(self) -> None:
        """Verifies cryptographic signature generation and deterministic serializations."""
        metrics = self.runner.execute_backtest_workload(
            "finance-hardened-blueprint", cycles=100
        )
        badge = self.runner.generate_attestation_badge(metrics)

        self.assertEqual(badge["schema_version"], "1.0.0")
        self.assertEqual(badge["issuer"], "Milimo Marketplace Attestation Engine")
        self.assertEqual(badge["verified_metrics"], metrics)

        attestation = badge["attestation_badge"]
        self.assertEqual(attestation["status"], "Verified")
        self.assertEqual(attestation["algorithm"], "HMAC-SHA256")

        # Verify signature length (Hex encoded SHA256 is 64 chars)
        self.assertEqual(len(attestation["signature"]), 64)
        self.assertEqual(len(attestation["badge_id"]), 16)

    def test_deterministic_signing(self) -> None:
        """Asserts that identical metrics compute identical signatures."""
        metrics_1 = {
            "blueprint": "content-squad-v2",
            "cycles_total": 100,
            "accuracy_score": 0.98,
            "token_efficiency_score": 124.5,
        }

        metrics_2 = {
            "blueprint": "content-squad-v2",
            "cycles_total": 100,
            "accuracy_score": 0.98,
            "token_efficiency_score": 124.5,
        }

        badge_1 = self.runner.generate_attestation_badge(metrics_1)
        badge_2 = self.runner.generate_attestation_badge(metrics_2)

        self.assertEqual(
            badge_1["attestation_badge"]["signature"],
            badge_2["attestation_badge"]["signature"],
        )


if __name__ == "__main__":
    unittest.main()
