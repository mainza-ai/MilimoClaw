#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Region Detector

Detects the optimal region for a claw based on IP geolocation, latency
probes, and manual configuration. Used for multi-region mesh routing.

Usage:
    from orchestrator.region_detector import RegionDetector, RegionInfo

    detector = RegionDetector(regions_config_path="regions.yaml")
    region = detector.detect()
    print(f"Detected region: {region.region_id}")
"""

from __future__ import annotations

import json
import logging
import os
import socket
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import urllib.request
import urllib.error

import yaml

logger = logging.getLogger("milimo.region_detector")


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

@dataclass
class RegionInfo:
    """Information about a detected region."""

    region_id: str
    region_code: str
    country: str
    city: str = ""
    timezone: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    endpoint: str = ""
    relay: str = ""
    fallback_region: str = ""
    latency_samples: dict[str, list[float]] = field(default_factory=dict)
    detected_at: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "region_id": self.region_id,
            "region_code": self.region_code,
            "country": self.country,
            "city": self.city,
            "timezone": self.timezone,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "endpoint": self.endpoint,
            "relay": self.relay,
            "fallback_region": self.fallback_region,
            "latency_samples": self.latency_samples,
            "detected_at": self.detected_at,
            "confidence": self.confidence,
        }


@dataclass
class RegionConfig:
    """Configuration for a region."""

    region_id: str
    code: str
    endpoint: str
    relay: str = ""
    fallback_region: str = ""
    country: str = ""
    city: str = ""

    @classmethod
    def from_dict(cls, region_id: str, data: dict[str, Any]) -> RegionConfig:
        return cls(
            region_id=region_id,
            code=data.get("code", region_id),
            endpoint=data.get("endpoint", ""),
            relay=data.get("relay", ""),
            fallback_region=data.get("fallback_region", ""),
            country=data.get("country", ""),
            city=data.get("city", ""),
        )


# ---------------------------------------------------------------------------
# Region Detector
# ---------------------------------------------------------------------------

class RegionDetector:
    """
    Detects the optimal region for a claw.

    Detection methods (in order of priority):
    1. Manual configuration (MILIMO_REGION env var)
    2. Configuration file (region field in mesh config)
    3. Latency probing to all regions
    4. IP geolocation lookup
    5. Default region
    """

    KNOWN_REGIONS = {
        "us-east-1": {"code": "use1", "country": "US", "lat": 39.04, "lon": -77.49},
        "us-west-2": {"code": "usw2", "country": "US", "lat": 45.52, "lon": -122.68},
        "eu-west-1": {"code": "euw1", "country": "IE", "lat": 53.35, "lon": -6.26},
        "eu-central-1": {"code": "euc1", "country": "DE", "lat": 50.11, "lon": 8.68},
        "ap-southeast-1": {"code": "apse1", "country": "SG", "lat": 1.35, "lon": 103.82},
        "ap-northeast-1": {"code": "apne1", "country": "JP", "lat": 35.69, "lon": 139.69},
        "sa-east-1": {"code": "sae1", "country": "BR", "lat": -23.55, "lon": -46.63},
    }

    PROBE_ENDPOINTS = [
        "https://aws-latency.com/probe",
        "https://ping.aws.amazon.com",
    ]

    GEOLOCATION_SERVICES = [
        "https://ipapi.co/json/",
        "https://ip-api.com/json/",
    ]

    def __init__(
        self,
        regions_config_path: Optional[str] = None,
        default_region: str = "us-east-1",
        probe_timeout_ms: int = 5000,
    ) -> None:
        self.default_region = default_region
        self.probe_timeout_ms = probe_timeout_ms
        self._regions_config: dict[str, RegionConfig] = {}
        self._cache: Optional[RegionInfo] = None
        self._cache_time: Optional[datetime] = None
        self._cache_ttl_seconds = 3600

        if regions_config_path:
            self._load_regions_config(regions_config_path)

    def _load_regions_config(self, path: str) -> None:
        """Load regions configuration from YAML file."""
        try:
            config_path = Path(path)
            if config_path.exists():
                with config_path.open() as f:
                    data = yaml.safe_load(f) or {}
                    regions = data.get("regions", {})
                    for region_id, region_data in regions.items():
                        self._regions_config[region_id] = RegionConfig.from_dict(region_id, region_data)
                    logger.info("Loaded %d region configurations", len(self._regions_config))
        except Exception as e:
            logger.warning("Failed to load regions config: %s", e)

    def detect(self, force_refresh: bool = False) -> RegionInfo:
        """
        Detect the optimal region for this claw.

        Args:
            force_refresh: Skip cache and re-detect

        Returns:
            RegionInfo with detected region details
        """
        if not force_refresh and self._is_cache_valid():
            assert self._cache is not None
            return self._cache

        region_id = self._detect_region_id()

        region_info = self._build_region_info(region_id)
        region_info.detected_at = datetime.now(timezone.utc).isoformat()

        self._cache = region_info
        self._cache_time = datetime.now(timezone.utc)

        logger.info("Detected region: %s (confidence: %.2f)", region_id, region_info.confidence)
        return region_info

    def _is_cache_valid(self) -> bool:
        """Check if cached region info is still valid."""
        if self._cache is None or self._cache_time is None:
            return False
        elapsed = (datetime.now(timezone.utc) - self._cache_time).total_seconds()
        return elapsed < self._cache_ttl_seconds

    def _detect_region_id(self) -> str:
        """Detect region ID using multiple methods."""
        region = os.environ.get("MILIMO_REGION", "")
        if region and self._is_valid_region(region):
            logger.debug("Region from environment: %s", region)
            return region

        region = self._detect_by_latency()
        if region:
            logger.debug("Region from latency probe: %s", region)
            return region

        region = self._detect_by_geolocation()
        if region:
            logger.debug("Region from geolocation: %s", region)
            return region

        logger.debug("Using default region: %s", self.default_region)
        return self.default_region

    def _is_valid_region(self, region_id: str) -> bool:
        """Check if a region ID is valid."""
        return region_id in self.KNOWN_REGIONS or region_id in self._regions_config

    def _detect_by_latency(self) -> Optional[str]:
        """Detect region by latency probing."""
        latencies: dict[str, float] = {}

        for region_id, config in self._get_probe_targets().items():
            latency = self._probe_region_latency(region_id, config)
            if latency is not None:
                latencies[region_id] = latency

        if not latencies:
            return None

        best_region = min(latencies.keys(), key=lambda r: latencies[r])
        return best_region

    def _get_probe_targets(self) -> dict[str, dict[str, Any]]:
        """Get endpoints to probe for each region."""
        targets = {}

        for region_id, info in self.KNOWN_REGIONS.items():
            if region_id in self._regions_config:
                config = self._regions_config[region_id]
                targets[region_id] = {
                    "endpoint": config.endpoint,
                    "relay": config.relay,
                }
            else:
                targets[region_id] = {
                    "endpoint": f"https://{region_id}.endpoint.milimo.dev",
                    "relay": "",
                }

        return targets

    def _probe_region_latency(self, region_id: str, config: dict[str, Any]) -> Optional[float]:
        """Probe latency to a specific region."""
        endpoint = config.get("endpoint", "")
        if not endpoint:
            return None

        start_time = time.time()
        try:
            request = urllib.request.Request(endpoint, method="HEAD")
            request.add_header("User-Agent", "MilimoClaw-RegionDetector/1.0")

            response = urllib.request.urlopen(request, timeout=self.probe_timeout_ms / 1000)
            latency_ms = (time.time() - start_time) * 1000

            if response.status < 400:
                logger.debug("Latency to %s: %.2fms", region_id, latency_ms)
                return latency_ms

        except (urllib.error.URLError, socket.timeout, Exception) as e:
            logger.debug("Failed to probe %s: %s", region_id, e)

        return None

    def _detect_by_geolocation(self) -> Optional[str]:
        """Detect region by IP geolocation."""
        for service_url in self.GEOLOCATION_SERVICES:
            try:
                request = urllib.request.Request(service_url)
                request.add_header("User-Agent", "MilimoClaw-RegionDetector/1.0")

                response = urllib.request.urlopen(request, timeout=self.probe_timeout_ms / 1000)
                data = json.loads(response.read().decode())

                return self._map_geolocation_to_region(data)

            except Exception as e:
                logger.debug("Geolocation service failed: %s", e)
                continue

        return None

    def _map_geolocation_to_region(self, geo_data: dict[str, Any]) -> Optional[str]:
        """Map geolocation data to a region."""
        country = geo_data.get("country_code", geo_data.get("countryCode", ""))
        city = geo_data.get("city", "")
        lat = float(geo_data.get("latitude", geo_data.get("lat", 0)))
        lon = float(geo_data.get("longitude", geo_data.get("lon", 0)))

        logger.debug("Geolocation: country=%s, city=%s, lat=%.2f, lon=%.2f", country, city, lat, lon)

        best_region = None
        best_distance = float("inf")

        for region_id, info in self.KNOWN_REGIONS.items():
            if info["country"] == country:
                distance = ((lat - info["lat"]) ** 2 + (lon - info["lon"]) ** 2) ** 0.5
                if distance < best_distance:
                    best_distance = distance
                    best_region = region_id

        return best_region

    def _build_region_info(self, region_id: str) -> RegionInfo:
        """Build full region info from detected region ID."""
        if region_id in self._regions_config:
            config = self._regions_config[region_id]
            info = RegionInfo(
                region_id=region_id,
                region_code=config.code,
                country=config.country,
                city=config.city,
                endpoint=config.endpoint,
                relay=config.relay,
                fallback_region=config.fallback_region,
                confidence=0.9,
            )
        elif region_id in self.KNOWN_REGIONS:
            known = self.KNOWN_REGIONS[region_id]
            info = RegionInfo(
                region_id=region_id,
                region_code=known["code"],
                country=known["country"],
                latitude=known["lat"],
                longitude=known["lon"],
                confidence=0.7,
            )
        else:
            info = RegionInfo(
                region_id=region_id,
                region_code=region_id[:4],
                country="unknown",
                confidence=0.3,
            )

        info.latency_samples = self._sample_latencies(region_id)
        return info

    def _sample_latencies(self, source_region: str) -> dict[str, list[float]]:
        """Sample latencies to other regions."""
        samples: dict[str, list[float]] = {}
        targets = self._get_probe_targets()

        for target_region, config in targets.items():
            if target_region == source_region:
                continue

            latency = self._probe_region_latency(target_region, config)
            if latency is not None:
                samples[target_region] = [latency]

        return samples

    def get_region_config(self, region_id: str) -> Optional[RegionConfig]:
        """Get configuration for a specific region."""
        return self._regions_config.get(region_id)

    def get_all_regions(self) -> list[str]:
        """Get list of all known regions."""
        return list(set(list(self.KNOWN_REGIONS.keys()) + list(self._regions_config.keys())))

    def get_optimal_relay(self, region_id: Optional[str] = None) -> str:
        """Get the optimal relay endpoint for a region."""
        target_region = region_id or self.detect().region_id

        if target_region in self._regions_config:
            relay = self._regions_config[target_region].relay
            if relay:
                return relay

        return f"wss://relay-{target_region}.milimo.dev:443"

    def get_fallback_region(self, region_id: Optional[str] = None) -> str:
        """Get the fallback region for a region."""
        target_region = region_id or self.detect().region_id

        if target_region in self._regions_config:
            fallback = self._regions_config[target_region].fallback_region
            if fallback:
                return fallback

        return self.default_region


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    "RegionInfo",
    "RegionConfig",
    "RegionDetector",
]
