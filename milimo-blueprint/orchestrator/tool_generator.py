#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Tool Generator

Generates Python tool implementations from specifications using LLM.
Part of the self-evolution engine's BUILD stage.

Usage:
    from tool_generator import ToolGenerator

    generator = ToolGenerator()
    result = generator.generate(tool_spec)

    if result.success:
        print(result.code)
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from string import Template
from typing import Any, Literal, Optional

logger = logging.getLogger("milimo.tool_generator")


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


ToolType = Literal[
    "classifier",
    "predictor",
    "optimizer",
    "detector",
    "generator",
    "transformer",
    "aggregator",
]


@dataclass
class GenerationConfig:
    """Configuration for tool generation."""

    template_dir: str = ""
    max_code_length: int = 10000
    max_execution_time_ms: int = 5000
    max_memory_mb: int = 200
    require_type_hints: bool = True
    require_docstrings: bool = True
    forbid_network: bool = True
    forbid_filesystem_write: bool = True
    forbid_arbitrary_exec: bool = True


@dataclass
class GenerationResult:
    """Result of tool generation."""

    success: bool
    code: str = ""
    error: str = ""
    warnings: list[str] = field(default_factory=list)
    validation_passed: bool = False
    test_passed: bool = False
    estimated_performance: float = 0.0


@dataclass
class ToolSpec:
    """Specification for a tool to be generated."""

    name: str
    tool_type: ToolType
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    permissions: dict[str, Any] = field(default_factory=dict)
    pattern_description: str = ""
    frequency: int = 0
    time_period: str = ""
    evolution_cycle: str = ""
    test_cases: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Prompt Builder
# ---------------------------------------------------------------------------


class PromptBuilder:
    """Builds prompts for tool generation."""

    def __init__(self, template_dir: str | Path | None = None):
        if template_dir:
            self._template_dir = Path(template_dir)
        else:
            # Default to prompts/tool-generation relative to this file
            self._template_dir = (
                Path(__file__).parent.parent / "prompts" / "tool-generation"
            )

    def build_prompt(self, spec: ToolSpec) -> str:
        """Build a prompt for the given tool specification."""
        template_name = f"{spec.tool_type}.txt"
        template_path = self._template_dir / template_name

        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        template_content = template_path.read_text()

        # Prepare substitution variables
        variables = {
            "tool_name": spec.name,
            "description": spec.description,
            "input_schema": json.dumps(spec.input_schema, indent=2),
            "output_schema": json.dumps(spec.output_schema, indent=2),
            "pattern_description": spec.pattern_description,
            "frequency": str(spec.frequency),
            "time_period": spec.time_period,
            "evolution_cycle": spec.evolution_cycle,
            # Tool-type specific variables
            **self._get_type_specific_vars(spec),
        }

        # Apply substitutions using safe template
        prompt = self._safe_substitute(template_content, variables)

        return prompt

    def _get_type_specific_vars(self, spec: ToolSpec) -> dict[str, str]:
        """Get type-specific template variables."""
        vars_dict: dict[str, str] = {}

        if spec.tool_type == "classifier":
            # Extract target classes from output schema
            target_classes = spec.output_schema.get("properties", {}).get(
                "predicted_class", {}
            )
            if "enum" in target_classes:
                vars_dict["target_classes"] = str(target_classes["enum"])
            else:
                vars_dict["target_classes"] = "[]"
            vars_dict["performance_impact"] = spec.metadata.get(
                "performance_impact", "unknown"
            )

        elif spec.tool_type == "predictor":
            vars_dict["target_value"] = spec.metadata.get("target_value", "value")
            vars_dict["correlation_coefficient"] = str(
                spec.metadata.get("correlation", 0.0)
            )
            vars_dict["sample_size"] = str(spec.metadata.get("sample_size", 0))

        elif spec.tool_type == "optimizer":
            vars_dict["optimization_target"] = spec.metadata.get(
                "optimization_target", "target"
            )
            vars_dict["constraints"] = json.dumps(spec.metadata.get("constraints", {}))
            vars_dict["baseline_performance"] = str(
                spec.metadata.get("baseline_performance", 0)
            )
            vars_dict["optimization_potential"] = str(
                spec.metadata.get("optimization_potential", 0)
            )

        elif spec.tool_type == "detector":
            vars_dict["detection_target"] = spec.metadata.get(
                "detection_target", "anomaly"
            )
            vars_dict["min_true_positive_rate"] = str(spec.metadata.get("min_tpr", 0.8))
            vars_dict["max_false_positive_rate"] = str(
                spec.metadata.get("max_fpr", 0.1)
            )

        elif spec.tool_type == "generator":
            vars_dict["content_type"] = spec.metadata.get("content_type", "content")
            vars_dict["style_constraints"] = json.dumps(
                spec.metadata.get("style_constraints", {})
            )
            vars_dict["quality_metric"] = spec.metadata.get(
                "quality_metric", "approval_rate"
            )
            vars_dict["approval_rate"] = str(spec.metadata.get("approval_rate", 0.0))

        # Add test input example if available
        if spec.test_cases:
            vars_dict["test_input_example"] = json.dumps(
                spec.test_cases[0].get("input", {}), indent=4
            )
        else:
            vars_dict["test_input_example"] = "{}"

        return vars_dict

    def _safe_substitute(self, template: str, variables: dict[str, str]) -> str:
        """Safely substitute variables in template."""
        # Use string replace for {{var}} pattern
        result = template
        for key, value in variables.items():
            result = result.replace("{{" + key + "}}", value)
        return result


