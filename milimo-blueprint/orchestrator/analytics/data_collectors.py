# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Analytics Data Collectors

Real API connectors for external data sources.
Replaces fabricated/mock data with actual platform metrics.

Supported sources:
- YouTube Data API v3
- Google Analytics 4
- Generic REST endpoints (configurable)
"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..milimo_paths import analytics_dir

logger = logging.getLogger("milimo.analytics.collectors")


@dataclass
class CollectorResult:
    """Result from a data collection run."""

    source: str
    success: bool
    records_collected: int
    data: list[dict[str, Any]]
    error: str | None = None
    collected_at: str = ""

    def __post_init__(self) -> None:
        if not self.collected_at:
            self.collected_at = datetime.now(timezone.utc).isoformat()


class YouTubeDataCollector:
    """
    Collects analytics from YouTube Data API v3.

    Requires YOUTUBE_API_KEY environment variable.
    Fetches video performance metrics, audience retention, and engagement data.
    """

    API_BASE = "https://www.googleapis.com/youtube/v3"

    def __init__(
        self,
        channel_id: str | None = None,
        api_key: str | None = None,
        data_dir: Path | None = None,
    ) -> None:
        self.channel_id = channel_id or os.environ.get("YOUTUBE_CHANNEL_ID", "")
        self.api_key = api_key or os.environ.get("YOUTUBE_API_KEY", "")
        self.data_dir = data_dir or analytics_dir("youtube")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._last_collection: datetime | None = None

    def is_configured(self) -> bool:
        return bool(self.api_key and self.channel_id)

    def collect_video_stats(self, max_results: int = 50) -> CollectorResult:
        """Collect performance stats for channel videos."""
        if not self.is_configured():
            return CollectorResult(
                source="youtube",
                success=False,
                records_collected=0,
                data=[],
                error="YouTube API key or channel ID not configured",
            )

        try:
            # Step 1: Get channel's recent videos
            videos = self._get_channel_videos(max_results)
            if not videos:
                return CollectorResult(
                    source="youtube", success=True, records_collected=0, data=[]
                )

            # Step 2: Collect stats for each video
            all_records = []
            for video in videos:
                video_id = (
                    video["id"]["videoId"]
                    if "videoId" in video.get("id", {})
                    else video.get("id", "")
                )
                stats = self._get_video_stats(video_id)
                if stats:
                    record = {
                        "video_id": video_id,
                        "title": video.get("snippet", {}).get("title", ""),
                        "published_at": video.get("snippet", {}).get("publishedAt", ""),
                        "views": stats.get("viewCount", 0),
                        "likes": stats.get("likeCount", 0),
                        "comments": stats.get("commentCount", 0),
                        "favorites": stats.get("favoriteCount", 0),
                        "engagement_rate": self._calc_engagement_rate(stats),
                        "collected_at": datetime.now(timezone.utc).isoformat(),
                    }
                    all_records.append(record)

            self._persist_records(all_records)
            self._last_collection = datetime.now(timezone.utc)

            return CollectorResult(
                source="youtube",
                success=True,
                records_collected=len(all_records),
                data=all_records,
            )

        except Exception as e:
            logger.error("YouTube collection failed: %s", e)
            return CollectorResult(
                source="youtube",
                success=False,
                records_collected=0,
                data=[],
                error=str(e),
            )

    def collect_channel_analytics(self) -> CollectorResult:
        """Collect aggregate channel-level analytics."""
        if not self.is_configured():
            return CollectorResult(
                source="youtube",
                success=False,
                records_collected=0,
                data=[],
                error="YouTube API key or channel ID not configured",
            )

        try:
            url = f"{self.API_BASE}/channels"
            params = {
                "part": "statistics,snippet,contentDetails",
                "id": self.channel_id,
                "key": self.api_key,
            }
            query_string = "&".join(f"{k}={v}" for k, v in params.items())
            full_url = f"{url}?{query_string}"

            response = self._api_request(full_url)
            if not response or "items" not in response or not response["items"]:
                return CollectorResult(
                    source="youtube",
                    success=False,
                    records_collected=0,
                    data=[],
                    error="Channel not found",
                )

            channel_data = response["items"][0]
            stats = channel_data.get("statistics", {})
            snippet = channel_data.get("snippet", {})

            record = {
                "channel_id": self.channel_id,
                "channel_name": snippet.get("title", ""),
                "subscriber_count": int(stats.get("subscriberCount", 0)),
                "video_count": int(stats.get("videoCount", 0)),
                "view_count": int(stats.get("viewCount", 0)),
                "hidden_subscriber_count": stats.get("hiddenSubscriberCount", False),
                "collected_at": datetime.now(timezone.utc).isoformat(),
            }

            self._persist_records([record], filename="channel_stats.jsonl")
            self._last_collection = datetime.now(timezone.utc)

            return CollectorResult(
                source="youtube",
                success=True,
                records_collected=1,
                data=[record],
            )

        except Exception as e:
            logger.error("YouTube channel analytics failed: %s", e)
            return CollectorResult(
                source="youtube",
                success=False,
                records_collected=0,
                data=[],
                error=str(e),
            )

    def _get_channel_videos(self, max_results: int) -> list[dict[str, Any]]:
        """Get recent videos from the channel."""
        url = f"{self.API_BASE}/search"
        params = {
            "part": "snippet",
            "channelId": self.channel_id,
            "type": "video",
            "order": "date",
            "maxResults": min(max_results, 50),
            "key": self.api_key,
        }
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        full_url = f"{url}?{query_string}"

        response = self._api_request(full_url)
        return response.get("items", []) if response else []

    def _get_video_stats(self, video_id: str) -> dict[str, Any] | None:
        """Get statistics for a single video."""
        url = f"{self.API_BASE}/videos"
        params = {
            "part": "statistics",
            "id": video_id,
            "key": self.api_key,
        }
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        full_url = f"{url}?{query_string}"

        response = self._api_request(full_url)
        if response and response.get("items"):
            return response["items"][0].get("statistics", {})
        return None

    def _calc_engagement_rate(self, stats: dict[str, Any]) -> float:
        """Calculate engagement rate from video stats."""
        views = int(stats.get("viewCount", 0))
        if views == 0:
            return 0.0
        likes = int(stats.get("likeCount", 0))
        comments = int(stats.get("commentCount", 0))
        return round((likes + comments) / views * 100, 4)

    def _api_request(self, url: str) -> dict[str, Any] | None:
        """Make a YouTube API request with retry logic."""
        for attempt in range(3):
            try:
                req = Request(url)
                with urlopen(req, timeout=30) as response:
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as e:
                if e.code == 429 and attempt < 2:
                    # Rate limited — wait and retry
                    time.sleep(2**attempt)
                    continue
                logger.error("YouTube API HTTP error %d: %s", e.code, e.reason)
                return None
            except URLError as e:
                logger.error("YouTube API URL error: %s", e.reason)
                if attempt < 2:
                    time.sleep(2**attempt)
                    continue
                return None
            except Exception as e:
                logger.error("YouTube API request failed: %s", e)
                return None
        return None

    def _persist_records(
        self, records: list[dict], filename: str = "video_stats.jsonl"
    ) -> None:
        """Persist collected records to disk."""
        filepath = self.data_dir / filename
        with open(filepath, "a") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")

    def get_collected_data(self, lookback_days: int = 30) -> list[dict[str, Any]]:
        """Read collected data from disk within lookback window."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        records = []

        for jsonl_file in self.data_dir.glob("*.jsonl"):
            try:
                with open(jsonl_file) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                            collected_at = record.get("collected_at", "")
                            if collected_at:
                                record_time = datetime.fromisoformat(collected_at)
                                if record_time >= cutoff:
                                    records.append(record)
                        except (json.JSONDecodeError, ValueError):
                            continue
            except Exception as e:
                logger.warning("Failed to read %s: %s", jsonl_file, e)

        return records


class GoogleAnalyticsCollector:
    """
    Collects analytics from Google Analytics 4 via the GA4 Reporting API.

    Requires GOOGLE_APPLICATION_CREDENTIALS environment variable pointing to
    a service account JSON key file.
    """

    API_BASE = "https://analyticsdata.googleapis.com/v1beta"

    def __init__(
        self,
        property_id: str | None = None,
        credentials_path: str | None = None,
        data_dir: Path | None = None,
    ) -> None:
        self.property_id = property_id or os.environ.get("GA4_PROPERTY_ID", "")
        self.credentials_path = credentials_path or os.environ.get(
            "GOOGLE_APPLICATION_CREDENTIALS", ""
        )
        self.data_dir = data_dir or analytics_dir("google_analytics")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._access_token: str | None = None
        self._token_expiry: datetime | None = None
        self._last_collection: datetime | None = None

    def is_configured(self) -> bool:
        return bool(self.property_id and self.credentials_path)

    def collect_page_views(self, days: int = 7) -> CollectorResult:
        """Collect page view metrics from GA4."""
        if not self.is_configured():
            return CollectorResult(
                source="google_analytics",
                success=False,
                records_collected=0,
                data=[],
                error="GA4 property ID or credentials not configured",
            )

        try:
            token = self._get_access_token()
            if not token:
                return CollectorResult(
                    source="google_analytics",
                    success=False,
                    records_collected=0,
                    data=[],
                    error="Failed to obtain access token",
                )

            payload = {
                "dateRanges": [{"startDate": f"{days}daysAgo", "endDate": "today"}],
                "dimensions": [{"name": "pagePath"}, {"name": "date"}],
                "metrics": [
                    {"name": "screenPageViews"},
                    {"name": "activeUsers"},
                    {"name": "averageSessionDuration"},
                ],
                "orderBys": [
                    {"metric": {"metricName": "screenPageViews"}, "desc": True}
                ],
                "limit": 1000,
            }

            url = f"{self.API_BASE}/properties/{self.property_id}:runReport"
            response = self._api_request(url, payload, token)
            if not response or "rows" not in response:
                return CollectorResult(
                    source="google_analytics",
                    success=True,
                    records_collected=0,
                    data=[],
                )

            records = []
            for row in response["rows"]:
                dims = row.get("dimensionValues", [])
                metrics = row.get("metricValues", [])
                record = {
                    "page_path": dims[0].get("value", "") if len(dims) > 0 else "",
                    "date": dims[1].get("value", "") if len(dims) > 1 else "",
                    "page_views": int(metrics[0].get("value", 0))
                    if len(metrics) > 0
                    else 0,
                    "active_users": int(metrics[1].get("value", 0))
                    if len(metrics) > 1
                    else 0,
                    "avg_session_duration": float(metrics[2].get("value", 0))
                    if len(metrics) > 2
                    else 0,
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                }
                records.append(record)

            self._persist_records(records, filename="page_views.jsonl")
            self._last_collection = datetime.now(timezone.utc)

            return CollectorResult(
                source="google_analytics",
                success=True,
                records_collected=len(records),
                data=records,
            )

        except Exception as e:
            logger.error("GA4 collection failed: %s", e)
            return CollectorResult(
                source="google_analytics",
                success=False,
                records_collected=0,
                data=[],
                error=str(e),
            )

    def collect_events(self, days: int = 7) -> CollectorResult:
        """Collect event metrics from GA4."""
        if not self.is_configured():
            return CollectorResult(
                source="google_analytics",
                success=False,
                records_collected=0,
                data=[],
                error="GA4 property ID or credentials not configured",
            )

        try:
            token = self._get_access_token()
            if not token:
                return CollectorResult(
                    source="google_analytics",
                    success=False,
                    records_collected=0,
                    data=[],
                    error="Failed to obtain access token",
                )

            payload = {
                "dateRanges": [{"startDate": f"{days}daysAgo", "endDate": "today"}],
                "dimensions": [{"name": "eventName"}, {"name": "date"}],
                "metrics": [{"name": "eventCount"}, {"name": "activeUsers"}],
                "orderBys": [{"metric": {"metricName": "eventCount"}, "desc": True}],
                "limit": 500,
            }

            url = f"{self.API_BASE}/properties/{self.property_id}:runReport"
            response = self._api_request(url, payload, token)
            if not response or "rows" not in response:
                return CollectorResult(
                    source="google_analytics",
                    success=True,
                    records_collected=0,
                    data=[],
                )

            records = []
            for row in response["rows"]:
                dims = row.get("dimensionValues", [])
                metrics = row.get("metricValues", [])
                record = {
                    "event_name": dims[0].get("value", "") if len(dims) > 0 else "",
                    "date": dims[1].get("value", "") if len(dims) > 1 else "",
                    "event_count": int(metrics[0].get("value", 0))
                    if len(metrics) > 0
                    else 0,
                    "active_users": int(metrics[1].get("value", 0))
                    if len(metrics) > 1
                    else 0,
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                }
                records.append(record)

            self._persist_records(records, filename="events.jsonl")
            self._last_collection = datetime.now(timezone.utc)

            return CollectorResult(
                source="google_analytics",
                success=True,
                records_collected=len(records),
                data=records,
            )

        except Exception as e:
            logger.error("GA4 events collection failed: %s", e)
            return CollectorResult(
                source="google_analytics",
                success=False,
                records_collected=0,
                data=[],
                error=str(e),
            )

    def _get_access_token(self) -> str | None:
        """Get OAuth2 access token from service account credentials."""
        if (
            self._access_token
            and self._token_expiry
            and datetime.now(timezone.utc) < self._token_expiry
        ):
            return self._access_token

        try:
            with open(self.credentials_path) as f:
                credentials = json.load(f)

            client_email = credentials.get("client_email", "")
            private_key = credentials.get("private_key", "")
            token_uri = credentials.get(
                "token_uri", "https://oauth2.googleapis.com/token"
            )

            if not client_email or not private_key:
                logger.error("Invalid service account credentials")
                return None

            # Build JWT assertion for service account auth
            import base64

            # Header
            header = {"alg": "RS256", "typ": "JWT"}
            header_b64 = (
                base64.urlsafe_b64encode(json.dumps(header).encode())
                .rstrip(b"=")
                .decode()
            )

            # Payload (JWT claim set)
            now = int(time.time())
            payload_data = {
                "iss": client_email,
                "scope": "https://www.googleapis.com/auth/analytics.readonly",
                "aud": token_uri,
                "exp": now + 3600,
                "iat": now,
            }
            payload_b64 = (
                base64.urlsafe_b64encode(json.dumps(payload_data).encode())
                .rstrip(b"=")
                .decode()
            )

            # Sign (simplified — in production use cryptography library)
            signing_input = f"{header_b64}.{payload_b64}".encode()
            signature = self._sign_rsa(private_key, signing_input)
            if not signature:
                return None

            assertion = f"{header_b64}.{payload_b64}.{signature}"

            # Exchange assertion for access token
            body = f"grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer&assertion={assertion}"
            req = Request(
                token_uri,
                data=body.encode(),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            with urlopen(req, timeout=30) as response:
                token_data = json.loads(response.read().decode("utf-8"))
                self._access_token = token_data.get("access_token")
                self._token_expiry = datetime.now(timezone.utc) + timedelta(
                    seconds=token_data.get("expires_in", 3600) - 300
                )
                return self._access_token

        except Exception as e:
            logger.error("Failed to get access token: %s", e)
            return None

    def _sign_rsa(self, private_key_pem: str, data: bytes) -> str | None:
        """Sign data with RSA-SHA256. Requires cryptography library."""
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding
            from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

            key = serialization.load_pem_private_key(
                private_key_pem.encode(), password=None
            )
            if not isinstance(key, RSAPrivateKey):
                raise TypeError("Expected RSA private key")
            signature = key.sign(data, padding.PKCS1v15(), hashes.SHA256())
            return base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
        except ImportError:
            logger.error("cryptography library required for JWT signing")
            return None
        except Exception as e:
            logger.error("RSA signing failed: %s", e)
            return None

    def _api_request(
        self, url: str, payload: dict, token: str
    ) -> dict[str, Any] | None:
        """Make GA4 API request."""
        try:
            body = json.dumps(payload).encode("utf-8")
            req = Request(
                url,
                data=body,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urlopen(req, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as e:
            logger.error(
                "GA4 API HTTP error %d: %s",
                e.code,
                e.read().decode("utf-8", errors="replace"),
            )
            return None
        except Exception as e:
            logger.error("GA4 API request failed: %s", e)
            return None

    def _persist_records(
        self, records: list[dict], filename: str = "data.jsonl"
    ) -> None:
        """Persist collected records to disk."""
        filepath = self.data_dir / filename
        with open(filepath, "a") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")

    def get_collected_data(
        self, lookback_days: int = 30, metric: str = "page_views"
    ) -> list[dict[str, Any]]:
        """Read collected data from disk within lookback window."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        records = []

        for jsonl_file in self.data_dir.glob("*.jsonl"):
            try:
                with open(jsonl_file) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                            collected_at = record.get("collected_at", "")
                            if collected_at:
                                record_time = datetime.fromisoformat(collected_at)
                                if record_time >= cutoff:
                                    records.append(record)
                        except (json.JSONDecodeError, ValueError):
                            continue
            except Exception as e:
                logger.warning("Failed to read %s: %s", jsonl_file, e)

        return records


