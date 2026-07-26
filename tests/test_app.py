import io
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app


def make_client(tmp_path):
    app = create_app(db_path=tmp_path / "test.db", upload_folder=tmp_path / "uploads")
    app.testing = True
    return app.test_client()


def test_upcoming_trip_appears_in_kore_kara(tmp_path):
    client = make_client(tmp_path)
    future_date = (date.today() + timedelta(days=10)).isoformat()

    client.post(
        "/trips",
        data={
            "event_name": "未来のライブ",
            "date": future_date,
            "place": "東京",
            "budget": "10000",
        },
    )

    page = client.get("/").get_data(as_text=True)
    assert "未来のライブ" in page
    assert "あと10日" in page


def test_past_trip_with_memo_and_route_appears_in_kore_made(tmp_path):
    client = make_client(tmp_path)
    past_date = (date.today() - timedelta(days=5)).isoformat()

    client.post(
        "/trips",
        data={
            "event_name": "過去のライブ",
            "date": past_date,
            "place": "大阪",
            "budget": "8000",
            "route": "会場入り→物販→本編",
            "memo": "最高でした",
        },
    )

    page = client.get("/").get_data(as_text=True)
    assert "過去のライブ" in page
    assert "最高でした" in page
    assert "会場入り" in page


def test_photo_upload_is_saved_and_displayed(tmp_path):
    client = make_client(tmp_path)
    past_date = (date.today() - timedelta(days=2)).isoformat()

    client.post(
        "/trips",
        data={
            "event_name": "写真付きライブ",
            "date": past_date,
            "place": "札幌",
            "budget": "5000",
            "photo": (io.BytesIO(b"fake-image-data"), "photo.png"),
        },
        content_type="multipart/form-data",
    )

    page = client.get("/").get_data(as_text=True)
    assert "写真付きライブ" in page
    assert "/static/uploads/" in page
    assert len(list((tmp_path / "uploads").iterdir())) == 1


def test_edit_updates_memo_and_route(tmp_path):
    client = make_client(tmp_path)
    past_date = (date.today() - timedelta(days=1)).isoformat()

    client.post(
        "/trips",
        data={
            "event_name": "編集対象",
            "date": past_date,
            "place": "名古屋",
            "budget": "3000",
        },
    )

    page = client.get("/").get_data(as_text=True)
    trip_id = page.split("/trips/")[1].split("/")[0]

    client.post(
        f"/trips/{trip_id}/edit",
        data={
            "event_name": "編集対象",
            "date": past_date,
            "place": "名古屋",
            "budget": "3000",
            "route": "更新後ルート",
            "memo": "更新後メモ",
        },
    )

    page = client.get("/").get_data(as_text=True)
    assert "更新後ルート" in page
    assert "更新後メモ" in page


def test_delete_removes_trip(tmp_path):
    client = make_client(tmp_path)
    future_date = (date.today() + timedelta(days=1)).isoformat()

    client.post(
        "/trips",
        data={
            "event_name": "削除対象",
            "date": future_date,
            "place": "福岡",
            "budget": "1000",
        },
    )

    page = client.get("/").get_data(as_text=True)
    trip_id = page.split("/trips/")[1].split("/")[0]

    client.post(f"/trips/{trip_id}/delete")

    page = client.get("/").get_data(as_text=True)
    assert "削除対象" not in page


def test_share_link_enable_view_and_disable(tmp_path):
    client = make_client(tmp_path)

    client.post(
        "/trips",
        data={
            "event_name": "共有確認用",
            "date": date.today().isoformat(),
            "place": "東京",
            "budget": "1000",
        },
    )

    client.post("/share/enable")
    page = client.get("/").get_data(as_text=True)
    assert "共有リンクが有効です" in page

    share_url = page.split('<div class="share-url">')[1].split("</div>")[0].strip()
    token = share_url.rstrip("/").split("/")[-1]

    share_page = client.get(f"/share/{token}")
    assert share_page.status_code == 200
    assert "共有確認用" in share_page.get_data(as_text=True)

    client.post("/share/disable")
    assert client.get(f"/share/{token}").status_code == 404
