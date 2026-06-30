# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw v3.0 — Failover Inference Broker

This module continuously monitors local edge model latency (such as a local vLLM
instance or edge NVIDIA NIM) and dynamically swaps active model routes utilizing
NemoClaw environment overrides (NEMOCLAW_MODEL) and the OpenShell CLI.
"""

import logging
import os
import subprocess
import time
import urllib.request

logger = logging.getLogger("milimo.failover_broker")


class FailoverInferenceBroker:
    """
    Manages edge latency heartbeats and dynamic route failovers.
    Toggles between local edge models and remote cloud NIMs at runtime.
    """

    def __init__(
        self,
        local_endpoint: str = "http://localhost:8000/v1/models",
        latency_threshold_ms: float = 800.0,
        cloud_model: str | None = None,
        require_operator_approval: bool = True,
    ) -> None:
        self.local_endpoint = local_endpoint
        self.latency_threshold_ms = latency_threshold_ms
        self.cloud_model = cloud_model
        self.require_operator_approval = require_operator_approval
        self._is_failed_over = False
        self._failover_pending_approval = False
        self._operator_approved = False

    def ping_local_backend(self) -> float:
        """
        Pings the local endpoint to measure current latency.
        Returns latency in milliseconds, or float('inf') on error.
        """
        start = time.perf_counter()
        try:
            # Short 1.0s timeout to prevent thread blocks
            with urllib.request.urlopen(self.local_endpoint, timeout=1.0) as response:
                if response.status == 200:
                    latency = (time.perf_counter() - start) * 1000.0
                    return latency
        except Exception as e:
            logger.debug("Failed to ping local backend: %s", e)
        return float("inf")

    def evaluate_and_route(self) -> bool:
        """
        Evaluates local latency. If latency exceeds thresholds:
        - If require_operator_approval is True, requests manual operator approval
          and only routes once approve_failover() is called.
        - If require_operator_approval is False, automatically activates cloud failover.
        """
        latency = self.ping_local_backend()

        if latency > self.latency_threshold_ms:
            if not self._is_failed_over:
                if self.require_operator_approval:
                    if not self._operator_approved:
                        if not self._failover_pending_approval:
                            logger.warning(
                                "Local edge latency (%.2fms) breached threshold (%.2fms). "
                                "Cloud failover is pending manual operator REVIEW.",
                                latency,
                                self.latency_threshold_ms,
                            )
                            self._failover_pending_approval = True
                        return False  # Restrict routing: do not route to cloud yet
                else:
                    # Auto routing
                    logger.warning(
                        "Local edge latency (%.2fms) breached threshold (%.2fms). "
                        "Initiating automatic cloud NIM failover.",
                        latency,
                        self.latency_threshold_ms,
                    )
                    self._activate_cloud_routing()
            return self._is_failed_over
        else:
            self._failover_pending_approval = False
            self._operator_approved = False
            if self._is_failed_over:
                logger.info(
                    "Local edge latency recovered (%.2fms). Restoring local edge routing.",
                    latency,
                )
                self._restore_local_routing()
            return False

    def approve_failover(self) -> None:
        """Manually approves the pending failover request, triggering cloud failover."""
        if self._failover_pending_approval and not self._is_failed_over:
            logger.info(
                "Operator approved cloud failover request. Activating cloud routing."
            )
            self._operator_approved = True
            self._failover_pending_approval = False
            self._activate_cloud_routing()

    def deny_failover(self) -> None:
        """Manually denies the pending failover request."""
        if self._failover_pending_approval:
            logger.info(
                "Operator denied cloud failover request. Remaining on local edge."
            )
            self._failover_pending_approval = False
            self._operator_approved = False

    @property
    def failover_pending_approval(self) -> bool:
        """Returns True if a failover is currently awaiting operator approval."""
        return self._failover_pending_approval

    @property
    def operator_approved(self) -> bool:
        """Returns True if the operator has approved the active failover."""
        return self._operator_approved

    def _activate_cloud_routing(self) -> None:
        """Triggers the OpenShell CLI and sets environments to route to cloud."""
        if not self.cloud_model:
            logger.warning("Cannot activate cloud routing — no cloud_model configured")
            return

        # 1. Update the process model environment override
        os.environ["NEMOCLAW_MODEL"] = self.cloud_model

        # 2. Invoke the OpenShell CLI dynamically
        try:
            cmd = [
                "openshell",
                "inference",
                "set",
                "--provider",
                "nvidia-nim",
                "--model",
                self.cloud_model,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                logger.info("Successfully executed: %s", " ".join(cmd))
            else:
                logger.error(
                    "OpenShell CLI execution failed: %s", result.stderr.strip()
                )
        except FileNotFoundError:
            logger.warning(
                "openshell CLI not found on PATH. Defaulting to env overrides."
            )

        self._is_failed_over = True

    def _restore_local_routing(self) -> None:
        """Restores process configurations back to local edge backends."""
        if "NEMOCLAW_MODEL" in os.environ:
            del os.environ["NEMOCLAW_MODEL"]

        try:
            cmd = [
                "openshell",
                "inference",
                "set",
                "--provider",
                "openai",
                "--model",
                "local-edge",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                logger.info("Successfully restored local route: %s", " ".join(cmd))
        except FileNotFoundError:
            pass

        self._is_failed_over = False

    @property
    def is_failed_over(self) -> bool:
        """Returns True if currently routed to cloud NIM."""
        return self._is_failed_over
