"""
YouTube Data API v3 client with a TTL cache and a soft daily quota guard.

The free tier gives 10,000 quota units/day and `search.list` alone costs 100
units - five searches from a careless UI loop can burn 5% of a day's budget.
Caching identical requests and tracking estimated spend keeps this module
usable without silently hitting a 403 quotaExceeded partway through a demo.
"""

import time
from collections import OrderedDict
from datetime import datetime, timezone

import requests

from app.core.config import settings


class YouTubeNotConfiguredError(RuntimeError):
    """Raised when a YouTube endpoint is called without an API key set."""


class YouTubeQuotaGuardError(RuntimeError):
    """Raised when a call would push estimated daily usage past the configured budget."""


# Approximate published unit costs per endpoint. search.list is the outlier -
# almost everything else costs 1 unit per call regardless of part count.
ENDPOINT_UNIT_COST = {
    "search": 100,
    "videos": 1,
    "channels": 1,
    "commentThreads": 1,
    "playlistItems": 1,
    "liveChat/messages": 5,
    "liveBroadcasts": 1,
    "channelSections": 1,
    "i18nRegions": 1,
    "i18nLanguages": 1,
    "videoCategories": 1,
}

# How long a cached response stays valid, per endpoint. Search/trending data
# is slow-moving relative to its cost, so it gets the longest TTL; comments
# and live chat move fast and get short/no caching.
ENDPOINT_CACHE_TTL_SECONDS = {
    "search": 600,
    "videos": 240,
    "channels": 300,
    "playlistItems": 300,
    "commentThreads": 120,
    "liveChat/messages": 0,
    "liveBroadcasts": 0,
    "channelSections": 3600,
    # Region/language/category lists are essentially static reference data.
    "i18nRegions": 86400,
    "i18nLanguages": 86400,
    "videoCategories": 86400,
}

MAX_CACHE_ENTRIES = 500


class _QuotaTracker:
    """In-memory, resets on process restart and at UTC midnight. Good enough
    for a soft guard - the authoritative limit is still enforced by Google."""

    def __init__(self):
        self._day = self._today()
        self._used = 0

    @staticmethod
    def _today():
        return datetime.now(timezone.utc).date()

    def _roll_if_new_day(self):
        today = self._today()
        if today != self._day:
            self._day = today
            self._used = 0

    def used(self) -> int:
        self._roll_if_new_day()
        return self._used

    def add(self, units: int):
        self._roll_if_new_day()
        self._used += units


class YouTubeAPIClient:
    """
    Thin wrapper around the YouTube Data API v3.

    Every call is a single unauthenticated (API-key only) GET request -
    there is no OAuth here, so this can only read public data: videos,
    channels, search results, playlists and public comment threads.
    """

    def __init__(self):
        self.base_url = settings.YOUTUBE_API_BASE_URL
        self.api_key = settings.YOUTUBE_API_KEY
        self.timeout = settings.REQUEST_TIMEOUT
        self.daily_quota_budget = settings.YOUTUBE_DAILY_QUOTA_BUDGET
        self._quota = _QuotaTracker()
        self._cache: "OrderedDict[tuple, tuple[float, dict]]" = OrderedDict()

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def quota_status(self) -> dict:
        used = self._quota.used()
        return {
            "estimated_units_used_today": used,
            "daily_budget": self.daily_quota_budget,
            "remaining": max(self.daily_quota_budget - used, 0),
        }

    def _cache_key(self, endpoint: str, params: dict) -> tuple:
        return (endpoint, tuple(sorted((k, str(v)) for k, v in params.items())))

    def _get_cached(self, key: tuple) -> dict | None:
        entry = self._cache.get(key)
        if not entry:
            return None
        expires_at, payload = entry
        if time.monotonic() >= expires_at:
            del self._cache[key]
            return None
        self._cache.move_to_end(key)
        return payload

    def _store_cache(self, key: tuple, endpoint: str, payload: dict):
        ttl = ENDPOINT_CACHE_TTL_SECONDS.get(endpoint, 180)
        if ttl <= 0:
            return
        self._cache[key] = (time.monotonic() + ttl, payload)
        self._cache.move_to_end(key)
        while len(self._cache) > MAX_CACHE_ENTRIES:
            self._cache.popitem(last=False)

    def get(self, endpoint: str, params: dict, use_cache: bool = True) -> dict:
        if not self.is_configured:
            raise YouTubeNotConfiguredError(
                "YOUTUBE_API_KEY is not set; add it to backend/.env"
            )

        cache_key = self._cache_key(endpoint, params)
        if use_cache:
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached

        cost = ENDPOINT_UNIT_COST.get(endpoint, 1)
        used = self._quota.used()
        if used + cost > self.daily_quota_budget:
            raise YouTubeQuotaGuardError(
                f"Estimated daily YouTube quota budget ({self.daily_quota_budget} units) "
                f"would be exceeded by this call (~{used}/{self.daily_quota_budget} used). "
                "Raise YOUTUBE_DAILY_QUOTA_BUDGET in backend/.env or wait for the daily reset."
            )

        response = requests.get(
            f"{self.base_url}/{endpoint}",
            params={**params, "key": self.api_key},
            timeout=self.timeout,
        )

        # The API returns a JSON error body even on failure, which is more
        # useful than the bare status code (e.g. quota exceeded vs bad param).
        if not response.ok:
            try:
                detail = response.json().get("error", {}).get("message", response.text)
            except ValueError:
                detail = response.text or f"HTTP {response.status_code} with no response body"
            raise requests.HTTPError(
                f"YouTube API {response.status_code} on {endpoint}: {detail}",
                response=response,
            )

        self._quota.add(cost)
        payload = response.json()
        if use_cache:
            self._store_cache(cache_key, endpoint, payload)
        return payload


youtube_client = YouTubeAPIClient()
