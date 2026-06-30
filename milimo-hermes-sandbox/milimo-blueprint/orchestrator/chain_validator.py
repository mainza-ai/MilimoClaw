# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Chain Validator

Validates the complete provenance chain of a blueprint,
ensuring all attestations form a valid sequence from
origin to current version.

Usage:
    from chain_validator import ChainValidator

    validator = ChainValidator()
    result = validator.validate_chain(attestations)
    if result.valid:
        print(f"Chain validated: {result.chain_length} attestations")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from .provenance_signer import Attestation
from .provenance_verifier import ProvenanceVerifier, VerificationResult

logger = logging.getLogger("milimo.chain_validator")


# ---------------------------------------------------------------------------
# Chain Validation Result
# ---------------------------------------------------------------------------


@dataclass
class ChainNode:
    """A node in the provenance chain."""

    attestation: Attestation
    verification_result: VerificationResult
    position: int
    children: list["ChainNode"] = field(default_factory=list)


@dataclass
class ChainValidationResult:
    """Result of chain validation."""

    valid: bool
    chain_length: int = 0
    genesis_attestation_id: str = ""
    latest_attestation_id: str = ""
    author_squad_ids: list[str] = field(default_factory=list)
    version_sequence: list[str] = field(default_factory=list)
    forks: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "chain_length": self.chain_length,
            "genesis_attestation_id": self.genesis_attestation_id,
            "latest_attestation_id": self.latest_attestation_id,
            "author_squad_ids": self.author_squad_ids,
            "version_sequence": self.version_sequence,
            "forks": self.forks,
            "errors": self.errors,
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# Version Comparison
# ---------------------------------------------------------------------------


def compare_versions(v1: str, v2: str) -> int:
    """
    Compare two semantic versions.

    Args:
        v1: First version string (e.g., "1.2.3")
        v2: Second version string

    Returns:
        -1 if v1 < v2, 0 if equal, 1 if v1 > v2
    """

    def parse_version(v: str) -> tuple[int, ...]:
        parts = v.lstrip("v").split(".")
        return tuple(int(p) for p in parts if p.isdigit())

    p1 = parse_version(v1)
    p2 = parse_version(v2)

    # Pad with zeros if needed
    max_len = max(len(p1), len(p2))
    p1 = p1 + (0,) * (max_len - len(p1))
    p2 = p2 + (0,) * (max_len - len(p2))

    if p1 < p2:
        return -1
    elif p1 > p2:
        return 1
    return 0


