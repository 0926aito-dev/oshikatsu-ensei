import re

import requests

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"

_CHANNEL_ID_PATTERN = re.compile(r"^UC[\w-]{22}$")


def parse_handle(identifier):
    identifier = identifier.strip()
    match = re.search(r"youtube\.com/(@[\w.-]+)", identifier)
    if match:
        return match.group(1)
    if identifier.startswith("@"):
        return identifier
    if _CHANNEL_ID_PATTERN.match(identifier):
        return identifier
    return f"@{identifier}"


def resolve_channel(identifier, api_key, http_get=requests.get):
    handle = parse_handle(identifier)
    params = {"part": "snippet", "key": api_key}
    if _CHANNEL_ID_PATTERN.match(handle):
        params["id"] = handle
    else:
        params["forHandle"] = handle

    response = http_get(f"{YOUTUBE_API_BASE}/channels", params=params, timeout=10)
    response.raise_for_status()
    items = response.json().get("items", [])
    if not items:
        return None

    item = items[0]
    return {"channel_id": item["id"], "title": item["snippet"]["title"]}


def fetch_recent_videos(channel_id, api_key, max_results=10, http_get=requests.get):
    """Fetch up to max_results most recent videos, newest first.

    YouTube caps each search.list page at 50 results, so this pages through
    search.list with pageToken until either max_results is reached or the
    channel runs out of videos.
    """
    videos = []
    page_token = None

    while len(videos) < max_results:
        params = {
            "part": "snippet",
            "channelId": channel_id,
            "order": "date",
            "type": "video",
            "maxResults": min(50, max_results - len(videos)),
            "key": api_key,
        }
        if page_token:
            params["pageToken"] = page_token

        response = http_get(f"{YOUTUBE_API_BASE}/search", params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        for item in data.get("items", []):
            video_id = item["id"]["videoId"]
            snippet = item["snippet"]
            videos.append(
                {
                    "video_id": video_id,
                    "title": snippet.get("title", ""),
                    "description": snippet.get("description", ""),
                    "published_at": snippet.get("publishedAt", ""),
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                }
            )

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return videos
