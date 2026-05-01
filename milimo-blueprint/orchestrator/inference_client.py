# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
NVIDIA NIM Inference Client with fallback chain and category-based model routing.

Wraps the NVIDIA NIM API (OpenAI-compatible) for all inference needs across
Build, Content, and Ops claws. Implements the fallback chain defined in
build_init.py (NEMOCLAW_MODEL → claude-sonnet-4-6 → gemini-3.1-pro) and
category-based model/temperature selection from BUILD_CATEGORIES.

Environment variables:
    NVIDIA_API_KEY — API key for NVIDIA NIM endpoint
    NVIDIA_API_BASE — Base URL (default: https://integrate.api.nvidia.com/v1)
    INFERENCE_FALLBACK — Comma-separated fallback model list (optional override)
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("milimo.inference_client")

_NEMOCLAW_MODEL = os.environ.get("NEMOCLAW_MODEL", "nvidia/nemotron-3-super-120b-a12b")

DEFAULT_FALLBACK_CHAIN = [
    _NEMOCLAW_MODEL,
    "meta/llama-3.3-70b-instruct",
    "mistralai/mixtral-8x22b-instruct-v0.1",
]

DEFAULT_API_BASE = os.environ.get(
    "NVIDIA_API_BASE", "https://integrate.api.nvidia.com/v1"
)

CATEGORY_MODELS: dict[str, dict[str, Any]] = {
    "source_code_generation": {"model": _NEMOCLAW_MODEL, "temperature": 0.1},
    "code_review": {"model": _NEMOCLAW_MODEL, "temperature": 0.1},
    "pr_description_generation": {"model": _NEMOCLAW_MODEL, "temperature": 0.3},
    "issue_complexity_scoring": {"model": _NEMOCLAW_MODEL, "temperature": 0.2},
    "changelog_generation": {"model": _NEMOCLAW_MODEL, "temperature": 0.7},
    "api_documentation_generation": {"model": _NEMOCLAW_MODEL, "temperature": 0.3},
    "devlog_draft_generation": {"model": _NEMOCLAW_MODEL, "temperature": 0.7},
    "dependency_vulnerability_analysis": {"model": _NEMOCLAW_MODEL, "temperature": 0.1},
    "content_draft": {"model": _NEMOCLAW_MODEL, "temperature": 0.7},
    "content_plan": {"model": _NEMOCLAW_MODEL, "temperature": 0.3},
    "sentiment_analysis": {"model": _NEMOCLAW_MODEL, "temperature": 0.1},
    "incident_analysis": {"model": _NEMOCLAW_MODEL, "temperature": 0.2},
    "general": {"model": _NEMOCLAW_MODEL, "temperature": 0.5},
}


@dataclass
class InferenceUsage:
    """Tracks token usage and cost for a single inference call."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    model_used: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class InferenceResponse:
    """Response from an inference call."""

    content: str
    usage: InferenceUsage
    model_used: str
    attempts: int
    success: bool
    error: str | None = None


class NvidiaInferenceClient:
    """
    NVIDIA NIM inference client with automatic fallback chain retry.

    Usage:
        client = NvidiaInferenceClient()
        response = client.complete(prompt="Write a function...", data_type="source_code_generation")
        print(response.content)
        print(client.get_usage())
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        fallback_chain: list[str] | None = None,
        max_retries: int = 3,
        timeout: int = 120,
    ) -> None:
        _sandbox_mode = bool(os.environ.get("NEMOCLAW_MODEL"))
        _proxy_host = os.environ.get("NEMOCLAW_PROXY_HOST", "10.200.0.1")
        _proxy_port = os.environ.get("NEMOCLAW_PROXY_PORT", "3128")

        self.api_key = api_key or os.environ.get("NVIDIA_API_KEY", "")
        self.api_base = (api_base or DEFAULT_API_BASE).rstrip("/")
        self.fallback_chain = fallback_chain or DEFAULT_FALLBACK_CHAIN
        self.max_retries = max_retries
        self.timeout = timeout

        self._usage_history: list[InferenceUsage] = []
        self._total_cost_usd: float = 0.0
        self._sandbox_mode = _sandbox_mode

        if _sandbox_mode:
            inference_base = os.environ.get("NEMOCLAW_INFERENCE_BASE_URL", "")
            if inference_base:
                self.api_base = inference_base.rstrip("/")
            if not self.api_key:
                self.api_key = "unused"
            proxy_url = f"http://{_proxy_host}:{_proxy_port}"
            os.environ["HTTP_PROXY"] = proxy_url
            os.environ["HTTPS_PROXY"] = proxy_url
            logger.info(
                "NvidiaInferenceClient: sandbox mode — using proxy %s", proxy_url
            )
        elif not self.api_key:
            logger.warning("NVIDIA_API_KEY not set — inference calls will fail")

    def complete(
        self,
        prompt: str,
        data_type: str = "general",
        temperature: float | None = None,
        max_tokens: int = 4096,
        system_prompt: str | None = None,
    ) -> str:
        category = CATEGORY_MODELS.get(data_type, CATEGORY_MODELS["general"])
        _model = category["model"]
        temp = temperature if temperature is not None else category["temperature"]

        last_error: str | None = None
        attempts = 0

        for attempt_idx, model_name in enumerate(self.fallback_chain):
            attempts += 1
            try:
                response = self._call_model(
                    model=model_name,
                    prompt=prompt,
                    temperature=temp,
                    max_tokens=max_tokens,
                    system_prompt=system_prompt,
                )
                usage = InferenceUsage(
                    prompt_tokens=response.get("usage", {}).get("prompt_tokens", 0),
                    completion_tokens=response.get("usage", {}).get(
                        "completion_tokens", 0
                    ),
                    total_tokens=response.get("usage", {}).get("total_tokens", 0),
                    estimated_cost_usd=self._estimate_cost(
                        response.get("usage", {}).get("total_tokens", 0)
                    ),
                    model_used=model_name,
                )
                self._usage_history.append(usage)
                self._total_cost_usd += usage.estimated_cost_usd

                content = ""
                if "choices" in response and response["choices"]:
                    content = (
                        response["choices"][0].get("message", {}).get("content", "")
                    )

                logger.info(
                    "Inference success with %s (attempt %d, %d tokens)",
                    model_name,
                    attempt_idx + 1,
                    usage.total_tokens,
                )
                return content

            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "Inference failed with %s (attempt %d/%d): %s",
                    model_name,
                    attempt_idx + 1,
                    len(self.fallback_chain),
                    last_error,
                )
                if attempt_idx < len(self.fallback_chain) - 1:
                    time.sleep(2**attempt_idx)

        raise RuntimeError(
            f"All {len(self.fallback_chain)} models in fallback chain failed. "
            f"Last error: {last_error}"
        )

    def get_usage(self) -> dict[str, Any]:
        """Return aggregate usage statistics."""
        total_prompt = sum(u.prompt_tokens for u in self._usage_history)
        total_completion = sum(u.completion_tokens for u in self._usage_history)
        total_tokens = sum(u.total_tokens for u in self._usage_history)

        return {
            "total_calls": len(self._usage_history),
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "total_tokens": total_tokens,
            "total_cost_usd": round(self._total_cost_usd, 6),
            "history": [
                {
                    "model": u.model_used,
                    "tokens": u.total_tokens,
                    "cost_usd": u.estimated_cost_usd,
                    "timestamp": u.timestamp,
                }
                for u in self._usage_history[-50:]
            ],
        }

    def reset_usage(self) -> None:
        """Reset usage counters."""
        self._usage_history.clear()
        self._total_cost_usd = 0.0

    def _call_model(
        self,
        model: str,
        prompt: str,
        temperature: float,
        max_tokens: int,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Make a single API call to the specified model using stdlib urllib."""
        if not self.api_key and not self._sandbox_mode:
            raise RuntimeError("NVIDIA_API_KEY is not configured")

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        url = f"{self.api_base}/chat/completions"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        ctx = None
        if self._sandbox_mode:
            import ssl

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

        with urllib.request.urlopen(req, timeout=self.timeout, context=ctx) as response:
            return json.loads(response.read())

    @staticmethod
    def _estimate_cost(total_tokens: int) -> float:
        """Estimate cost based on token count (~$0.0001 per token for NEMOCLAW_MODEL)."""
        return total_tokens * 0.0001
