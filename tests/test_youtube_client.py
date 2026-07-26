import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import youtube_client


def test_parse_handle_from_full_url():
    assert (
        youtube_client.parse_handle("https://www.youtube.com/@nogizakahaishinchu")
        == "@nogizakahaishinchu"
    )


def test_parse_handle_from_bare_handle():
    assert youtube_client.parse_handle("@sakurazakachannel") == "@sakurazakachannel"


def test_parse_handle_adds_at_prefix():
    assert youtube_client.parse_handle("hinatazakachannel") == "@hinatazakachannel"


def test_parse_handle_keeps_channel_id():
    channel_id = "UC" + "a" * 22
    assert youtube_client.parse_handle(channel_id) == channel_id


def test_resolve_channel_returns_channel_info():
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"items": [{"id": "UCabc123", "snippet": {"title": "乃木坂配信中"}}]}

    def fake_http_get(url, params=None, timeout=None):
        assert params["forHandle"] == "@nogizakahaishinchu"
        return FakeResponse()

    result = youtube_client.resolve_channel(
        "https://www.youtube.com/@nogizakahaishinchu",
        "fake-key",
        http_get=fake_http_get,
    )
    assert result == {"channel_id": "UCabc123", "title": "乃木坂配信中"}


def test_resolve_channel_returns_none_when_not_found():
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"items": []}

    def fake_http_get(url, params=None, timeout=None):
        return FakeResponse()

    assert (
        youtube_client.resolve_channel("@doesnotexist", "fake-key", http_get=fake_http_get)
        is None
    )


def test_fetch_recent_videos_parses_items():
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "items": [
                    {
                        "id": {"videoId": "abc123"},
                        "snippet": {
                            "title": "東京ライブ配信",
                            "description": "会場は東京です",
                            "publishedAt": "2026-07-01T00:00:00Z",
                        },
                    }
                ]
            }

    def fake_http_get(url, params=None, timeout=None):
        assert params["channelId"] == "UCabc123"
        return FakeResponse()

    videos = youtube_client.fetch_recent_videos(
        "UCabc123", "fake-key", http_get=fake_http_get
    )
    assert videos == [
        {
            "video_id": "abc123",
            "title": "東京ライブ配信",
            "description": "会場は東京です",
            "published_at": "2026-07-01T00:00:00Z",
            "url": "https://www.youtube.com/watch?v=abc123",
        }
    ]


def test_fetch_recent_videos_paginates_past_50_per_page():
    def make_item(video_id):
        return {
            "id": {"videoId": video_id},
            "snippet": {
                "title": f"video {video_id}",
                "description": "",
                "publishedAt": "2026-07-01T00:00:00Z",
            },
        }

    calls = []

    class FakeResponse:
        def __init__(self, items, next_page_token=None):
            self._items = items
            self._next_page_token = next_page_token

        def raise_for_status(self):
            pass

        def json(self):
            data = {"items": self._items}
            if self._next_page_token:
                data["nextPageToken"] = self._next_page_token
            return data

    def fake_http_get(url, params=None, timeout=None):
        calls.append(dict(params))
        if params.get("pageToken") is None:
            return FakeResponse(
                [make_item(f"v{i}") for i in range(50)], next_page_token="page2"
            )
        return FakeResponse([make_item(f"v{i}") for i in range(50, 70)])

    videos = youtube_client.fetch_recent_videos(
        "UCabc123", "fake-key", max_results=70, http_get=fake_http_get
    )

    assert len(videos) == 70
    assert len(calls) == 2
    assert calls[0]["maxResults"] == 50
    assert "pageToken" not in calls[0]
    assert calls[1]["pageToken"] == "page2"