# ---------------------------------------------------------------------------
# Code Validator
# ---------------------------------------------------------------------------


class CodeValidator:
    """Validates generated tool code for security and correctness."""

    FORBIDDEN_IMPORTS = {
        "subprocess",
        "os.system",
        "eval",
        "exec",
        "compile",
        "socket",
        "urllib",
        "requests",
        "httpx",
        "aiohttp",
        "pickle",
        "shelve",
        "marshal",
    }

    FORBIDDEN_PATTERNS = [
        r"\bimport\s+subprocess\b",
        r"\bfrom\s+subprocess\b",
        r"\bimport\s+socket\b",
        r"\bfrom\s+socket\b",
        r"\bimport\s+urllib\b",
        r"\bfrom\s+urllib\b",
        r"\bimport\s+requests\b",
        r"\bfrom\s+requests\b",
        r"\bos\.system\s*\(",
        r"\beval\s*\(",
        r"\bexec\s*\(",
        r"\bcompile\s*\(",
        r"__import__\s*\(",
        r"open\s*\([^)]*[\'\"]w[\'\"]",
        r"\.write\s*\(",
        r"\.popen\s*\(",
    ]

    def validate(self, code: str, config: GenerationConfig) -> tuple[bool, list[str]]:
        """
        Validate generated code for security and quality.

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues: list[str] = []

        # Check code length
        if len(code) > config.max_code_length:
            issues.append(
                f"Code exceeds maximum length: {len(code)} > {config.max_code_length}"
            )

        # Check for forbidden patterns
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, code):
                issues.append(f"Forbidden pattern detected: {pattern}")

        # Check for type hints
        if config.require_type_hints:
            if (
                "def run(" in code
                and ": " not in code.split("def run(")[1].split(")")[0]
            ):
                if "->" not in code.split("def run(")[1].split("\n")[0]:
                    issues.append("Missing type hints for run function")

        # Check for docstrings
        if config.require_docstrings:
            if '"""' not in code.split("def run(")[1].split("\n")[0:5]:
                issues.append("Missing docstring for run function")

        # Try to parse the code
        try:
            compile(code, "<generated>", "exec")
        except SyntaxError as e:
            issues.append(f"Syntax error: {e}")

        return len(issues) == 0, issues


# ---------------------------------------------------------------------------
# Code Tester
# ---------------------------------------------------------------------------


