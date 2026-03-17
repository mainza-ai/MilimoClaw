#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for the Milimo Claw Privacy Router.

Tests verify:
  - Policy loading from YAML and dict
  - Data type classification and routing decisions
  - Role-level overrides (Finance → always local-nim)
  - Locked route enforcement
  - Fallback behavior for unknown data types
  - Squad override validation
"""

import os
import sys
import unittest
from pathlib import Path

# Add parent directory to path so we can import the orchestrator
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.privacy_router import (
    InferenceBackend,
    PrivacyRouter,
    RoutingDecision,
)

# Path to the default privacy policy
POLICY_PATH = Path(__file__).parent.parent / "privacy_policy.yaml"


class TestPolicyLoading(unittest.TestCase):
    """Test that the privacy policy loads correctly."""

    def test_load_from_file(self):
        router = PrivacyRouter.from_policy_file(POLICY_PATH)
        self.assertIsNotNone(router.policy)
        self.assertEqual(router.policy.policy_version, "0.1.0")

    def test_load_from_dict(self):
        raw = {
            "policy_version": "0.1.0",
            "default_backend": "local-nim",
            "routes": [
                {
                    "data_type": "test_type",
                    "description": "Test route",
                    "backend": "cloud",
                    "locked": False,
                }
            ],
        }
        router = PrivacyRouter.from_dict(raw)
        self.assertEqual(len(router.policy.routes), 1)

    def test_default_backend_is_local_nim(self):
        router = PrivacyRouter.from_policy_file(POLICY_PATH)
        self.assertEqual(router.policy.default_backend, InferenceBackend.LOCAL_NIM)

    def test_policy_has_routes(self):
        router = PrivacyRouter.from_policy_file(POLICY_PATH)
        self.assertGreater(len(router.policy.routes), 0)

    def test_file_not_found_raises(self):
        with self.assertRaises(FileNotFoundError):
            PrivacyRouter.from_policy_file("/nonexistent/path.yaml")


class TestDataTypeRouting(unittest.TestCase):
    """Test routing decisions for specific data types."""

    @classmethod
    def setUpClass(cls):
        cls.router = PrivacyRouter.from_policy_file(POLICY_PATH)

    def test_public_drafts_route_to_cloud(self):
        decision = self.router.route(role="content", data_type="public_drafts")
        self.assertEqual(decision.backend, InferenceBackend.CLOUD)

    def test_client_communications_route_to_cloud(self):
        decision = self.router.route(role="ops", data_type="client_communications")
        self.assertEqual(decision.backend, InferenceBackend.CLOUD)

    def test_trend_research_routes_to_cloud(self):
        decision = self.router.route(role="analytics", data_type="trend_research")
        self.assertEqual(decision.backend, InferenceBackend.CLOUD)

    def test_market_analysis_routes_to_cloud(self):
        decision = self.router.route(role="analytics", data_type="market_analysis")
        self.assertEqual(decision.backend, InferenceBackend.CLOUD)

    def test_internal_comms_route_to_local_nim(self):
        decision = self.router.route(role="ops", data_type="internal_comms")
        self.assertEqual(decision.backend, InferenceBackend.LOCAL_NIM)

    def test_client_contacts_route_to_local_nim(self):
        decision = self.router.route(role="ops", data_type="client_contacts")
        self.assertEqual(decision.backend, InferenceBackend.LOCAL_NIM)

    def test_financial_records_route_to_local_nim(self):
        decision = self.router.route(role="finance", data_type="financial_records")
        self.assertEqual(decision.backend, InferenceBackend.LOCAL_NIM)

    def test_payment_details_route_to_local_nim(self):
        decision = self.router.route(role="finance", data_type="payment_details")
        self.assertEqual(decision.backend, InferenceBackend.LOCAL_NIM)

    def test_personal_notes_route_to_local_vllm(self):
        decision = self.router.route(role="content", data_type="personal_notes")
        self.assertEqual(decision.backend, InferenceBackend.LOCAL_VLLM)

    def test_credentials_route_to_local_vllm(self):
        decision = self.router.route(role="build", data_type="credentials")
        self.assertEqual(decision.backend, InferenceBackend.LOCAL_VLLM)

    def test_contract_review_routes_to_local_nim(self):
        decision = self.router.route(role="ops", data_type="contract_review")
        self.assertEqual(decision.backend, InferenceBackend.LOCAL_NIM)


class TestRoleOverrides(unittest.TestCase):
    """Test per-role override behavior."""

    @classmethod
    def setUpClass(cls):
        cls.router = PrivacyRouter.from_policy_file(POLICY_PATH)

    def test_finance_always_routes_to_local_nim(self):
        """Finance Claw: ALL inference must go local. No exceptions."""
        decision = self.router.route(role="finance", data_type="public_drafts")
        self.assertEqual(decision.backend, InferenceBackend.LOCAL_NIM)
        self.assertTrue(decision.was_overridden)

    def test_finance_overrides_cloud_routes(self):
        """Even cloud-routed data types get forced local for Finance."""
        cloud_types = ["public_drafts", "client_communications", "trend_research"]
        for dt in cloud_types:
            decision = self.router.route(role="finance", data_type=dt)
            self.assertEqual(
                decision.backend,
                InferenceBackend.LOCAL_NIM,
                f"Finance should force local-nim for {dt}",
            )

    def test_build_source_code_forced_local(self):
        """Build Claw: source code always stays local."""
        decision = self.router.route(role="build", data_type="source_code")
        self.assertEqual(decision.backend, InferenceBackend.LOCAL_NIM)
        self.assertTrue(decision.was_overridden)

    def test_build_production_logs_forced_local(self):
        decision = self.router.route(role="build", data_type="production_logs")
        self.assertEqual(decision.backend, InferenceBackend.LOCAL_NIM)
        self.assertTrue(decision.was_overridden)

    def test_build_boilerplate_can_use_cloud(self):
        """Build Claw: boilerplate is NOT in force_local_types → cloud OK."""
        decision = self.router.route(role="build", data_type="boilerplate")
        self.assertEqual(decision.backend, InferenceBackend.CLOUD)

    def test_content_no_override(self):
        """Content Claw has no role override — routes by data type."""
        decision = self.router.route(role="content", data_type="public_drafts")
        self.assertEqual(decision.backend, InferenceBackend.CLOUD)
        self.assertFalse(decision.was_overridden)


class TestFallback(unittest.TestCase):
    """Test fallback behavior for unknown data types."""

    @classmethod
    def setUpClass(cls):
        cls.router = PrivacyRouter.from_policy_file(POLICY_PATH)

    def test_unknown_data_type_falls_back_to_local_nim(self):
        decision = self.router.route(role="content", data_type="totally_unknown_type")
        self.assertEqual(decision.backend, InferenceBackend.LOCAL_NIM)

    def test_fallback_has_no_matched_rule(self):
        decision = self.router.route(role="ops", data_type="mystery_data")
        self.assertIsNone(decision.matched_rule)

    def test_fallback_reason_mentions_unclassified(self):
        decision = self.router.route(role="analytics", data_type="unknown_xyz")
        self.assertIn("unclassified", decision.reason.lower())


class TestLockedRoutes(unittest.TestCase):
    """Test locked route enforcement."""

    @classmethod
    def setUpClass(cls):
        cls.router = PrivacyRouter.from_policy_file(POLICY_PATH)

    def test_financial_records_is_locked(self):
        self.assertTrue(self.router.is_locked("financial_records"))

    def test_payment_details_is_locked(self):
        self.assertTrue(self.router.is_locked("payment_details"))

    def test_personal_notes_is_locked(self):
        self.assertTrue(self.router.is_locked("personal_notes"))

    def test_credentials_is_locked(self):
        self.assertTrue(self.router.is_locked("credentials"))

    def test_client_contacts_is_locked(self):
        self.assertTrue(self.router.is_locked("client_contacts"))

    def test_public_drafts_is_not_locked(self):
        self.assertFalse(self.router.is_locked("public_drafts"))

    def test_trend_research_is_not_locked(self):
        self.assertFalse(self.router.is_locked("trend_research"))

    def test_unknown_type_is_not_locked(self):
        self.assertFalse(self.router.is_locked("nonexistent"))


class TestSquadOverrideValidation(unittest.TestCase):
    """Test squad override validation."""

    @classmethod
    def setUpClass(cls):
        cls.router = PrivacyRouter.from_policy_file(POLICY_PATH)

    def test_locked_route_cannot_be_overridden(self):
        allowed, reason = self.router.validate_squad_override(
            "financial_records", "cloud"
        )
        self.assertFalse(allowed)
        self.assertIn("locked", reason.lower())

    def test_unlocked_route_can_be_overridden(self):
        allowed, reason = self.router.validate_squad_override(
            "public_drafts", "local-nim"
        )
        self.assertTrue(allowed)

    def test_unknown_type_can_be_added(self):
        allowed, reason = self.router.validate_squad_override(
            "new_custom_type", "cloud"
        )
        self.assertTrue(allowed)


class TestListRoutes(unittest.TestCase):
    """Test route listing utility."""

    @classmethod
    def setUpClass(cls):
        cls.router = PrivacyRouter.from_policy_file(POLICY_PATH)

    def test_list_routes_returns_all(self):
        routes = self.router.list_routes()
        self.assertGreater(len(routes), 10)

    def test_each_route_has_required_fields(self):
        for route in self.router.list_routes():
            self.assertIn("data_type", route)
            self.assertIn("backend", route)
            self.assertIn("locked", route)
            self.assertIn("description", route)

    def test_get_backend_for_finance(self):
        backend = self.router.get_backend_for_role("finance")
        self.assertEqual(backend, InferenceBackend.LOCAL_NIM)

    def test_get_backend_for_content_is_none(self):
        """Content has no forced backend."""
        backend = self.router.get_backend_for_role("content")
        self.assertIsNone(backend)


if __name__ == "__main__":
    unittest.main()