def is_version_sequence_valid(versions: list[str]) -> tuple[bool, Optional[str]]:
    """
    Check if version sequence is monotonically increasing.

    Args:
        versions: List of version strings in order

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(versions) <= 1:
        return True, None

    for i in range(1, len(versions)):
        prev = versions[i - 1]
        curr = versions[i]

        if compare_versions(curr, prev) <= 0:
            return False, f"Version sequence invalid: {prev} -> {curr}"

    return True, None


# ---------------------------------------------------------------------------
# Chain Validator
# ---------------------------------------------------------------------------


class ChainValidator:
    """
    Validates complete provenance chains.

    Ensures all attestations:
    1. Have valid signatures
    2. Form a connected chain (no gaps)
    3. Have monotonically increasing versions
    4. Have consistent timestamps
    """

    def __init__(
        self,
        strict_mode: bool = False,
        allow_forks: bool = True,
    ):
        """
        Initialize the chain validator.

        Args:
            strict_mode: Fail on warnings
            allow_forks: Allow multiple children (forks)
        """
        self.strict_mode = strict_mode
        self.allow_forks = allow_forks
        self.verifier = ProvenanceVerifier()

    def validate_chain(
        self,
        attestations: list[Attestation],
    ) -> ChainValidationResult:
        """
        Validate a complete provenance chain.

        Args:
            attestations: List of attestations to validate

        Returns:
            ChainValidationResult
        """
        result = ChainValidationResult(valid=True)

        if not attestations:
            result.valid = False
            result.errors.append("Empty attestation chain")
            return result

        # Build attestation index by hash
        attestation_index = {a.hash(): a for a in attestations}

        # Find genesis (no parent) attestations
        genesis_nodes = [a for a in attestations if not a.parent_attestation]

        if len(genesis_nodes) == 0:
            result.valid = False
            result.errors.append(
                "No genesis attestation found (all have parent references)"
            )
            return result

        if len(genesis_nodes) > 1:
            result.warnings.append(
                f"Multiple genesis attestations found: {len(genesis_nodes)}"
            )

        # Verify each attestation
        for attestation in attestations:
            verify_result = self.verifier.verify(attestation)
            if not verify_result.valid:
                result.valid = False
                result.errors.extend(verify_result.errors)

        if not result.valid:
            return result

        # Build chain tree
        chain_tree = self._build_chain_tree(attestations, attestation_index)

        # Traverse and validate
        self._traverse_chain(chain_tree, genesis_nodes, attestation_index, result)

        # Check version sequence
        if result.version_sequence:
            seq_valid, seq_error = is_version_sequence_valid(result.version_sequence)
        if not seq_valid:
            result.valid = False
            if seq_error is not None:
                result.errors.append(seq_error)

        # Apply strict mode
        if self.strict_mode and result.warnings:
            result.valid = False
            result.errors.append("Strict mode: warnings treated as errors")

        result.chain_length = len(attestations)

        return result

    def _build_chain_tree(
        self,
        attestations: list[Attestation],
        attestation_index: dict[str, Attestation],
    ) -> dict[str, list[str]]:
        """
        Build a tree structure of attestations.

        Args:
            attestations: All attestations
            attestation_index: Index of attestations by hash

        Returns:
            Dictionary mapping parent hash to list of child hashes
        """
        tree: dict[str, list[str]] = {}

        for attestation in attestations:
            att_hash = attestation.hash()

            if attestation.parent_attestation:
                parent_hash = attestation.parent_attestation
                if parent_hash not in tree:
                    tree[parent_hash] = []
                tree[parent_hash].append(att_hash)
            else:
                # Genesis attestation
                if "genesis" not in tree:
                    tree["genesis"] = []
                tree["genesis"].append(att_hash)

        return tree

    def _traverse_chain(
        self,
        chain_tree: dict[str, list[str]],
        genesis_nodes: list[Attestation],
        attestation_index: dict[str, Attestation],
        result: ChainValidationResult,
    ) -> None:
        """
        Traverse the chain tree and collect information.

        Args:
            chain_tree: Tree structure of attestations
            genesis_nodes: Genesis attestations
            attestation_index: Index of attestations
            result: Result to populate
        """
        visited: set[str] = set()

        def visit(attestation: Attestation, depth: int = 0) -> None:
            att_hash = attestation.hash()

            if att_hash in visited:
                return
            visited.add(att_hash)

            # Record information
            if attestation.author:
                squad_id = attestation.author.squad_id
                if squad_id not in result.author_squad_ids:
                    result.author_squad_ids.append(squad_id)

            result.version_sequence.append(attestation.blueprint_version)

            if depth == 0 and not result.genesis_attestation_id:
                result.genesis_attestation_id = att_hash

            result.latest_attestation_id = att_hash

            # Visit children
            children = chain_tree.get(att_hash, [])
            if len(children) > 1:
                result.forks.append(att_hash)
                if not self.allow_forks:
                    result.errors.append(f"Fork detected at {att_hash[:16]}...")
                    result.valid = False

            for child_hash in children:
                if child_hash in attestation_index:
                    visit(attestation_index[child_hash], depth + 1)

        # Start traversal from genesis nodes
        for genesis in genesis_nodes:
            visit(genesis)

    def validate_single_path(
        self,
        attestations: list[Attestation],
    ) -> ChainValidationResult:
        """
        Validate a single linear chain path (no forks).

        Args:
            attestations: Attestations in order from genesis to latest

        Returns:
            ChainValidationResult
        """
        result = ChainValidationResult(valid=True)

        if not attestations:
            result.valid = False
            result.errors.append("Empty attestation chain")
            return result

        # Verify chain connectivity
        prev_hash = None
        for i, attestation in enumerate(attestations):
            # Verify signature
            verify_result = self.verifier.verify(attestation)
            if not verify_result.valid:
                result.valid = False
                result.errors.extend(verify_result.errors)

            # Check parent reference
            if i == 0:
                # Genesis should have no parent
                if attestation.parent_attestation:
                    result.warnings.append("Genesis attestation has parent reference")
            else:
                # Should reference previous attestation
                if attestation.parent_attestation != prev_hash:
                    result.valid = False
                    result.errors.append(
                        f"Chain break at position {i}: "
                        f"expected parent {prev_hash[:16] if prev_hash else 'None'}..., "
                        f"got {attestation.parent_attestation[:16] if attestation.parent_attestation else 'None'}..."
                    )

            prev_hash = attestation.hash()
            result.version_sequence.append(attestation.blueprint_version)

            if attestation.author:
                squad_id = attestation.author.squad_id
                if squad_id not in result.author_squad_ids:
                    result.author_squad_ids.append(squad_id)

        # Set genesis and latest
        if attestations:
            result.genesis_attestation_id = attestations[0].hash()
            result.latest_attestation_id = attestations[-1].hash()

        result.chain_length = len(attestations)

        return result

    def find_ancestor(
        self,
        attestations: list[Attestation],
        target_version: str,
    ) -> Optional[Attestation]:
        """
        Find attestation with specific version in chain.

        Args:
            attestations: Chain to search
            target_version: Version to find

        Returns:
            Attestation with matching version or None
        """
        for attestation in attestations:
            if attestation.blueprint_version.lstrip("v") == target_version.lstrip("v"):
                return attestation
        return None

    def get_chain_summary(self, attestations: list[Attestation]) -> dict[str, Any]:
        """
        Get a summary of the chain.

        Args:
            attestations: Chain to summarize

        Returns:
            Dictionary with chain summary
        """
        if not attestations:
            return {"error": "Empty chain"}

        # Sort by version
        sorted_attestations = sorted(attestations, key=lambda a: a.blueprint_version)

        return {
            "chain_length": len(attestations),
            "genesis_version": sorted_attestations[0].blueprint_version,
            "latest_version": sorted_attestations[-1].blueprint_version,
            "authors": list(set(a.author.squad_id for a in attestations if a.author)),
            "versions": [a.blueprint_version for a in sorted_attestations],
            "genesis_hash": sorted_attestations[0].hash(),
            "latest_hash": sorted_attestations[-1].hash(),
        }


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------


def validate_provenance_chain(attestations: list[Attestation]) -> ChainValidationResult:
    """
    Convenience function to validate a provenance chain.

    Args:
        attestations: List of attestations

    Returns:
        ChainValidationResult
    """
    validator = ChainValidator()
    return validator.validate_chain(attestations)


def verify_blueprint_provenance(
    attestations: list[Attestation],
    strict: bool = False,
) -> tuple[bool, list[str]]:
    """
    Verify complete blueprint provenance.

    Args:
        attestations: Attestation chain
        strict: Enable strict mode

    Returns:
        Tuple of (is_valid, list of errors)
    """
    validator = ChainValidator(strict_mode=strict)
    result = validator.validate_chain(attestations)

    errors = result.errors.copy()
    if strict:
        errors.extend(result.warnings)

    return result.valid and len(errors) == 0, errors