class CodeTester:
    """Tests generated tool code in an isolated environment."""

    def __init__(self, timeout_seconds: int = 5):
        self._timeout = timeout_seconds

    def test(
        self, code: str, test_cases: list[dict[str, Any]]
    ) -> tuple[bool, list[str]]:
        """
        Run test cases against generated code.

        Returns:
            Tuple of (all_passed, list_of_failures)
        """
        failures: list[str] = []

        if not test_cases:
            return True, ["No test cases provided"]

        # Create temporary directory for isolated execution
        with tempfile.TemporaryDirectory() as tmpdir:
            tool_file = Path(tmpdir) / "generated_tool.py"
            tool_file.write_text(code)

            for i, test_case in enumerate(test_cases):
                test_input = test_case.get("input", {})
                expected = test_case.get("expected_output", {})
                validation = test_case.get("validation", "schema_only")

                try:
                    # Run the tool with test input
                    test_script = f'''
import sys
sys.path.insert(0, "{tmpdir}")
from generated_tool import run
import json

result = run({json.dumps(test_input)})
print(json.dumps(result))
'''
                    result = subprocess.run(
                        [sys.executable, "-c", test_script],
                        capture_output=True,
                        text=True,
                        timeout=self._timeout,
                        cwd=tmpdir,
                    )

                    if result.returncode != 0:
                        failures.append(f"Test {i}: Execution failed: {result.stderr}")
                        continue

                    output = json.loads(result.stdout)

                    # Validate output
                    if validation == "exact":
                        if output != expected:
                            failures.append(
                                f"Test {i}: Output mismatch. Expected {expected}, got {output}"
                            )
                    elif validation == "partial":
                        for key, value in expected.items():
                            if key not in output:
                                failures.append(
                                    f"Test {i}: Missing key '{key}' in output"
                                )
                            elif output[key] != value:
                                failures.append(
                                    f"Test {i}: Key '{key}' mismatch. Expected {value}, got {output[key]}"
                                )
                    # schema_only: just check it's valid JSON (already done)

                except subprocess.TimeoutExpired:
                    failures.append(f"Test {i}: Execution timeout")
                except json.JSONDecodeError as e:
                    failures.append(f"Test {i}: Invalid JSON output: {e}")
                except Exception as e:
                    failures.append(f"Test {i}: Unexpected error: {e}")

        return len(failures) == 0, failures


# ---------------------------------------------------------------------------
# Tool Generator
# ---------------------------------------------------------------------------


