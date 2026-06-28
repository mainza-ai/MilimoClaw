"""Unit tests for HermesCredentialAdapter."""

import pytest
import subprocess
from unittest.mock import MagicMock, AsyncMock, patch
from milimo_core.hermes_credential_adapter import HermesCredentialAdapter


class TestHermesCredentialAdapter:
    """Tests for HermesCredentialAdapter."""

    def test_initialization(self):
        """Test adapter initialization."""
        adapter = HermesCredentialAdapter()

        # Should have OPENSHELL_PLACEHOLDERS class attribute
        assert hasattr(HermesCredentialAdapter, "OPENSHELL_PLACEHOLDERS")
        placeholders = HermesCredentialAdapter.OPENSHELL_PLACEHOLDERS
        assert "stripe" in placeholders
        assert "vercel" in placeholders
        assert "sentry" in placeholders
        assert "nvidia" in placeholders

    def test_get_github_token_from_gh_cli(self):
        """Test getting GitHub token from gh CLI."""
        adapter = HermesCredentialAdapter()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="gh_token_123\n",
                stderr="",
                returncode=0
            )

            token = HermesCredentialAdapter.get_github_token()

            assert token == "gh_token_123"
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "gh" in args[0]
            assert "auth" in args
            assert "token" in args

    def test_get_github_token_failure(self):
        """Test GitHub token failure handling."""
        adapter = HermesCredentialAdapter()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                returncode=1,
                cmd=["gh", "auth", "token"],
                stderr="not logged in"
            )

            with pytest.raises(RuntimeError) as exc_info:
                HermesCredentialAdapter.get_github_token()

            assert "Failed to get GitHub token" in str(exc_info.value)

    def test_get_github_token_gh_not_found(self):
        """Test GitHub token when gh CLI not found."""
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            with pytest.raises(RuntimeError) as exc_info:
                HermesCredentialAdapter.get_github_token()

            assert "gh CLI not found" in str(exc_info.value)

    def test_get_openshell_placeholder(self):
        """Test getting OpenShell placeholders."""
        stripe_placeholder = HermesCredentialAdapter.get_openshell_placeholder("stripe")
        vercel_placeholder = HermesCredentialAdapter.get_openshell_placeholder("vercel")
        sentry_placeholder = HermesCredentialAdapter.get_openshell_placeholder("sentry")
        nvidia_placeholder = HermesCredentialAdapter.get_openshell_placeholder("nvidia")
        unknown_placeholder = HermesCredentialAdapter.get_openshell_placeholder("unknown")

        assert stripe_placeholder == "STRIPE_API_KEY"
        assert vercel_placeholder == "VERCEL_TOKEN"
        assert sentry_placeholder == "SENTRY_AUTH_TOKEN"
        assert nvidia_placeholder == "NVIDIA_API_KEY"
        assert unknown_placeholder == ""

    def test_create_github_client(self):
        """Test creating GitHub client with Hermes credentials."""
        with patch.object(HermesCredentialAdapter, "get_github_token", return_value="test_token"):
            client = HermesCredentialAdapter.create_github_client()

            # Should return a GitHubClient instance
            assert client is not None

    def test_create_stripe_client(self):
        """Test creating Stripe client using OpenShell placeholder."""
        with patch("milimo_core.service_factory.create_stripe_client") as mock_create:
            client = HermesCredentialAdapter.create_stripe_client()
            mock_create.assert_called_once_with({})

    def test_create_vercel_client(self):
        """Test creating Vercel client using OpenShell placeholder."""
        with patch("milimo_core.service_factory.create_vercel_client") as mock_create:
            client = HermesCredentialAdapter.create_vercel_client()
            mock_create.assert_called_once_with({})

    def test_create_sentry_client(self):
        """Test creating Sentry client using OpenShell placeholder."""
        with patch("milimo_core.service_factory.create_sentry_client") as mock_create:
            client = HermesCredentialAdapter.create_sentry_client()
            mock_create.assert_called_once_with({})

    def test_create_nvidia_client(self):
        """Test creating NVIDIA client using OpenShell placeholder."""
        config = {"model": "test-model"}
        result = HermesCredentialAdapter.create_nvidia_client(config)

        # Returns the config as placeholder
        assert result == config
