# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for the Milimo Claw v3.0 Failover Inference Broker.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

# Add parent directory to path so we can import the orchestrator
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.failover_broker import FailoverInferenceBroker
from orchestrator.privacy_router import PrivacyRouter, InferenceBackend

POLICY_PATH = Path(__file__).parent.parent / "privacy_policy.yaml"


class TestFailoverInferenceBroker(unittest.TestCase):
    """Test the failover broker metrics and CLI execution loops."""

    def setUp(self) -> None:
        self.broker = FailoverInferenceBroker(
            local_endpoint="http://localhost:8000/v1/models",
            latency_threshold_ms=800.0,
            cloud_model="nvidia/nemotron-3-super-120b-a12b",
        )
        if "NEMOCLAW_MODEL" in os.environ:
            del os.environ["NEMOCLAW_MODEL"]

    def tearDown(self) -> None:
        if "NEMOCLAW_MODEL" in os.environ:
            del os.environ["NEMOCLAW_MODEL"]

    @patch("urllib.request.urlopen")
    def test_ping_success_low_latency(self, mock_urlopen) -> None:
        """Low latency should return a valid float and not trigger failover."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        latency = self.broker.ping_local_backend()
        self.assertLess(latency, float("inf"))

        is_failed = self.broker.evaluate_and_route()
        self.assertFalse(is_failed)
        self.assertFalse(self.broker.is_failed_over)
        self.assertNotIn("NEMOCLAW_MODEL", os.environ)

    @patch("urllib.request.urlopen")
    @patch("subprocess.run")
    def test_ping_success_high_latency_failover(self, mock_run, mock_urlopen) -> None:
        """High latency triggers openshell CLI set and NEMOCLAW_MODEL overrides."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Mock subproces run to return success
        mock_run.return_value = MagicMock(returncode=0)

        # Force high latency by mock side-effect delay
        with patch("time.perf_counter", side_effect=[0.0, 1.0]):  # 1000.0 ms
            is_failed = self.broker.evaluate_and_route()
            self.assertTrue(is_failed)
            self.assertTrue(self.broker.is_failed_over)
            self.assertEqual(os.environ.get("NEMOCLAW_MODEL"), self.broker.cloud_model)

            # Assert subprocess run is called with correct arguments
            mock_run.assert_called_with(
                [
                    "openshell",
                    "inference",
                    "set",
                    "--provider",
                    "nvidia-nim",
                    "--model",
                    self.broker.cloud_model,
                ],
                capture_output=True,
                text=True,
                check=False,
            )

    @patch("urllib.request.urlopen", side_effect=Exception("Connection refused"))
    @patch("subprocess.run")
    def test_ping_failure_triggers_failover(self, mock_run, mock_urlopen) -> None:
        """Total connection failure triggers automatic cloud routing."""
        mock_run.return_value = MagicMock(returncode=0)

        is_failed = self.broker.evaluate_and_route()
        self.assertTrue(is_failed)
        self.assertTrue(self.broker.is_failed_over)
        self.assertEqual(os.environ.get("NEMOCLAW_MODEL"), self.broker.cloud_model)

    @patch("urllib.request.urlopen")
    @patch("subprocess.run")
    def test_recovery_restores_local(self, mock_run, mock_urlopen) -> None:
        """Low latency after a failover restores local edge paths."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response
        mock_run.return_value = MagicMock(returncode=0)

        # 1. Force a failover
        with patch("time.perf_counter", side_effect=[0.0, 1.0]):
            self.broker.evaluate_and_route()
            self.assertTrue(self.broker.is_failed_over)

        # 2. Trigger evaluation with low latency
        with patch("time.perf_counter", side_effect=[0.0, 0.01]):  # 10ms
            is_failed = self.broker.evaluate_and_route()
            self.assertFalse(is_failed)
            self.assertFalse(self.broker.is_failed_over)
            self.assertNotIn("NEMOCLAW_MODEL", os.environ)
            mock_run.assert_any_call(
                [
                    "openshell",
                    "inference",
                    "set",
                    "--provider",
                    "openai",
                    "--model",
                    "local-edge",
                ],
                capture_output=True,
                text=True,
                check=False,
            )


class TestPrivacyRouterFailoverIntegration(unittest.TestCase):
    """Test dynamic latency interception when querying the PrivacyRouter."""

    def setUp(self) -> None:
        self.mock_broker = MagicMock()
        self.router = PrivacyRouter.from_policy_file(
            POLICY_PATH, failover_broker=self.mock_broker
        )

    def test_route_local_without_failover(self) -> None:
        """When local edge is healthy, request is resolved normally."""
        self.mock_broker.evaluate_and_route.return_value = False

        # 'credentials' routes to LOCAL_VLLM under normal policy
        decision = self.router.route(role="build", data_type="credentials")
        self.assertEqual(decision.backend, InferenceBackend.LOCAL_VLLM)
        self.assertFalse(decision.was_overridden)

    def test_route_local_with_failover(self) -> None:
        """When edge is degraded, local requests are dynamically intercepted to CLOUD."""
        self.mock_broker.evaluate_and_route.return_value = True

        # 'credentials' routes to LOCAL_VLLM under normal policy
        decision = self.router.route(role="build", data_type="credentials")

        # Intercepted and routed to Cloud backend
        self.assertEqual(decision.backend, InferenceBackend.CLOUD)
        self.assertTrue(decision.was_overridden)
        self.assertIn("Auto Broker", decision.reason)

    def test_route_cloud_unaffected_by_failover(self) -> None:
        """Requests that are cloud-by-default remain untouched."""
        self.mock_broker.evaluate_and_route.return_value = True

        # 'public_drafts' routes to CLOUD under normal policy
        decision = self.router.route(role="content", data_type="public_drafts")
        self.assertEqual(decision.backend, InferenceBackend.CLOUD)
        self.assertFalse(decision.was_overridden)


if __name__ == "__main__":
    unittest.main()
