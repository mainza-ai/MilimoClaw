# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
SSRF Validator for MilimoClaw Hermes Network Policy.

Validates egress endpoints in milimo-mcp.yaml against NemoClaw's SSRF policy:
- Blocks private networks (RFC 1918, RFC 3927, RFC 4193)
- Blocks localhost/loopback (127.0.0.0/8, ::1)
- Blocks metadata services (169.254.169.254)
- Blocks link-local, multicast, benchmark ranges
- Validates DNS resolution to public IPs only

Based on NemoClaw's SSRF policy from @openclaw/plugin-sdk/infra/net/ssrf.ts
"""

from __future__ import annotations

import ipaddress
import logging
import socket
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("milimo.ssrf_validator")


# ============================================================================
# SSRF Policy Constants (matching NemoClaw's ssrf.ts)
# ============================================================================

# Private network ranges that should be blocked
PRIVATE_NETWORKS = [
    ipaddress.IPv4Network("10.0.0.0/8"),        # RFC 1918
    ipaddress.IPv4Network("172.16.0.0/12"),     # RFC 1918
    ipaddress.IPv4Network("192.168.0.0/16"),    # RFC 1918
    ipaddress.IPv4Network("127.0.0.0/8"),       # Loopback
    ipaddress.IPv4Network("169.254.0.0/16"),    # RFC 3927 Link-local
    ipaddress.IPv4Network("224.0.0.0/4"),       # Multicast
    ipaddress.IPv4Network("240.0.0.0/4"),       # Reserved
    ipaddress.IPv4Network("255.255.255.255/32"), # Broadcast
]

PRIVATE_IPV6_NETWORKS = [
    ipaddress.IPv6Network("::1/128"),           # Loopback
    ipaddress.IPv6Network("fe80::/10"),         # Link-local
    ipaddress.IPv6Network("fc00::/7"),          # ULA (RFC 4193)
    ipaddress.IPv6Network("ff00::/8"),          # Multicast
    ipaddress.IPv6Network("::ffff:0:0/96"),     # IPv4-mapped
    ipaddress.IPv6Network("2001:db8::/32"),     # Documentation (RFC 3849)
    ipaddress.IPv6Network("2001:10::/28"),      # ORCHID (RFC 4843)
    ipaddress.IPv6Network("2001:20::/28"),      # ORCHIDv2 (RFC 7343)
]

# Metadata service IPs (cloud provider instance metadata)
METADATA_IPS = [
    ipaddress.IPv4Address("169.254.169.254"),   # AWS/GCP/Azure
    ipaddress.IPv6Address("fd00:ec2::254"),     # AWS IPv6 metadata
]

# RFC 2544 Benchmark Range (should be blocked by default)
RFC2544_RANGE = ipaddress.IPv4Network("198.18.0.0/15")


@dataclass
class SSRFValidationResult:
    """Result of SSRF validation for a single endpoint."""
    host: str
    port: int
    protocol: str
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    resolved_ips: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "port": self.port,
            "protocol": self.protocol,
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "resolved_ips": self.resolved_ips,
        }


@dataclass
class SSRFPolicy:
    """SSRF validation policy matching NemoClaw's SsrFPolicy."""
    allow_private_network: bool = False
    dangerously_allow_private_network: bool = False
    allow_rfc2544_benchmark_range: bool = False
    allowed_hostnames: list[str] = field(default_factory=list)
    hostname_allowlist: list[str] = field(default_factory=list)

    # Additional Milimo-specific settings
    require_dns_resolution: bool = True
    allow_local_nim: bool = True  # Allow nim-service.local for local inference


@dataclass
class SSRFValidationReport:
    """Complete validation report for all endpoints."""
    total_endpoints: int = 0
    valid_endpoints: int = 0
    invalid_endpoints: int = 0
    results: list[SSRFValidationResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_endpoints": self.total_endpoints,
            "valid_endpoints": self.valid_endpoints,
            "invalid_endpoints": self.invalid_endpoints,
            "results": [r.to_dict() for r in self.results],
        }

    def has_failures(self) -> bool:
        return self.invalid_endpoints > 0


