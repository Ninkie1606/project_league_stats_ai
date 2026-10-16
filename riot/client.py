import logging
import time

import requests

from riot import config
from riot.rate_limiter import RateLimiter, parse_limit_header

log = logging.getLogger(__name__)

RETRY_STATUSES = {500, 502, 503, 504}
MAX_RETRIES = 5


class ApiKeyError(RuntimeError):
    """The key is missing, expired (dev keys last 24 h) or invalid."""


class RiotClient:
    def __init__(self, api_key=None, limiter=None, session=None):
        self.api_key = api_key or config.RIOT_API_KEY
        if not self.api_key:
            raise ApiKeyError("RIOT_API_KEY ontbreekt in .env")
        self.limiter = limiter or RateLimiter()
        self.session = session or requests.Session()
        self.session.headers["X-Riot-Token"] = self.api_key
        self.request_count = 0

    def get(self, routing, path, params=None, method=None):
        """GET https://{routing}.api.riotgames.com{path}.

        `method` names the endpoint for its own method rate limit bucket.
        Returns the parsed JSON, or None on 404.
        """
        app_key = routing
        method_key = f"{routing}:{method or path}"
        if not self.limiter.has_limits(app_key):
            self.limiter.set_limits(app_key, config.DEFAULT_APP_LIMITS)

        url = f"https://{routing}.api.riotgames.com{path}"
        attempt = 0
        while True:
            self.limiter.acquire(app_key, method_key)
            self.request_count += 1
            try:
                response = self.session.get(url, params=params, timeout=15)
            except requests.RequestException as exc:
                attempt += 1
                if attempt > MAX_RETRIES:
                    raise
                delay = 2 ** attempt
                log.warning("Netwerkfout (%s), opnieuw over %ss", exc, delay)
                time.sleep(delay)
                continue

            self._sync_limits(response.headers, app_key, method_key)

            status = response.status_code
            if status == 200:
                return response.json()
            if status == 404:
                return None
            if status in (401, 403):
                raise ApiKeyError(
                    f"HTTP {status}: API key verlopen of ongeldig. Haal een nieuwe "
                    "key op developer.riotgames.com en zet die in .env."
                )
            if status == 429:
                retry_after = float(response.headers.get("Retry-After", 10))
                limit_type = response.headers.get("X-Rate-Limit-Type", "onbekend")
                log.warning("429 (%s limit) op %s, wacht %.0fs", limit_type, path, retry_after)
                time.sleep(retry_after)
                continue
            if status in RETRY_STATUSES:
                attempt += 1
                if attempt > MAX_RETRIES:
                    response.raise_for_status()
                delay = 2 ** attempt
                log.warning("HTTP %s op %s, opnieuw over %ss", status, path, delay)
                time.sleep(delay)
                continue
            response.raise_for_status()

    def _sync_limits(self, headers, app_key, method_key):
        for key, limit_header, count_header in (
            (app_key, "X-App-Rate-Limit", "X-App-Rate-Limit-Count"),
            (method_key, "X-Method-Rate-Limit", "X-Method-Rate-Limit-Count"),
        ):
            if limit_header in headers:
                self.limiter.set_limits(key, parse_limit_header(headers[limit_header]))
            if count_header in headers:
                self.limiter.sync_counts(key, parse_limit_header(headers[count_header]))

    # --- league-v4 (platform routing) ---

    def league_entries(self, tier, division, page=1):
        path = f"/lol/league/v4/entries/{config.QUEUE_TYPE}/{tier}/{division}"
        return self.get(config.PLATFORM, path, {"page": page}, method="league-entries") or []

    def apex_league(self, tier):
        """tier: CHALLENGER, GRANDMASTER or MASTER. Returns the entries list."""
        path = f"/lol/league/v4/{tier.lower()}leagues/by-queue/{config.QUEUE_TYPE}"
        league = self.get(config.PLATFORM, path, method=f"{tier.lower()}-league")
        return league["entries"] if league else []

    # --- match-v5 (regional routing) ---

    def match_ids(self, puuid, count=20, start=0, start_time=None, queue=config.QUEUE):
        params = {"queue": queue, "type": "ranked", "start": start, "count": count}
        if start_time is not None:
            params["startTime"] = int(start_time)
        path = f"/lol/match/v5/matches/by-puuid/{puuid}/ids"
        return self.get(config.REGION, path, params, method="match-ids") or []

    def match(self, match_id):
        return self.get(config.REGION, f"/lol/match/v5/matches/{match_id}", method="match")

    def timeline(self, match_id):
        path = f"/lol/match/v5/matches/{match_id}/timeline"
        return self.get(config.REGION, path, method="timeline")
