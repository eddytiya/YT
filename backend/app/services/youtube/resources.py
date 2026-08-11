import re

from app.services.youtube.client import youtube_client

# Real channel IDs are always "UC" + 22 URL-safe characters. Anything else
# pasted into a channel field - a full URL, an @handle, a bare handle
# without the @, or a legacy /user/ custom name - needs resolving first.
_CHANNEL_ID_RE = re.compile(r"^UC[\w-]{22}$")


def extract_channel_identifier(raw: str) -> str:
    """Pulls a channel ID, @handle, or legacy username out of whatever a
    user pasted - a full channel URL, a bare @handle, or an ID typed
    directly - so resolve_channel_id() below has a clean input either way."""

    value = (raw or "").strip()

    match = re.search(r"youtube\.com/channel/(UC[\w-]{22})", value)
    if match:
        return match.group(1)

    match = re.search(r"youtube\.com/@([\w.-]+)", value)
    if match:
        return f"@{match.group(1)}"

    match = re.search(r"youtube\.com/(?:c|user)/([\w.-]+)", value)
    if match:
        return match.group(1)

    return value


def resolve_channel_id(raw: str) -> str:
    """Turns a pasted channel URL, @handle, or raw channel ID into a real
    UC... channel ID. Tries the cheap, unambiguous path first (an ID needs
    no lookup at all), then the modern @handle lookup, then falls back to
    the legacy username lookup for old /user/ custom URLs."""

    identifier = extract_channel_identifier(raw)
    if _CHANNEL_ID_RE.match(identifier):
        return identifier

    handle = identifier if identifier.startswith("@") else f"@{identifier}"
    data = youtube_client.get("channels", {"part": "id", "forHandle": handle})
    items = data.get("items", [])
    if items:
        return items[0]["id"]

    data = youtube_client.get("channels", {"part": "id", "forUsername": identifier.lstrip("@")})
    items = data.get("items", [])
    if items:
        return items[0]["id"]

    return identifier  # let the caller's own not-found handling report it


def search_videos(
    query: str,
    max_results: int = 10,
    order: str = "relevance",
    region_code: str | None = None,
    category_id: str | None = None,
    event_type: str | None = None,
    video_duration: str | None = None,
    safe_search: str | None = None,
    video_definition: str | None = None,
    relevance_language: str | None = None,
) -> list[dict]:
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "order": order,
    }
    if region_code:
        params["regionCode"] = region_code
    if category_id:
        params["videoCategoryId"] = category_id
    if event_type:
        # eventType requires type=video, already set above. "live"/"upcoming"/"completed".
        params["eventType"] = event_type
    if video_duration:
        params["videoDuration"] = video_duration
    if safe_search:
        params["safeSearch"] = safe_search
    if video_definition:
        params["videoDefinition"] = video_definition
    if relevance_language:
        params["relevanceLanguage"] = relevance_language

    data = youtube_client.get("search", params)
    return data.get("items", [])


def get_videos(video_ids: list[str]) -> list[dict]:
    data = youtube_client.get(
        "videos",
        {
            "part": "snippet,statistics,contentDetails",
            "id": ",".join(video_ids),
        },
    )
    return data.get("items", [])


def get_channels(channel_ids: list[str]) -> list[dict]:
    data = youtube_client.get(
        "channels",
        {
            "part": "snippet,statistics,contentDetails",
            "id": ",".join(channel_ids),
        },
    )
    return data.get("items", [])


def get_comment_threads(video_id: str, max_results: int = 20) -> list[dict]:
    data = youtube_client.get(
        "commentThreads",
        {
            "part": "snippet,replies",
            "videoId": video_id,
            "maxResults": max_results,
            "order": "relevance",
            "textFormat": "plainText",
        },
    )
    return data.get("items", [])