class GenericAPICollector:
    """
    Generic REST API collector for any platform with a JSON API.

    Configurable endpoint, headers, and data extraction path.
    """

    def __init__(
        self,
        name: str,
        base_url: str,
        api_key: str | None = None,
        headers: dict[str, str] | None = None,
        data_dir: Path | None = None,
    ) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = headers or {}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
        self.data_dir = data_dir or analytics_dir(name)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._last_collection: datetime | None = None

    def collect(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> CollectorResult:
        """Collect data from a REST endpoint."""
        try:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            if params:
                query_string = "&".join(f"{k}={v}" for k, v in params.items())
                url = f"{url}?{query_string}"

            req = Request(url, headers=self.headers)
            with urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))

            records = data if isinstance(data, list) else [data]
            self._persist_records(records)
            self._last_collection = datetime.now(timezone.utc)

            return CollectorResult(
                source=self.name,
                success=True,
                records_collected=len(records),
                data=records,
            )

        except Exception as e:
            logger.error("Generic API collection (%s) failed: %s", self.name, e)
            return CollectorResult(
                source=self.name,
                success=False,
                records_collected=0,
                data=[],
                error=str(e),
            )

    def _persist_records(self, records: list[dict]) -> None:
        """Persist collected records to disk."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filepath = self.data_dir / f"collected_{timestamp}.json"
        with open(filepath, "w") as f:
            json.dump(records, f, indent=2)

    def get_collected_data(self, lookback_days: int = 30) -> list[dict[str, Any]]:
        """Read collected data from disk within lookback window."""
        datetime.now(timezone.utc) - timedelta(days=lookback_days)
        records = []

        for json_file in self.data_dir.glob("*.json"):
            try:
                with open(json_file) as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        records.extend(data)
                    else:
                        records.append(data)
            except Exception as e:
                logger.warning("Failed to read %s: %s", json_file, e)

        return records
