import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import places


def test_extract_place_candidates_finds_known_prefecture():
    candidates = places.extract_place_candidates("来週は東京でライブです")
    texts = [c["place_text"] for c in candidates]
    assert "東京" in texts


def test_extract_place_candidates_finds_venue_suffix():
    candidates = places.extract_place_candidates("さいたまスーパーアリーナで会いましょう")
    texts = [c["place_text"] for c in candidates]
    assert any(text.endswith("アリーナ") for text in texts)


def test_extract_place_candidates_ignores_unrelated_text():
    candidates = places.extract_place_candidates("今日は自宅でまったりしています")
    assert candidates == []


def test_geocode_returns_coordinates_on_hit():
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return [{"lat": "35.681236", "lon": "139.767125", "display_name": "Tokyo"}]

    def fake_http_get(url, params=None, headers=None, timeout=None):
        return FakeResponse()

    result = places.geocode("東京", http_get=fake_http_get)
    assert result == (35.681236, 139.767125, "Tokyo")


def test_geocode_returns_none_on_no_results():
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return []

    def fake_http_get(url, params=None, headers=None, timeout=None):
        return FakeResponse()

    assert places.geocode("存在しない場所です", http_get=fake_http_get) is None