def get_uploads_playlist_id(channel_id: str) -> str | None:
    channels = get_channels([channel_id])
    if not channels:
        return None
    return channels[0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")


def get_playlist_items(playlist_id: str, max_results: int = 20) -> list[dict]:
    data = youtube_client.get(
        "playlistItems",
        {
            "part": "snippet,contentDetails",
            "playlistId": playlist_id,
            "maxResults": max_results,
        },
    )
    return data.get("items", [])


def get_channel_recent_videos(channel_id: str, max_results: int = 20) -> list[dict]:
    """Recent uploads for a channel, hydrated with full stats (views/likes/comments)."""

    playlist_id = get_uploads_playlist_id(channel_id)
    if not playlist_id:
        return []

    items = get_playlist_items(playlist_id, max_results)
    video_ids = [item["contentDetails"]["videoId"] for item in items if item.get("contentDetails", {}).get("videoId")]
    if not video_ids:
        return []

    # The videos.list endpoint caps at 50 ids per call.
    videos: list[dict] = []
    for i in range(0, len(video_ids), 50):
        videos.extend(get_videos(video_ids[i:i + 50]))
    return videos


def get_video_categories(region_code: str = "US") -> list[dict]:
    data = youtube_client.get(
        "videoCategories",
        {"part": "snippet", "regionCode": region_code},
    )
    return [
        {"id": item["id"], "title": item["snippet"]["title"]}
        for item in data.get("items", [])
        if item.get("snippet", {}).get("assignable")
    ]


def get_channel_sections(channel_id: str) -> list[dict]:
    """A channel's curated homepage sections (featured playlists, multi-video
    shelves, single-playlist shelves) - shows how a creator organizes their
    content, not just what they upload."""

    data = youtube_client.get(
        "channelSections",
        {"part": "snippet,contentDetails", "channelId": channel_id},
    )
    sections = []
    for item in data.get("items", []):
        snippet = item.get("snippet", {})
        sections.append({
            "title": snippet.get("title") or snippet.get("type"),
            "type": snippet.get("type"),
            "style": snippet.get("style"),
            "playlist_count": len(item.get("contentDetails", {}).get("playlists", []) or []),
        })
    return sections


def get_i18n_regions() -> list[dict]:
    data = youtube_client.get("i18nRegions", {"part": "snippet"})
    return [
        {"code": item["id"], "name": item["snippet"]["name"]}
        for item in data.get("items", [])
    ]


def get_i18n_languages() -> list[dict]:
    data = youtube_client.get("i18nLanguages", {"part": "snippet"})
    return [
        {"code": item["id"], "name": item["snippet"]["name"]}
        for item in data.get("items", [])
    ]


def get_playlist_items_full(playlist_id: str, max_results: int = 50) -> list[dict]:
    """Playlist videos hydrated with full stats, for playlist-level analysis."""

    items = get_playlist_items(playlist_id, max_results)
    video_ids = [item["contentDetails"]["videoId"] for item in items if item.get("contentDetails", {}).get("videoId")]
    if not video_ids:
        return []

    videos: list[dict] = []
    for i in range(0, len(video_ids), 50):
        videos.extend(get_videos(video_ids[i:i + 50]))
    return videos


def get_active_live_chat_id(video_id: str) -> str | None:
    """Returns the live chat id for a currently-live broadcast, or None if the
    video isn't a live stream (or the stream has ended)."""

    data = youtube_client.get(
        "videos",
        {"part": "liveStreamingDetails", "id": video_id},
        use_cache=False,
    )
    items = data.get("items", [])
    if not items:
        return None
    return items[0].get("liveStreamingDetails", {}).get("activeLiveChatId")


def get_live_chat_messages(live_chat_id: str, page_token: str | None = None, max_results: int = 200) -> dict:
    """Raw liveChatMessages.list response (items + nextPageToken + pollingIntervalMillis).
    Never cached - by definition this is meant to be read fresh each poll."""

    params = {
        "part": "snippet,authorDetails",
        "liveChatId": live_chat_id,
        "maxResults": max_results,
    }
    if page_token:
        params["pageToken"] = page_token

    return youtube_client.get("liveChat/messages", params, use_cache=False)


def get_trending_videos(region_code: str = "IN", category_id: str | None = None, max_results: int = 20) -> list[dict]:
    params = {
        "part": "snippet,statistics,contentDetails",
        "chart": "mostPopular",
        "regionCode": region_code,
        "maxResults": max_results,
    }
    if category_id:
        params["videoCategoryId"] = category_id

    data = youtube_client.get("videos", params)
    return data.get("items", [])
