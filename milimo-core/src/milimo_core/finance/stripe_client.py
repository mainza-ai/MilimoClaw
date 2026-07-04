# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Stripe Client

Wraps the Stripe CLI for payment processing, invoice management,
and webhook handling. Falls back to direct Stripe API calls via
subprocess when the Python SDK is not available.

Environment variables:
    STRIPE_API_KEY — Secret key for Stripe API
    STRIPE_WEBHOOK_SECRET — Webhook signing secret
    STRIPE_CURRENCY — Default currency (default: usd)
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("milimo.finance.stripe_client")


class StripeClient:
    """
    Stripe client wrapping the Stripe CLI for payment operations.

    Provides methods for:
    - Creating and sending invoices
    - Processing payments
    - Checking payment status
    - Managing customers
    - Handling webhooks
    """

    def __init__(
        self,
        api_key: str | None = None,
        webhook_secret: str | None = None,
        currency: str | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("STRIPE_API_KEY", "")
        self.webhook_secret = webhook_secret or os.environ.get(
            "STRIPE_WEBHOOK_SECRET", ""
        )
        self.currency = currency or os.environ.get("STRIPE_CURRENCY", "usd")
        self._cli_available: bool | None = None

    def is_configured(self) -> bool:
        """Check if Stripe client has required credentials."""
        return bool(self.api_key)

    def _check_cli(self) -> bool:
        """Check if Stripe CLI is available."""
        if self._cli_available is not None:
            return self._cli_available

        try:
            result = subprocess.run(
                ["stripe", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            self._cli_available = result.returncode == 0
            if self._cli_available:
                logger.info("Stripe CLI available: %s", result.stdout.strip())
            return self._cli_available
        except FileNotFoundError:
            self._cli_available = False
            logger.info("Stripe CLI not found — will use direct API calls")
            return False

    def _stripe_cli(self, *args: str) -> dict[str, Any] | None:
        """Execute a Stripe CLI command and return parsed JSON output."""
        if not self._check_cli():
            return None

        cmd = ["stripe", *args, "--format", "json"]
        try:
            import os
            env = {**os.environ, "STRIPE_API_KEY": self.api_key}
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
            )
            if result.returncode != 0:
                logger.error("Stripe CLI error: %s", result.stderr.strip())
                return None
            return json.loads(result.stdout)
        except subprocess.TimeoutExpired:
            logger.error("Stripe CLI command timed out")
            return None
        except json.JSONDecodeError:
            logger.error("Failed to parse Stripe CLI output: %s", result.stdout)
            return None
        except Exception as e:
            logger.error("Stripe CLI command failed: %s", e)
            return None

    def _stripe_api(
        self, method: str, endpoint: str, data: dict | None = None
    ) -> dict[str, Any] | None:
        """Make a direct Stripe API call using curl (fallback when CLI unavailable)."""
        import urllib.parse
        import urllib.request
        import urllib.error

        url = f"https://api.stripe.com/v1{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Stripe-Version": "2024-12-18.acacia",
        }

        body = None
        if data:
            body = "&".join(
                f"{k}={urllib.parse.quote(str(v))}" for k, v in data.items()
            ).encode()

        req = urllib.request.Request(
            url, data=body, headers=headers, method=method.upper()
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            logger.error("Stripe API error %d: %s", e.code, error_body)
            try:
                return json.loads(error_body)
            except json.JSONDecodeError:
                return {"error": {"message": error_body, "status_code": e.code}}
        except Exception as e:
            logger.error("Stripe API request failed: %s", e)
            return None

    # ── Invoice Operations ──────────────────────────────────────────────

    def create_invoice(
        self,
        customer_id: str,
        amount: float,
        currency: str | None = None,
        description: str = "",
        due_date: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Create a Stripe invoice for a customer.

        Args:
            customer_id: Stripe customer ID
            amount: Amount in the smallest currency unit (cents for USD)
            currency: Currency code (default: self.currency)
            description: Invoice description
            due_date: Due date in YYYY-MM-DD format
            metadata: Additional key-value pairs

        Returns:
            Invoice object from Stripe
        """
        currency = currency or self.currency
        amount_cents = int(amount * 100)  # Convert to cents

        data = {
            "customer": customer_id,
            "currency": currency,
            "description": description,
            "auto_advance": True,
        }

        if due_date:
            data["due_date"] = due_date
        if metadata:
            for k, v in metadata.items():
                data[f"metadata[{k}]"] = v

        # Try CLI first, fall back to API
        result = self._stripe_cli("invoices", "create", *self._flatten_params(data))
        if result:
            return result

        # Fallback: direct API call
        result = self._stripe_api("POST", "/invoices", data)
        if result and "id" in result:
            # Add invoice line item
            line_data = {
                "invoice": result["id"],
                "amount": amount_cents,
                "currency": currency,
                "description": description,
            }
            self._stripe_api("POST", "/invoiceitems", line_data)
            # Finalize invoice
            return (
                self._stripe_api("POST", f"/invoices/{result['id']}/finalize") or result
            )

        return {
            "error": "Failed to create invoice",
            "customer_id": customer_id,
            "amount": amount,
        }

    def send_invoice(self, invoice_id: str) -> dict[str, Any]:
        """Send an invoice to the customer via email."""
        result = self._stripe_cli("invoices", "send", invoice_id)
        if result:
            return result

        return self._stripe_api("POST", f"/invoices/{invoice_id}/send") or {
            "error": "Failed to send invoice",
            "invoice_id": invoice_id,
        }

    def get_invoice(self, invoice_id: str) -> dict[str, Any]:
        """Get invoice details and status."""
        result = self._stripe_cli("invoices", "retrieve", invoice_id)
        if result:
            return result

        return self._stripe_api("GET", f"/invoices/{invoice_id}") or {
            "error": "Failed to retrieve invoice",
            "invoice_id": invoice_id,
        }

    def list_invoices(
        self,
        customer_id: str | None = None,
        status: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """List invoices with optional filters."""
        params: list[str] = ["--limit", str(limit)]
        if customer_id:
            params.extend(["--customer", customer_id])
        if status:
            params.extend(["--status", status])

        result = self._stripe_cli("invoices", "list", *params)
        if result and isinstance(result, list):
            return result
        if result and "data" in result:
            return result["data"]

        # Fallback API
        api_params: dict[str, Any] = {"limit": limit}
        if customer_id:
            api_params["customer"] = customer_id
        if status:
            api_params["status"] = status

        api_result = self._stripe_api("GET", "/invoices", api_params)
        if api_result and "data" in api_result:
            return api_result["data"]

        return []

    def finalize_invoice(self, invoice_id: str) -> dict[str, Any]:
        """Finalize a draft invoice."""
        return self._stripe_api("POST", f"/invoices/{invoice_id}/finalize") or {
            "error": "Failed to finalize invoice",
            "invoice_id": invoice_id,
        }

    # ── Customer Operations ─────────────────────────────────────────────

    def create_customer(
        self,
        email: str,
        name: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Create a new Stripe customer."""
        data: dict[str, Any] = {"email": email}
        if name:
            data["name"] = name
        if metadata:
            for k, v in metadata.items():
                data[f"metadata[{k}]"] = v

        result = self._stripe_cli("customers", "create", *self._flatten_params(data))
        if result:
            return result

        return self._stripe_api("POST", "/customers", data) or {
            "error": "Failed to create customer",
            "email": email,
        }

    def get_customer(self, customer_id: str) -> dict[str, Any]:
        """Get customer details."""
        result = self._stripe_cli("customers", "retrieve", customer_id)
        if result:
            return result

        return self._stripe_api("GET", f"/customers/{customer_id}") or {
            "error": "Failed to retrieve customer",
            "customer_id": customer_id,
        }

    def list_customers(self, limit: int = 10) -> list[dict[str, Any]]:
        """List Stripe customers."""
        result = self._stripe_cli("customers", "list", "--limit", str(limit))
        if result and isinstance(result, list):
            return result
        if result and "data" in result:
            return result["data"]
        return []

    # ── Payment Operations ──────────────────────────────────────────────

    def create_payment_intent(
        self,
        amount: float,
        currency: str | None = None,
        customer_id: str | None = None,
        description: str = "",
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Create a PaymentIntent for processing a payment."""
        currency = currency or self.currency
        amount_cents = int(amount * 100)

        data: dict[str, Any] = {
            "amount": amount_cents,
            "currency": currency,
            "description": description,
        }
        if customer_id:
            data["customer"] = customer_id
        if metadata:
            for k, v in metadata.items():
                data[f"metadata[{k}]"] = v

        result = self._stripe_api("POST", "/payment_intents", data)
        return result or {"error": "Failed to create payment intent", "amount": amount}

    def confirm_payment_intent(self, intent_id: str) -> dict[str, Any]:
        """Confirm a PaymentIntent."""
        return self._stripe_api("POST", f"/payment_intents/{intent_id}/confirm") or {
            "error": "Failed to confirm payment intent",
            "intent_id": intent_id,
        }

    def get_payment_intent(self, intent_id: str) -> dict[str, Any]:
        """Get PaymentIntent status."""
        return self._stripe_api("GET", f"/payment_intents/{intent_id}") or {
            "error": "Failed to retrieve payment intent",
            "intent_id": intent_id,
        }

    # ── Subscription Operations ─────────────────────────────────────────

    def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        trial_period_days: int | None = None,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Create a subscription for a customer."""
        data: dict[str, Any] = {
            "customer": customer_id,
            "items[0][price]": price_id,
        }
        if trial_period_days:
            data["trial_period_days"] = str(trial_period_days)
        if metadata:
            for k, v in metadata.items():
                data[f"metadata[{k}]"] = v

        return self._stripe_api("POST", "/subscriptions", data) or {
            "error": "Failed to create subscription",
            "customer_id": customer_id,
        }

    def cancel_subscription(self, subscription_id: str) -> dict[str, Any]:
        """Cancel a subscription."""
        return self._stripe_api("DELETE", f"/subscriptions/{subscription_id}") or {
            "error": "Failed to cancel subscription",
            "subscription_id": subscription_id,
        }

    def get_subscription(self, subscription_id: str) -> dict[str, Any]:
        """Get subscription details."""
        return self._stripe_api("GET", f"/subscriptions/{subscription_id}") or {
            "error": "Failed to retrieve subscription",
            "subscription_id": subscription_id,
        }

    # ── Webhook Handling ────────────────────────────────────────────────

    def verify_webhook(self, payload: str, sig_header: str) -> dict[str, Any] | None:
        """Verify a Stripe webhook signature and return the event."""
        if not self.webhook_secret:
            logger.warning("No webhook secret configured — cannot verify webhooks")
            return None

        try:
            import stripe as stripe_lib

            return stripe_lib.Webhook.construct_event(  # type: ignore[return-value]
                payload, sig_header, self.webhook_secret
            )
        except ImportError:
            # Manual verification fallback
            return self._verify_webhook_manual(payload, sig_header)
        except Exception as e:
            logger.error("Webhook verification failed: %s", e)
            return None

    def _verify_webhook_manual(
        self, payload: str, sig_header: str
    ) -> dict[str, Any] | None:
        """Manual webhook verification without the Stripe SDK."""
        import hmac
        import hashlib

        if not self.webhook_secret:
            return None

        # Parse signature header: t=timestamp,v1=signature
        parts = {}
        for part in sig_header.split(","):
            if "=" in part:
                key, value = part.split("=", 1)
                parts[key.strip()] = value.strip()

        timestamp = parts.get("t", "")
        signature = parts.get("v1", "")

        if not timestamp or not signature:
            logger.error("Invalid webhook signature header")
            return None

        # Verify timestamp (reject events older than 5 minutes)
        try:
            event_time = int(timestamp)
            if abs(int(datetime.now(timezone.utc).timestamp()) - event_time) > 300:
                logger.warning("Webhook timestamp too old — possible replay attack")
                return None
        except ValueError:
            return None

        # Verify signature
        signed_payload = f"{timestamp}.{payload}".encode("utf-8")
        expected = hmac.new(
            self.webhook_secret.encode("utf-8"),
            signed_payload,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, signature):
            logger.error("Webhook signature mismatch")
            return None

        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return None

    # ── Balance & Reporting ─────────────────────────────────────────────

    def get_balance(self) -> dict[str, Any]:
        """Get current Stripe account balance."""
        return self._stripe_api("GET", "/balance") or {
            "error": "Failed to retrieve balance"
        }

    def list_charges(
        self,
        customer_id: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """List charges with optional customer filter."""
        params: dict[str, Any] = {"limit": limit}
        if customer_id:
            params["customer"] = customer_id

        result = self._stripe_api("GET", "/charges", params)
        if result and "data" in result:
            return result["data"]
        return []

    def get_revenue_summary(self, days: int = 30) -> dict[str, Any]:
        """Get a summary of revenue over the past N days."""
        charges = self.list_charges(limit=100)
        cutoff = datetime.now(timezone.utc).timestamp() - (days * 86400)

        total_revenue = 0
        successful_count = 0
        failed_count = 0

        for charge in charges:
            created = charge.get("created", 0)
            if isinstance(created, (int, float)) and created >= cutoff:
                if charge.get("status") == "succeeded":
                    total_revenue += charge.get("amount", 0)
                    successful_count += 1
                else:
                    failed_count += 1

        return {
            "total_revenue_cents": total_revenue,
            "total_revenue": total_revenue / 100,
            "successful_payments": successful_count,
            "failed_payments": failed_count,
            "currency": self.currency,
            "period_days": days,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # ── Utility ─────────────────────────────────────────────────────────

    def _flatten_params(self, params: dict[str, Any]) -> list[str]:
        """Flatten a dict into CLI arguments."""
        args: list[str] = []
        for key, value in params.items():
            args.extend([f"--{key}", str(value)])
        return args
