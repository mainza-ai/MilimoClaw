# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Tests for StripeClient CLI argument isolation and direct API fallback."""

from unittest.mock import patch, MagicMock
from orchestrator.finance.stripe_client import StripeClient


def test_stripe_client_key_env_injection():
    """Verify that StripeClient passes the secret key via environment dictionary, not command line argv."""
    client = StripeClient(api_key="sk_test_mock_12345")

    with patch("subprocess.run") as mock_sub_run:
        # Mock Stripe CLI to appear pre-installed
        mock_ver = MagicMock()
        mock_ver.returncode = 0
        mock_ver.stdout = "stripe version 1.18.0"

        mock_cmd = MagicMock()
        mock_cmd.returncode = 0
        mock_cmd.stdout = '{"id": "inv_123"}'

        mock_sub_run.side_effect = [mock_ver, mock_cmd]

        res = client._stripe_cli("invoices", "create")

        assert res == {"id": "inv_123"}
        assert mock_sub_run.call_count == 2

        # Check command arguments of the second call (the invoice create call)
        cmd_args = mock_sub_run.call_args_list[1][0][0]
        # Assert --api-key is NOT passed in the command line args list
        assert "--api-key" not in cmd_args
        assert "sk_test_mock_12345" not in cmd_args

        # Assert STRIPE_API_KEY is present in the env dict passed to subprocess
        passed_env = mock_sub_run.call_args_list[1][1].get("env", {})
        assert passed_env.get("STRIPE_API_KEY") == "sk_test_mock_12345"


def test_stripe_client_direct_api_fallback():
    """Verify that StripeClient falls back to direct API requests using authorization headers when CLI is absent."""
    client = StripeClient(api_key="sk_test_mock_67890")

    with patch("subprocess.run", side_effect=FileNotFoundError):
        # Mock urlopen to simulate Stripe API response
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b'{"id": "cust_abc", "object": "customer"}'
            mock_urlopen.return_value.__enter__.return_value = mock_resp

            res = client._stripe_api(
                "POST", "/customers", data={"email": "test@example.com"}
            )

            assert res == {"id": "cust_abc", "object": "customer"}
            assert mock_urlopen.call_count == 1

            # Verify request headers include Authorization Bearer key
            req_arg = mock_urlopen.call_args[0][0]
            assert req_arg.get_header("Authorization") == "Bearer sk_test_mock_67890"