class ToolGenerator:
    """
    Generates tool implementations using LLM inference.

    Coordinates:
    1. Building prompts from specifications
    2. Calling LLM for code generation
    3. Validating generated code
    4. Testing generated code
    """

    def __init__(
        self,
        config: GenerationConfig | None = None,
        template_dir: str | Path | None = None,
        inference_client: Any | None = None,
    ):
        self._config = config or GenerationConfig()
        self._prompt_builder = PromptBuilder(template_dir)
        self._validator = CodeValidator()
        self._tester = CodeTester()
        self._inference_client = inference_client

    def generate(self, spec: ToolSpec) -> GenerationResult:
        """
        Generate a tool implementation from a specification.

        Args:
            spec: Tool specification

        Returns:
            GenerationResult with generated code or error
        """
        warnings: list[str] = []

        # 1. Build prompt
        try:
            prompt = self._prompt_builder.build_prompt(spec)
        except FileNotFoundError as e:
            return GenerationResult(
                success=False,
                error=str(e),
            )

        # 2. Call LLM for generation
        code = self._call_llm(prompt, spec.tool_type)

        if not code:
            return GenerationResult(
                success=False,
                error="LLM returned empty response",
                warnings=warnings,
            )

        # Extract code from markdown if present
        code = self._extract_code(code)

        # 3. Validate generated code
        valid, issues = self._validator.validate(code, self._config)
        if not valid:
            return GenerationResult(
                success=False,
                code=code,
                error="Validation failed: " + "; ".join(issues),
                warnings=warnings,
            )

        warnings.extend(issues)

        # 4. Test generated code
        if spec.test_cases:
            passed, failures = self._tester.test(code, spec.test_cases)
            if not passed:
                warnings.extend(failures)
                # Still return success but with warnings
        else:
            passed = True
            warnings.append("No test cases provided")

        return GenerationResult(
            success=True,
            code=code,
            warnings=warnings,
            validation_passed=valid,
            test_passed=passed,
            estimated_performance=self._estimate_performance(code, spec),
        )

    def _call_llm(self, prompt: str, tool_type: str) -> str:
        """
        Call LLM for code generation.

        Routes through NemoClaw's NvidiaInferenceClient when available,
        otherwise falls back to template-based generation.
        """
        if self._inference_client is not None:
            try:
                result = self._inference_client.complete(
                    prompt=prompt,
                    data_type="source_code_generation",
                    system_prompt=(
                        "You are a Python tool code generator for an AI squad system. "
                        "Generate only valid Python code. Include type hints and docstrings. "
                        "The tool must expose a `run(input_data: dict) -> dict` function."
                    ),
                )
                if result:
                    return result
                logger.warning(
                    "Inference client returned empty, falling back to template"
                )
            except Exception as e:
                logger.warning(
                    "Inference call failed: %s — falling back to template", e
                )

        return self._generate_template_code(prompt, tool_type)

    def _generate_template_code(self, prompt: str, tool_type: str) -> str:
        """Generate template code for testing without LLM."""
        # This is a fallback for testing/development
        # Real implementation would use LLM inference

        if tool_type == "classifier":
            return textwrap.dedent('''
                """
                Generated Classifier Tool

                Generated by Milimo Claw Self-Evolution Engine
                """

                from typing import TypedDict, Literal
                from dataclasses import dataclass


                class Input(TypedDict):
                    text: str


                class Output(TypedDict):
                    predicted_class: str
                    confidence: float
                    reasoning: str


                def run(input_data: Input) -> Output:
                    """
                    Classify the input text.

                    Args:
                        input_data: Input containing text to classify

                    Returns:
                        Classification result with confidence score
                    """
                    text = input_data.get("text", "").lower()

                    # Simple rule-based classification
                    if any(word in text for word in ["urgent", "asap", "deadline"]):
                        return {
                            "predicted_class": "urgent",
                            "confidence": 0.85,
                            "reasoning": "Contains urgency indicators"
                        }
                    elif any(word in text for word in ["question", "help", "how"]):
                        return {
                            "predicted_class": "question",
                            "confidence": 0.80,
                            "reasoning": "Contains question indicators"
                        }
                    else:
                        return {
                            "predicted_class": "normal",
                            "confidence": 0.70,
                            "reasoning": "No special indicators detected"
                        }


                if __name__ == "__main__":
                    result = run({"text": "This is urgent, please respond ASAP"})
                    print(result)
            ''').strip()

        elif tool_type == "predictor":
            return textwrap.dedent('''
                """
                Generated Predictor Tool

                Generated by Milimo Claw Self-Evolution Engine
                """

                from typing import TypedDict


                class Input(TypedDict):
                    historical_values: list[float]
                    context: dict


                class Output(TypedDict):
                    predicted_value: float
                    confidence_interval: tuple[float, float]
                    confidence: float
                    feature_importance: dict[str, float]


                def run(input_data: Input) -> Output:
                    """
                    Predict future value based on historical data.

                    Args:
                        input_data: Historical values and context

                    Returns:
                        Prediction with confidence interval
                    """
                    values = input_data.get("historical_values", [0.0])

                    if not values:
                        return {
                            "predicted_value": 0.0,
                            "confidence_interval": (0.0, 0.0),
                            "confidence": 0.0,
                            "feature_importance": {}
                        }

                    # Simple moving average prediction
                    avg = sum(values[-5:]) / min(len(values), 5)
                    std = (sum((v - avg) ** 2 for v in values[-5:]) / min(len(values), 5)) ** 0.5

                    return {
                        "predicted_value": round(avg, 2),
                        "confidence_interval": (round(avg - 1.96 * std, 2), round(avg + 1.96 * std, 2)),
                        "confidence": 0.75,
                        "feature_importance": {"historical_average": 0.6, "recent_trend": 0.4}
                    }
            ''').strip()

        elif tool_type == "detector":
            return textwrap.dedent('''
                """
                Generated Detector Tool

                Generated by Milimo Claw Self-Evolution Engine
                """

                from typing import TypedDict, Literal

                Severity = Literal["low", "medium", "high", "critical"]


                class Input(TypedDict):
                    metrics: dict[str, float]
                    threshold_config: dict[str, float]


                class Output(TypedDict):
                    detected: bool
                    severity: Severity
                    confidence: float
                    indicators: list[str]
                    remediation: str


                def run(input_data: Input) -> Output:
                    """
                    Detect anomalies in metrics.

                    Args:
                        input_data: Metrics and threshold configuration

                    Returns:
                        Detection result with severity and remediation
                    """
                    metrics = input_data.get("metrics", {})
                    thresholds = input_data.get("threshold_config", {})

                    indicators = []
                    max_severity: Severity = "low"

                    for metric, value in metrics.items():
                        threshold = thresholds.get(metric, float('inf'))
                        if value > threshold:
                            indicators.append(f"{metric}={value} exceeds threshold {threshold}")
                            if value > threshold * 2:
                                max_severity = "critical"
                            elif value > threshold * 1.5:
                                max_severity = "high"
                            elif value > threshold * 1.2:
                                max_severity = "medium"

                    return {
                        "detected": len(indicators) > 0,
                        "severity": max_severity,
                        "confidence": 0.8 if indicators else 0.9,
                        "indicators": indicators,
                        "remediation": "Review threshold configuration and investigate root cause" if indicators else "No action needed"
                    }
            ''').strip()

        else:
            # Generic template
            return textwrap.dedent(f'''
                """
                Generated {tool_type.title()} Tool

                Generated by Milimo Claw Self-Evolution Engine
                """

                from typing import Any, dict


                def run(input_data: dict[str, Any]) -> dict[str, Any]:
                    """
                    Process input and return result.

                    Args:
                        input_data: Input data

                    Returns:
                        Processing result
                    """
                    # Placeholder implementation
                    return {{"result": "generated", "type": "{tool_type}"}}
            ''').strip()

    def _extract_code(self, response: str) -> str:
        """Extract Python code from LLM response."""
        # Check for markdown code blocks
        code_block_pattern = r"```python\s*\n(.*?)\n```"
        matches = re.findall(code_block_pattern, response, re.DOTALL)

        if matches:
            return matches[0]

        # Check for any code block
        code_block_pattern = r"```\s*\n(.*?)\n```"
        matches = re.findall(code_block_pattern, response, re.DOTALL)

        if matches:
            return matches[0]

        # Return as-is if no code blocks found
        return response.strip()

    def _estimate_performance(self, code: str, spec: ToolSpec) -> float:
        """Estimate performance improvement from the tool."""
        # Simple heuristic based on code complexity and type
        base_improvement = {
            "classifier": 5.0,
            "predictor": 7.0,
            "optimizer": 10.0,
            "detector": 6.0,
            "generator": 4.0,
        }

        base = base_improvement.get(spec.tool_type, 5.0)

        # Adjust based on frequency
        if spec.frequency > 100:
            base *= 1.2
        elif spec.frequency > 50:
            base *= 1.1

        return round(base, 1)


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------


def generate_tool(
    name: str,
    tool_type: ToolType,
    description: str,
    input_schema: dict[str, Any],
    output_schema: dict[str, Any],
    **kwargs: Any,
) -> GenerationResult:
    """
    Convenience function to generate a tool.

    Args:
        name: Tool name
        tool_type: Type of tool
        description: Tool description
        input_schema: Input JSON schema
        output_schema: Output JSON schema
        **kwargs: Additional spec parameters

    Returns:
        GenerationResult
    """
    spec = ToolSpec(
        name=name,
        tool_type=tool_type,
        description=description,
        input_schema=input_schema,
        output_schema=output_schema,
        **kwargs,
    )

    generator = ToolGenerator()
    return generator.generate(spec)
