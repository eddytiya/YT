"""
OAuth 2.0 flow for the YouTube Analytics API (creator-only private metrics:
impressions, CTR, audience retention, revenue where applicable).

This is a separate credential from YOUTUBE_API_KEY - Google requires a real
user consent flow (an OAuth "Web application" Client ID/Secret from Google
Cloud Console) to access anything beyond public data. Nothing here can be
faked or bypassed; GOOGLE_OAUTH_CLIENT_ID/SECRET must be supplied before any
of this works, and every endpoint reports itself as "not configured" until
then rather than failing with a confusing error.
"""

from datetime import datetime, timedelta

import requests

from app.core.config import settings

AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v2/userinfo"
ANALYTICS_REPORTS_ENDPOINT = "https://youtubeanalytics.googleapis.com/v2/reports"
CHANNELS_ENDPOINT = "https://www.googleapis.com/youtube/v3/channels"

SCOPES = " ".join([
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
])


class OAuthNotConfiguredError(RuntimeError):
    pass


def is_configured() -> bool:
    return bool(settings.GOOGLE_OAUTH_CLIENT_ID and settings.GOOGLE_OAUTH_CLIENT_SECRET)


def _require_configured():
    if not is_configured():
        raise OAuthNotConfiguredError(
            "GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET are not set in backend/.env. "
            "Create an OAuth 2.0 Web application Client ID in Google Cloud Console, add "
            f"{settings.GOOGLE_OAUTH_REDIRECT_URI} as an authorized redirect URI, then set both values."
        )


def build_authorize_url(state: str) -> str:
    _require_configured()
    params = {
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    query = "&".join(f"{k}={requests.utils.quote(v)}" for k, v in params.items())
    return f"{AUTH_ENDPOINT}?{query}"


def exchange_code_for_tokens(code: str) -> dict:
    _require_configured()
    response = requests.post(TOKEN_ENDPOINT, data={
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
    }, timeout=settings.REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def refresh_access_token(refresh_token: str) -> dict:
    _require_configured()
    response = requests.post(TOKEN_ENDPOINT, data={
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }, timeout=settings.REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def get_user_email(access_token: str) -> str | None:
    response = requests.get(USERINFO_ENDPOINT, headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
    if not response.ok:
        return None
    return response.json().get("email")


def get_own_channel_id(access_token: str) -> str | None:
    response = requests.get(CHANNELS_ENDPOINT, params={"part": "id", "mine": "true"},
                             headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
    if not response.ok:
        return None
    items = response.json().get("items", [])
    return items[0]["id"] if items else None


def get_channel_analytics(access_token: str, channel_id: str, days: int = 28) -> dict:
    """Core creator report: views, watch time, subscribers gained/lost,
    likes and comments over the trailing `days`, for the authenticated
    channel only - this is data the public API cannot return."""

    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)

    response = requests.get(ANALYTICS_REPORTS_ENDPOINT, params={
        "ids": f"channel=={channel_id}",
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "metrics": "views,estimatedMinutesWatched,subscribersGained,subscribersLost,likes,comments",
        "dimensions": "day",
    }, headers={"Authorization": f"Bearer {access_token}"}, timeout=settings.REQUEST_TIMEOUT)

    if not response.ok:
        detail = response.json().get("error", {}).get("message", response.text)
        raise requests.HTTPError(f"YouTube Analytics API {response.status_code}: {detail}", response=response)

    return response.json()