class SSRFValidator:
    """
    Validates network endpoints against SSRF policy.

    Reads milimo-mcp.yaml and validates each endpoint:
    1. Resolves hostname to IPs
    2. Checks against private network ranges
    3. Checks against metadata service IPs
    4. Validates port/protocol combinations
    5. Checks explicit deny rules
    """

    def __init__(self, policy: SSRFPolicy | None = None):
        self.policy = policy or SSRFPolicy()
        self._dns_cache: dict[str, list[str]] = {}

    def _is_private_ipv4(self, ip: ipaddress.IPv4Address) -> bool:
        """Check if IPv4 address is in private ranges."""
        for network in PRIVATE_NETWORKS:
            if ip in network:
                return True
        if not self.policy.allow_rfc2544_benchmark_range and ip in RFC2544_RANGE:
            return True
        return False

    def _is_private_ipv6(self, ip: ipaddress.IPv6Address) -> bool:
        """Check if IPv6 address is in private ranges."""
        for network in PRIVATE_IPV6_NETWORKS:
            if ip in network:
                return True
        return False

    def _is_metadata_ip(self, ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        """Check if IP is a cloud metadata service."""
        for metadata_ip in METADATA_IPS:
            if ip == metadata_ip:
                return True
        return False

    def _is_allowed_hostname(self, hostname: str) -> bool:
        """Check if hostname is explicitly allowed."""
        allowed = set(self.policy.allowed_hostnames + self.policy.hostname_allowlist)
        if hostname in allowed:
            return True
        # Check wildcard patterns (e.g., *.github.com)
        for pattern in allowed:
            if pattern.startswith("*."):
                domain = pattern[2:]
                if hostname == domain or hostname.endswith("." + domain):
                    return True
        return False

    def _resolve_hostname(self, hostname: str) -> list[str]:
        """Resolve hostname to IP addresses."""
        if hostname in self._dns_cache:
            return self._dns_cache[hostname]

        try:
            # Use getaddrinfo for both IPv4 and IPv6
            addrs = socket.getaddrinfo(hostname, None, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM)
            ips = list(set(addr[4][0] for addr in addrs))
            self._dns_cache[hostname] = ips
            return ips
        except socket.gaierror as e:
            logger.warning("DNS resolution failed for %s: %s", hostname, e)
            return []

    def _validate_ip(self, ip_str: str) -> list[str]:
        """Validate a single IP address, return list of errors."""
        errors = []
        try:
            ip = ipaddress.ip_address(ip_str)
            if isinstance(ip, ipaddress.IPv4Address):
                if self._is_private_ipv4(ip) and not self.policy.dangerously_allow_private_network:
                    errors.append(f"Private IPv4 address blocked: {ip}")
                if self._is_metadata_ip(ip):
                    errors.append(f"Metadata service IP blocked: {ip}")
            elif isinstance(ip, ipaddress.IPv6Address):
                if self._is_private_ipv6(ip) and not self.policy.dangerously_allow_private_network:
                    errors.append(f"Private IPv6 address blocked: {ip}")
                if self._is_metadata_ip(ip):
                    errors.append(f"Metadata service IP blocked: {ip}")
        except ValueError:
            errors.append(f"Invalid IP address: {ip_str}")
        return errors

    def _validate_endpoint(
        self,
        host: str,
        port: int,
        protocol: str,
        binaries: list[str],
        optional: bool = False
    ) -> SSRFValidationResult:
        """Validate a single endpoint from milimo-mcp.yaml."""
        result = SSRFValidationResult(
            host=host,
            port=port,
            protocol=protocol,
            valid=True,
        )

        # Check explicit deny rules first (these override everything)
        # In milimo-mcp.yaml, deny rules are global - check if this endpoint matches
        # For now, we just validate the allow rules

        # If optional and DNS fails, it's a warning not an error
        is_optional = optional

        # Check if hostname is explicitly allowed
        if not self._is_allowed_hostname(host):
            # Not in allowlist - will validate via DNS resolution
            pass

        # Resolve hostname
        if self.policy.require_dns_resolution:
            resolved_ips = self._resolve_hostname(host)
            result.resolved_ips = resolved_ips

            if not resolved_ips:
                if is_optional:
                    result.warnings.append(f"DNS resolution failed for optional host: {host}")
                else:
                    result.errors.append(f"DNS resolution failed for required host: {host}")
                    result.valid = False
            else:
                # Validate each resolved IP
                for ip in resolved_ips:
                    errors = self._validate_ip(ip)
                    if errors:
                        result.errors.extend(errors)
                        result.valid = False
        else:
            if is_optional:
                result.warnings.append(f"DNS resolution skipped for optional host: {host}")
            else:
                result.errors.append(f"DNS resolution required but disabled for: {host}")
                result.valid = False

        # Special handling for local NIM service
        if host == "nim-service.local" and not self.policy.allow_local_nim:
            result.errors.append("Local NIM service (nim-service.local) not allowed by policy")
            result.valid = False

        # Validate port
        if port < 1 or port > 65535:
            result.errors.append(f"Invalid port: {port}")
            result.valid = False

        # Validate protocol
        if protocol not in ("http", "https", "tcp", "udp"):
            result.errors.append(f"Unknown protocol: {protocol}")
            result.valid = False

        # HTTP on port 80/443 should use HTTPS
        if protocol == "http" and port == 443:
            result.warnings.append("HTTP on port 443 - should use HTTPS")
        if protocol == "https" and port == 80:
            result.warnings.append("HTTPS on port 80 - unexpected")

        return result

    def validate_policy_file(self, policy_path: Path) -> SSRFValidationReport:
        """Validate all endpoints in a milimo-mcp.yaml policy file."""
        with policy_path.open() as f:
            policy_data = yaml.safe_load(f)

        endpoints = policy_data.get("endpoints", [])
        deny_rules = policy_data.get("deny", [])

        report = SSRFValidationReport(total_endpoints=len(endpoints))

        for endpoint in endpoints:
            result = self._validate_endpoint(
                host=endpoint["host"],
                port=endpoint["port"],
                protocol=endpoint["protocol"],
                binaries=endpoint.get("binaries", []),
                optional=endpoint.get("optional", False)
            )
            report.results.append(result)
            if result.valid:
                report.valid_endpoints += 1
            else:
                report.invalid_endpoints += 1

        # Also validate deny rules don't conflict with allow rules
        self._check_deny_conflicts(endpoints, deny_rules, report)

        return report

    def _check_deny_conflicts(
        self,
        endpoints: list[dict[str, Any]],
        deny_rules: list[dict[str, Any]],
        report: SSRFValidationReport
    ) -> None:
        """Check for conflicts between allow and deny rules."""
        # For each deny rule, check if any allow endpoint matches
        for deny in deny_rules:
            deny_host = deny.get("host", "*")
            deny_port = deny.get("port")
            deny_protocol = deny.get("protocol")

            for endpoint in endpoints:
                if deny_host != "*" and deny_host != endpoint["host"]:
                    continue
                if deny_port is not None and deny_port != endpoint["port"]:
                    continue
                if deny_protocol is not None and deny_protocol != endpoint["protocol"]:
                    continue

                # Check if this is an explicit metadata service block
                if deny_host == "169.254.169.254":
                    # This is expected - metadata service should be blocked
                    continue

                # Log warning about potential conflict
                for result in report.results:
                    if result.host == endpoint["host"] and result.port == endpoint["port"]:
                        result.warnings.append(
                            f"Endpoint matches deny rule: {deny.get('reason', 'No reason')}"
                        )

    def print_report(self, report: SSRFValidationReport, verbose: bool = False) -> None:
        """Print validation report to console."""
        print(f"\n{'='*60}")
        print(f"SSRF Validation Report")
        print(f"{'='*60}")
        print(f"Total endpoints:  {report.total_endpoints}")
        print(f"Valid:            {report.valid_endpoints}")
        print(f"Invalid:          {report.invalid_endpoints}")
        print(f"{'='*60}")

        for result in report.results:
            status = "✓" if result.valid else "✗"
            print(f"\n{status} {result.host}:{result.port} ({result.protocol})")

            if result.resolved_ips:
                print(f"  Resolved IPs: {', '.join(result.resolved_ips)}")

            if result.errors:
                for error in result.errors:
                    print(f"  ERROR: {error}")

            if result.warnings and verbose:
                for warning in result.warnings:
                    print(f"  WARN: {warning}")

        print(f"\n{'='*60}")
        if report.has_failures():
            print("VALIDATION FAILED - Some endpoints are invalid")
        else:
            print("VALIDATION PASSED - All endpoints are valid")
        print(f"{'='*60}\n")


def main() -> int:
    """CLI entry point for SSRF validation."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate MilimoClaw Hermes network policy against SSRF rules")
    parser.add_argument(
        "policy",
        nargs="?",
        default="milimo-blueprint/policies/milimo-mcp.yaml",
        help="Path to milimo-mcp.yaml policy file"
    )
    parser.add_argument(
        "--policy",
        "-p",
        dest="policy_flag",
        help="Path to milimo-mcp.yaml policy file (alternative to positional)"
    )
    parser.add_argument(
        "--allow-private",
        action="store_true",
        help="Dangerously allow private network access (for testing)"
    )
    parser.add_argument(
        "--allow-rfc2544",
        action="store_true",
        help="Allow RFC 2544 benchmark range"
    )
    parser.add_argument(
        "--skip-dns",
        action="store_true",
        help="Skip DNS resolution (offline mode)"
    )
    parser.add_argument(
        "--allow-local-nim",
        action="store_true",
        help="Allow nim-service.local for local inference"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show warnings"
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output JSON report to file"
    )
    parser.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="Exit with error code if any warnings"
    )

    args = parser.parse_args()

    policy = SSRFPolicy(
        allow_private_network=False,
        dangerously_allow_private_network=args.allow_private,
        allow_rfc2544_benchmark_range=args.allow_rfc2544,
        require_dns_resolution=not args.skip_dns,
        allow_local_nim=args.allow_local_nim,
    )

    validator = SSRFValidator(policy)
    policy_path = Path(args.policy_flag or args.policy)

    if not policy_path.exists():
        print(f"Error: Policy file not found: {policy_path}")
        return 1

    report = validator.validate_policy_file(policy_path)
    validator.print_report(report, verbose=args.verbose)

    if args.output:
        import json
        with open(args.output, "w") as f:
            json.dump(report.to_dict(), f, indent=2)
        print(f"Report written to {args.output}")

    if report.has_failures() or (args.fail_on_warning and any(r.warnings for r in report.results)):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
