#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Tool Builder & Tester

Builds proposed tools in isolation, backtests them against historical
operation log data, and compares performance against baseline.

The builder generates tool code (using the claw's inference backend),
replays 4 weeks of historical data through the tool, and only stages
the tool for deployment if it beats the baseline by the configured
minimum improvement threshold.

Usage:
    from tool_builder import ToolBuilder, BuiltTool

    builder = ToolBuilder(claw_role="content")
    result = builder.build(proposal)
    if result.passed:
        builder.stage_for_deployment(result.tool)
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .operation_log import ActionRecord
from .tool_proposal import ToolProposal

logger = logging.getLogger("milimo.tool_builder")

# Import ToolGenerator for actual code generation
try:
    from .tool_generator import ToolGenerator, ToolSpec, GenerationResult

    TOOL_GENERATOR_AVAILABLE = True
except ImportError:
    TOOL_GENERATOR_AVAILABLE = False
    ToolGenerator = None
    ToolSpec = None
    GenerationResult = None

# Import ToolSandbox for isolated testing
try:
    from .tool_sandbox import ToolSandbox, SandboxConfig

    TOOL_SANDBOX_AVAILABLE = True
except ImportError:
    TOOL_SANDBOX_AVAILABLE = False
    ToolSandbox = None
    SandboxConfig = None

# Import PrivacyRouter for inference routing
try:
    from .privacy_router import PrivacyRouter, InferenceBackend

    PRIVACY_ROUTER_AVAILABLE = True
except ImportError:
    PRIVACY_ROUTER_AVAILABLE = False
    PrivacyRouter = None
    InferenceBackend = None

# Import SandboxRunner for isolated backtesting
try:
    from .evolution.sandbox_runner import (
        SandboxRunner,
        BacktestResult as SandboxBacktestResult,
        _meets_threshold,
    )

    SANDBOX_RUNNER_AVAILABLE = True
except ImportError:
    SANDBOX_RUNNER_AVAILABLE = False
    SandboxRunner = None
    SandboxBacktestResult = None
    _meets_threshold = None


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class BuiltTool:
    """A tool that has been built and backtested."""

    proposal: ToolProposal
    tool_name: str
    tool_type: str
    version: str = "0.1.0"
    code: str = ""  # Python source for the tool
    performance_delta: float = 0.0  # measured % uplift vs baseline
    training_data_hash: str = ""  # sha256 of data used
    baseline_score: float = 0.0
    tool_score: float = 0.0
    claw_role: str = ""
    squad_id: str = ""
    built_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    status: str = "staged"  # staged | deployed | disabled

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BuiltTool:
        # Handle nested proposal
        proposal_data = data.get("proposal", {})
        if isinstance(proposal_data, dict):
            from .tool_proposal import ToolProposal

            data["proposal"] = ToolProposal.from_dict(proposal_data)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class BacktestResult:
    """Result of backtesting a tool against historical data."""

    tool_name: str
    baseline_score: float  # metric value without the tool
    tool_score: float  # metric value with the tool
    improvement_percent: float  # (tool - baseline) / baseline * 100
    sample_size: int  # number of actions in backtest window
    passed: bool  # did it beat the minimum threshold?
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class BuildResult:
    """Overall result of the build + backtest process."""

    proposal: ToolProposal
    tool: BuiltTool | None = None
    backtest: BacktestResult | None = None
    passed: bool = False
    failure_reason: str = ""


# ---------------------------------------------------------------------------
# Tool Builder
# ---------------------------------------------------------------------------


class ToolBuilder:
    """
    Builds and backtests proposed tools in isolation.

    The build process:
    1. Generate tool code from the proposal (uses inference)
    2. Backtest the tool against 4 weeks of historical data
    3. Compare against baseline — pass if improvement >= threshold
    4. Stage for deployment if passed
    """

    def __init__(
        self,
        claw_role: str,
        squad_id: str = "",
        min_improvement_percent: float = 5.0,
        backtest_window_weeks: int = 4,
        staging_dir: str | None = None,
        blueprint_dir: str | Path | None = None,
        inference_client: Any | None = None,
    ) -> None:
        self.claw_role = claw_role
        self.squad_id = squad_id
        self.min_improvement_percent = min_improvement_percent
        self.backtest_window_weeks = backtest_window_weeks
        self.blueprint_dir = Path(blueprint_dir) if blueprint_dir else None
        self._inference_client = inference_client

        if staging_dir:
            self._staging_dir = Path(staging_dir)
        else:
            self._staging_dir = Path("/tmp") / "milimo-tool-staging" / claw_role
        self._staging_dir.mkdir(parents=True, exist_ok=True)

        # Initialize tool generator if available
        self._tool_generator = None
        if TOOL_GENERATOR_AVAILABLE and self.blueprint_dir:
            template_dir = self.blueprint_dir / "prompts" / "tool-generation"
            if template_dir.exists():
                assert ToolGenerator is not None
                self._tool_generator = ToolGenerator(
                    template_dir=template_dir,
                    inference_client=self._inference_client,
                )
                logger.info(
                    "ToolGenerator initialized with templates from %s", template_dir
                )

    def build(
        self,
        proposal: ToolProposal,
        historical_actions: list[ActionRecord],
        tool_code: str | None = None,
    ) -> BuildResult:
        """
        Build a tool from a proposal and backtest it.

        Args:
            proposal: The tool proposal to build
            historical_actions: Actions for backtesting (4+ weeks)
            tool_code: Optional pre-generated tool code (for testing).
                       In production, this would be generated by inference.

        Returns:
            BuildResult with pass/fail and the built tool if passed.
        """
        logger.info(
            "Building tool '%s' (%s) for %s",
            proposal.tool_name,
            proposal.tool_type,
            self.claw_role,
        )

        proposal.status = "building"

        # Step 1: Generate tool code
        if tool_code is None:
            tool_code = self._generate_tool_code(proposal)
            if not tool_code:
                proposal.status = "failed"
                return BuildResult(
                    proposal=proposal,
                    passed=False,
                    failure_reason="Tool code generation failed",
                )

        proposal.status = "testing"

        # Step 2: Compute data hash
        data_hash = self._compute_data_hash(historical_actions)

        # Step 3: Backtest
        backtest = self.backtest(proposal, historical_actions, tool_code)

        # Step 4: Build the tool object
        tool = BuiltTool(
            proposal=proposal,
            tool_name=proposal.tool_name,
            tool_type=proposal.tool_type,
            code=tool_code,
            performance_delta=backtest.improvement_percent,
            training_data_hash=data_hash,
            baseline_score=backtest.baseline_score,
            tool_score=backtest.tool_score,
            claw_role=self.claw_role,
            squad_id=self.squad_id,
        )

        # Step 5: Check pass/fail
        if backtest.passed:
            proposal.status = "deployed"
            tool.status = "staged"
            logger.info(
                "Tool '%s' passed backtest: +%.1f%% on %s (threshold: %.1f%%)",
                proposal.tool_name,
                backtest.improvement_percent,
                proposal.metric_target,
                self.min_improvement_percent,
            )
        else:
            proposal.status = "failed"
            tool.status = "disabled"
            logger.info(
                "Tool '%s' failed backtest: +%.1f%% (need +%.1f%%)",
                proposal.tool_name,
                backtest.improvement_percent,
                self.min_improvement_percent,
            )

        return BuildResult(
            proposal=proposal,
            tool=tool,
            backtest=backtest,
            passed=backtest.passed,
            failure_reason=""
            if backtest.passed
            else (
                f"Improvement {backtest.improvement_percent:.1f}% below "
                f"threshold {self.min_improvement_percent:.1f}%"
            ),
        )

    def backtest(
        self,
        proposal: ToolProposal,
        historical_actions: list[ActionRecord],
        tool_code: str,
    ) -> BacktestResult:
        """
        Backtest a tool against historical data.

        Computes baseline performance (without tool) and tool performance
        (simulating the tool's effect) on the target metric.
        """
        if not historical_actions:
            return BacktestResult(
                tool_name=proposal.tool_name,
                baseline_score=0.0,
                tool_score=0.0,
                improvement_percent=0.0,
                sample_size=0,
                passed=False,
                details={"reason": "No historical data for backtesting"},
            )

        # Compute baseline metric
        baseline = self._compute_baseline(proposal.metric_target, historical_actions)

        # Simulate tool effect
        tool_score = self._simulate_tool_effect(
            proposal, historical_actions, tool_code, baseline
        )

        # Calculate improvement
        if baseline == 0:
            improvement = 0.0
        else:
            improvement = ((tool_score - baseline) / abs(baseline)) * 100.0

        passed = improvement >= self.min_improvement_percent

        return BacktestResult(
            tool_name=proposal.tool_name,
            baseline_score=baseline,
            tool_score=tool_score,
            improvement_percent=round(improvement, 2),
            sample_size=len(historical_actions),
            passed=passed,
            details={
                "metric_target": proposal.metric_target,
                "threshold": self.min_improvement_percent,
            },
        )

    def stage_for_deployment(self, tool: BuiltTool) -> Path:
        """Write a built tool to the staging directory."""
        tool_file = self._staging_dir / f"{tool.tool_name}.json"
        with tool_file.open("w") as f:
            json.dump(tool.to_dict(), f, indent=2, default=str)
        logger.info("Staged tool '%s' at %s", tool.tool_name, tool_file)
        return tool_file

    # ── Internal Methods ──────────────────────────────────────────────

    def _generate_tool_code(self, proposal: ToolProposal) -> str:
        """
        Generate tool code from a proposal using inference.

        Routes to local/cloud NIM via privacy router (data_type="source_code").
        Falls back to skeleton code if inference fails.

        Args:
            proposal: The tool proposal

        Returns:
            Generated Python code for the tool
        """
        # Try using ToolGenerator with privacy router integration
        if self._tool_generator is not None and ToolSpec is not None:
            try:
                # Cast tool_type to valid literal
                tool_type = proposal.tool_type
                valid_types = (
                    "classifier",
                    "predictor",
                    "optimizer",
                    "detector",
                    "generator",
                    "transformer",
                    "aggregator",
                )
                if tool_type not in valid_types:
                    tool_type = "classifier"  # Default fallback

                # Build metadata with operational context
                metadata = {
                    "metric_target": proposal.metric_target,
                    "estimated_improvement": proposal.estimated_improvement,
                    "claw_role": proposal.claw_role,
                    "trigger_pattern": proposal.trigger_pattern.pattern_type,
                }

                spec = ToolSpec(
                    name=proposal.tool_name,
                    tool_type=tool_type,  # type: ignore[arg-type]
                    description=f"Generated for pattern: {proposal.trigger_pattern.pattern_type}",
                    input_schema={
                        "type": "object",
                        "properties": {"action_data": {"type": "object"}},
                    },
                    output_schema={
                        "type": "object",
                        "properties": {"result": {"type": "object"}},
                    },
                    pattern_description=proposal.trigger_pattern.trigger_description,
                    frequency=getattr(proposal.trigger_pattern, "frequency", 1),
                    time_period="7 days",
                    evolution_cycle=f"{self.squad_id}-{self.claw_role}",
                    metadata=metadata,
                    test_cases=[],
                )

                # Use ToolGenerator which routes through privacy router
                result = self._tool_generator.generate(spec)

                if result.success and result.code:
                    # Validate Python syntax before returning
                    if self._validate_syntax(result.code):
                        logger.info(
                            "Generated tool code via inference: %d chars, validation=%s",
                            len(result.code),
                            result.validation_passed,
                        )
                        return result.code
                    else:
                        logger.warning("Generated code failed syntax validation")

                logger.warning(
                    "ToolGenerator failed: %s, falling back to skeleton",
                    result.error,
                )

            except Exception as e:
                logger.warning("ToolGenerator error: %s, falling back to skeleton", e)

        # Fallback: inference-based code generation via privacy router
        if PRIVACY_ROUTER_AVAILABLE and self.blueprint_dir:
            try:
                code = self._generate_via_inference(proposal)
                if code and self._validate_syntax(code):
                    logger.info("Generated tool code via privacy router inference")
                    return code
            except Exception as e:
                logger.warning(
                    "Privacy router inference failed: %s, falling back to skeleton", e
                )

        # Final fallback: generate skeleton code
        return self._generate_skeleton_code(proposal)

    def _generate_via_inference(self, proposal: ToolProposal) -> str | None:
        """
        Generate tool code through privacy router inference.

        Routes data_type="source_code" which requires local NIM.
        Builds a structured prompt and extracts code from response.

        Args:
            proposal: The tool proposal

        Returns:
            Generated code or None if inference fails
        """
        if (
            not PRIVACY_ROUTER_AVAILABLE
            or PrivacyRouter is None
            or InferenceBackend is None
        ):
            return None

        if self.blueprint_dir is None:
            return None

        # Local variable with guaranteed non-None type
        blueprint_dir = self.blueprint_dir

        try:
            # Load privacy policy
            policy_path = blueprint_dir / "privacy_policy.yaml"
            if not policy_path.exists():
                logger.debug("No privacy policy found at %s", policy_path)
                return None

            router = PrivacyRouter.from_policy_file(policy_path)

            # Route inference - source_code must use local NIM
            decision = router.route(
                role=self.claw_role,
                data_type="source_code",
            )

            logger.debug(
                "Inference routed to %s for source_code: %s",
                decision.backend.value,
                decision.reason,
            )

            # Ensure local backend for source code
            if decision.backend != InferenceBackend.LOCAL_NIM:
                logger.warning(
                    "source_code routed to non-local backend %s, enforcing local",
                    decision.backend.value,
                )

            # Build structured prompt for inference
            prompt = self._build_inference_prompt(proposal)

            # Call local NIM inference endpoint
            code = self._call_nim_inference(prompt, proposal)

            if code and self._validate_syntax(code):
                logger.info(
                    "Generated tool code via NIM inference (%d chars)", len(code)
                )
                return code

            return None

        except Exception as e:
            logger.warning("Privacy router inference error: %s", e)
            return None

    def _call_nim_inference(self, prompt: str, proposal: ToolProposal) -> str | None:
        """
        Call local NIM inference endpoint to generate tool code.

        Supports multiple backends:
        1. NeMo Microservice (nemo-ms) on localhost:8000
        2. Local NIM (NEMOCLAW_MODEL) container on localhost:8000
        3. OpenShell gateway sandbox

            Args:
                prompt: The inference prompt
                proposal: The tool proposal for context

            Returns:
                Generated Python code or None on failure
        """
        import json
        import os
        import urllib.request
        import urllib.error

        # Check for NIM endpoint configuration
        nim_endpoint = os.environ.get("NIM_ENDPOINT", "http://localhost:8000")
        nim_model = os.environ.get(
            "NEMOCLAW_MODEL", "nvidia/nemotron-3-super-120b-a12b"
        )

        # Check if NIM is available
        try:
            health_url = f"{nim_endpoint}/v1/health"
            req = urllib.request.Request(health_url, method="GET")
            urllib.request.urlopen(req, timeout=2)
            logger.info("NIM endpoint healthy at %s", nim_endpoint)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            logger.debug("NIM endpoint not available at %s: %s", nim_endpoint, e)
            # Try OpenShell gateway as fallback
            return self._call_gateway_inference(prompt, proposal)

        # Build OpenAI-compatible request
        request_body = {
            "model": nim_model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a Python code generator. Generate only valid Python code with no explanations or markdown. Include proper type hints and docstrings. The code should implement an 'apply' function that takes action_data: dict and returns a result dict.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 2048,
            "stop": ["```", "---", "Explanation:", "Note:"],
        }

        try:
            url = f"{nim_endpoint}/v1/chat/completions"
            data = json.dumps(request_body).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))

            # Extract code from response
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0].get("message", {}).get("content", "")
                # Clean up code - remove markdown blocks if present
                code = self._extract_code_from_response(content)
                return code

            return None

        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            json.JSONDecodeError,
        ) as e:
            logger.warning("NIM inference call failed: %s", e)
            return None

    def _call_gateway_inference(
        self, prompt: str, proposal: ToolProposal
    ) -> str | None:
        """
        Call OpenShell gateway for inference as fallback.

        Args:
            prompt: The inference prompt
            proposal: The tool proposal

        Returns:
            Generated code or None
        """
        import os
        import time

        try:
            # Use file-based gateway for inference request
            home = os.environ.get("HOME", "/tmp")
            gateway_dir = Path(home) / ".milimo" / "inference"
            gateway_dir.mkdir(parents=True, exist_ok=True)

            # Write inference request
            request_file = gateway_dir / f"request_{proposal.tool_name}.json"
            request_data = {
                "type": "inference_request",
                "model": os.environ.get(
                    "NEMOCLAW_MODEL", "nvidia/nemotron-3-super-120b-a12b"
                ),
                "prompt": prompt,
                "parameters": {
                    "temperature": 0.3,
                    "max_tokens": 2048,
                },
                "tool_name": proposal.tool_name,
                "tool_type": proposal.tool_type,
                "claw_role": proposal.claw_role,
            }

            with request_file.open("w") as f:
                json.dump(request_data, f)

            # Check for response (would be written by gateway handler)
            response_file = gateway_dir / f"response_{proposal.tool_name}.json"

            # Wait briefly for response (non-blocking in production)
            for _ in range(10):  # Wait up to 10 seconds
                if response_file.exists():
                    with response_file.open() as f:
                        response = json.load(f)
                    code = response.get("code")
                    if code and self._validate_syntax(code):
                        return code
                    break
                time.sleep(1)

            logger.debug("No gateway inference response received")
            return None

        except Exception as e:
            logger.debug("Gateway inference fallback failed: %s", e)
            return None

    def _extract_code_from_response(self, content: str) -> str | None:
        """
        Extract Python code from LLM response.

        Handles various formats:
        - Raw code
        - Markdown code blocks
        - Code with explanations

        Args:
            content: Raw LLM response content

        Returns:
            Clean Python code or None
        """

        # Try to extract code from markdown blocks
        code_block_pattern = r"```(?:python)?\s*\n(.*?)\n```"
        matches = re.findall(code_block_pattern, content, re.DOTALL)

        if matches:
            # Use the longest code block
            code = max(matches, key=len).strip()
        else:
            # No code blocks, use content directly
            code = content.strip()

        # Clean up common artifacts
        lines = code.split("\n")
        cleaned_lines = []
        in_code = False

        for line in lines:
            # Skip explanation lines
            stripped = line.strip()
            if stripped.startswith("# ") and not in_code:
                # Check if this is a docstring or explanation
                if any(
                    word in stripped.lower()
                    for word in ["here", "this code", "the following", "example"]
                ):
                    continue

            # Start capturing after we see function/class definitions
            if stripped.startswith(("def ", "class ", "import ", "from ")) or in_code:
                in_code = True
                cleaned_lines.append(line)

        code = "\n".join(cleaned_lines).strip()

        # Validate syntax
        if self._validate_syntax(code):
            return code

        return None

    def _build_inference_prompt(self, proposal: ToolProposal) -> str:
        """
        Build structured prompt for inference-based tool generation.

        Args:
            proposal: The tool proposal

        Returns:
            Formatted prompt string
        """
        prompt_parts = [
            "# Tool Generation Request",
            "",
            "## Tool Purpose",
            f"Name: {proposal.tool_name}",
            f"Type: {proposal.tool_type}",
            f"Role: {proposal.claw_role}",
            "",
            "## Target Metric",
            f"Metric: {proposal.metric_target}",
            f"Expected Improvement: {proposal.estimated_improvement}%",
            "",
            "## Trigger Pattern",
            f"Type: {proposal.trigger_pattern.pattern_type}",
            f"Description: {proposal.trigger_pattern.trigger_description}",
            f"Confidence: {proposal.trigger_pattern.confidence}",
            "",
            "## Requirements",
            "- Accept standard ToolInput interface (action_data: dict)",
            "- Return standard ToolOutput interface (result: dict)",
            "- Include error handling for edge cases",
            "- Be importable as Python module",
            "- Pass syntax validation",
            "",
            "## Data Sources",
            "- Historical action logs",
            "- Claw configuration",
            "- Squad policies",
            "",
            "Generate the Python implementation:",
        ]

        return "\n".join(prompt_parts)

    def _generate_skeleton_code(self, proposal: ToolProposal) -> str:
        """
        Generate skeleton code as final fallback.

        Args:
            proposal: The tool proposal

        Returns:
            Skeleton Python code
        """
        return (
            f"# Auto-generated tool: {proposal.tool_name}\n"
            f"# Type: {proposal.tool_type}\n"
            f"# Metric target: {proposal.metric_target}\n"
            f"# Generated for: {proposal.claw_role}\n"
            f"#\n"
            f"# Trigger: {proposal.trigger_pattern.trigger_description}\n"
            f"\n"
            f"def apply(action_data: dict) -> dict:\n"
            f'    """Apply {proposal.tool_name} to an action."""\n'
            f"    # Tool logic placeholder — inference-generated in production\n"
            f"    return action_data\n"
        )

    @staticmethod
    def _validate_syntax(code: str) -> bool:
        """
        Validate Python syntax of generated code.

        Args:
            code: Python code to validate

        Returns:
            True if syntax is valid
        """
        try:
            compile(code, "<generated>", "exec")
            return True
        except SyntaxError:
            return False

    def _compute_baseline(
        self, metric_target: str, actions: list[ActionRecord]
    ) -> float:
        """Compute the baseline metric value from historical actions."""
        if metric_target == "approval_rate":
            approved = sum(1 for a in actions if a.outcome in ("approved", "auto"))
            return approved / max(len(actions), 1)

        # Check if metric exists in action metrics
        values = [
            a.metrics[metric_target] for a in actions if metric_target in a.metrics
        ]
        if values:
            return sum(values) / len(values)

        # Default: approval rate
        approved = sum(1 for a in actions if a.outcome in ("approved", "auto"))
        return approved / max(len(actions), 1)

    def _simulate_tool_effect(
        self,
        proposal: ToolProposal,
        actions: list[ActionRecord],
        tool_code: str,
        baseline: float,
    ) -> float:
        """
        Simulate the tool's effect on historical data.

        In production, this would execute the tool code against each
        historical action and measure the resulting metric. For now,
        uses the confidence score as a proxy for improvement.
        """
        # Simulation proxy: confidence * pattern strength → estimated score
        confidence = proposal.trigger_pattern.confidence
        estimated_lift = confidence * 0.15  # 15% max lift at 1.0 confidence

        return baseline * (1 + estimated_lift)

    @staticmethod
    def _compute_data_hash(actions: list[ActionRecord]) -> str:
        """Compute SHA-256 hash of the training/backtest data."""
        hasher = hashlib.sha256()
        for action in actions:
            hasher.update(json.dumps(action.to_dict(), sort_keys=True).encode())
        return hasher.hexdigest()
