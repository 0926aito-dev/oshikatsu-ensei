import os
import secrets
import sqlite3
import time
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

from flask import Flask, abort, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

import places
import youtube_client

ALLOWED_PHOTO_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

QUICK_ADD_CHANNELS = [
    ("@nogizakahaishinchu", "乃木坂配信中"),
    ("@sakurazakachannel", "櫻坂チャンネル"),
    ("@sakurazaka46SMEJ", "SME公式(櫻坂46)"),
    ("@46officialyoutubechannel99", "乃木坂46公式"),
    ("@hinatazakachannel", "日向坂チャンネル"),
]

# Regular (e.g. monthly, scheduled) checks only look at the most recent
# videos. A "full" check (typically run once, right after adding a channel)
# looks back further. This is capped rather than truly unlimited: scanning
# a channel's entire history could burn through the YouTube API's daily
# quota and take long enough to hit Render's request timeout.
DEFAULT_CHECK_VIDEO_LIMIT = 10
FULL_CHECK_VIDEO_LIMIT = 200


def create_app(db_path=None, upload_folder=None):
    app = Flask(__name__)

    db_path = Path(db_path or os.environ.get("DATABASE_PATH", "trips.db"))
    upload_folder = Path(
        upload_folder or os.environ.get("UPLOAD_FOLDER", "static/uploads")
    )
    upload_folder.mkdir(parents=True, exist_ok=True)

    app.config["DB_PATH"] = db_path
    app.config["UPLOAD_FOLDER"] = upload_folder
    app.config["YOUTUBE_API_KEY"] = os.environ.get("YOUTUBE_API_KEY")
    app.config["CHECK_TOKEN"] = os.environ.get("CHECK_TOKEN")

    def get_db():
        conn = sqlite3.connect(app.config["DB_PATH"])
        conn.row_factory = sqlite3.Row
        return conn

    def ensure_column(conn, table, column, coltype):
        existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")

    def init_db():
        with get_db() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS trips (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_name TEXT NOT NULL,
                    date TEXT NOT NULL,
                    place TEXT NOT NULL,
                    budget INTEGER NOT NULL
                )
                """
            )
            ensure_column(conn, "trips", "route", "TEXT")
            ensure_column(conn, "trips", "memo", "TEXT")
            ensure_column(conn, "trips", "photo_filename", "TEXT")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS share_settings (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    enabled INTEGER NOT NULL DEFAULT 0,
                    token TEXT
                )
                """
            )
            conn.execute(
                "INSERT OR IGNORE INTO share_settings (id, enabled, token) VALUES (1, 0, NULL)"
            )

            ensure_column(conn, "trips", "lat", "REAL")
            ensure_column(conn, "trips", "lng", "REAL")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS watched_channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scanned_videos (
                    video_id TEXT PRIMARY KEY
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mentioned_places (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT,
                    video_id TEXT NOT NULL,
                    video_title TEXT NOT NULL,
                    video_url TEXT NOT NULL,
                    published_at TEXT,
                    place_text TEXT NOT NULL,
                    context TEXT,
                    lat REAL NOT NULL,
                    lng REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(video_id, place_text)
                )
                """
            )

    def allowed_photo(filename):
        return (
            "." in filename
            and filename.rsplit(".", 1)[1].lower() in ALLOWED_PHOTO_EXTENSIONS
        )

    def save_photo(file_storage):
        if not file_storage or not file_storage.filename:
            return None
        if not allowed_photo(file_storage.filename):
            return None
        ext = secure_filename(file_storage.filename).rsplit(".", 1)[1].lower()
        filename = f"{uuid4().hex}.{ext}"
        file_storage.save(app.config["UPLOAD_FOLDER"] / filename)
        return filename

    def delete_photo(filename):
        if not filename:
            return
        path = app.config["UPLOAD_FOLDER"] / filename
        if path.exists():
            path.unlink()

    def split_trips(trips):
        today = date.today().isoformat()
        upcoming = sorted(
            (dict(t) for t in trips if t["date"] >= today), key=lambda t: t["date"]
        )
        past = sorted(
            (dict(t) for t in trips if t["date"] < today),
            key=lambda t: t["date"],
            reverse=True,
        )
        for trip in upcoming:
            trip["days_left"] = (date.fromisoformat(trip["date"]) - date.today()).days
        return upcoming, past

    def get_share_settings(conn):
        return conn.execute("SELECT * FROM share_settings WHERE id = 1").fetchone()

    @app.route("/")
    def index():
        with get_db() as conn:
            trips = conn.execute("SELECT * FROM trips").fetchall()
            share = get_share_settings(conn)

        upcoming, past = split_trips(trips)
        share_url = None
        if share["enabled"] and share["token"]:
            share_url = url_for("share_view", token=share["token"], _external=True)

        return render_template(
            "index.html",
            upcoming=upcoming,
            past=past,
            upcoming_total=sum(t["budget"] for t in upcoming),
            past_total=sum(t["budget"] for t in past),
            share_enabled=bool(share["enabled"]),
            share_url=share_url,
        )

    @app.route("/trips", methods=["POST"])
    def add_trip():
        event_name = request.form.get("event_name", "").strip()
        trip_date = request.form.get("date", "").strip()
        place = request.form.get("place", "").strip()
        budget_raw = request.form.get("budget", "").strip()
        budget = int(budget_raw) if budget_raw.isdigit() else 0
        route = request.form.get("route", "").strip() or None
        memo = request.form.get("memo", "").strip() or None
        photo_filename = save_photo(request.files.get("photo"))

        if event_name and trip_date and place:
            with get_db() as conn:
                conn.execute(
                    """
                    INSERT INTO trips
                        (event_name, date, place, budget, route, memo, photo_filename)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (event_name, trip_date, place, budget, route, memo, photo_filename),
                )
        return redirect(url_for("index"))

    @app.route("/trips/<int:trip_id>/edit", methods=["GET"])
    def edit_trip_form(trip_id):
        with get_db() as conn:
            trip = conn.execute(
                "SELECT * FROM trips WHERE id = ?", (trip_id,)
            ).fetchone()
        if trip is None:
            abort(404)
        return render_template("edit_trip.html", trip=trip)

    @app.route("/trips/<int:trip_id>/edit", methods=["POST"])
    def edit_trip(trip_id):
        with get_db() as conn:
            trip = conn.execute(
                "SELECT * FROM trips WHERE id = ?", (trip_id,)
            ).fetchone()
            if trip is None:
                abort(404)

            event_name = request.form.get("event_name", "").strip()
            trip_date = request.form.get("date", "").strip()
            place = request.form.get("place", "").strip()
            budget_raw = request.form.get("budget", "").strip()
            budget = int(budget_raw) if budget_raw.isdigit() else 0
            route = request.form.get("route", "").strip() or None
            memo = request.form.get("memo", "").strip() or None

            photo_filename = trip["photo_filename"]
            if request.form.get("remove_photo"):
                delete_photo(photo_filename)
                photo_filename = None

            new_photo = save_photo(request.files.get("photo"))
            if new_photo:
                delete_photo(photo_filename)
                photo_filename = new_photo

            if event_name and trip_date and place:
                conn.execute(
                    """
                    UPDATE trips
                    SET event_name = ?, date = ?, place = ?, budget = ?,
                        route = ?, memo = ?, photo_filename = ?
                    WHERE id = ?
                    """,
                    (
                        event_name,
                        trip_date,
                        place,
                        budget,
                        route,
                        memo,
                        photo_filename,
                        trip_id,
                    ),
                )
        return redirect(url_for("index"))

    @app.route("/trips/<int:trip_id>/delete", methods=["POST"])
    def delete_trip(trip_id):
        with get_db() as conn:
            trip = conn.execute(
                "SELECT * FROM trips WHERE id = ?", (trip_id,)
            ).fetchone()
            if trip is not None:
                delete_photo(trip["photo_filename"])
            conn.execute("DELETE FROM trips WHERE id = ?", (trip_id,))
        return redirect(url_for("index"))

    @app.route("/share/enable", methods=["POST"])
    def share_enable():
        with get_db() as conn:
            share = get_share_settings(conn)
            token = share["token"] or secrets.token_urlsafe(16)
            conn.execute(
                "UPDATE share_settings SET enabled = 1, token = ? WHERE id = 1",
                (token,),
            )
        return redirect(url_for("index"))

    @app.route("/share/disable", methods=["POST"])
    def share_disable():
        with get_db() as conn:
            conn.execute("UPDATE share_settings SET enabled = 0 WHERE id = 1")
        return redirect(url_for("index"))

    @app.route("/share/regenerate", methods=["POST"])
    def share_regenerate():
        with get_db() as conn:
            token = secrets.token_urlsafe(16)
            conn.execute(
                "UPDATE share_settings SET enabled = 1, token = ? WHERE id = 1",
                (token,),
            )
        return redirect(url_for("index"))

    @app.route("/share/<token>")
    def share_view(token):
        with get_db() as conn:
            share = get_share_settings(conn)
            if not share["enabled"] or not share["token"] or share["token"] != token:
                abort(404)
            trips = conn.execute("SELECT * FROM trips").fetchall()

        upcoming, past = split_trips(trips)
        return render_template(
            "share.html",
            upcoming=upcoming,
            past=past,
            upcoming_total=sum(t["budget"] for t in upcoming),
            past_total=sum(t["budget"] for t in past),
        )

    @app.route("/map")
    def map_view():
        with get_db() as conn:
            trips = conn.execute("SELECT * FROM trips").fetchall()
            _, past = split_trips(trips)

            for trip in past:
                if trip["lat"] is None or trip["lng"] is None:
                    result = places.geocode(trip["place"])
                    if result:
                        lat, lng, _ = result
                        conn.execute(
                            "UPDATE trips SET lat = ?, lng = ? WHERE id = ?",
                            (lat, lng, trip["id"]),
                        )
                        trip["lat"], trip["lng"] = lat, lng

            mentioned = [
                dict(row)
                for row in conn.execute(
                    "SELECT * FROM mentioned_places ORDER BY created_at DESC"
                ).fetchall()
            ]

        visited_pins = [
            {
                "lat": trip["lat"],
                "lng": trip["lng"],
                "label": f"{trip['event_name']}({trip['date']} / {trip['place']})",
                "url": url_for("edit_trip_form", trip_id=trip["id"]),
            }
            for trip in past
            if trip["lat"] is not None and trip["lng"] is not None
        ]

        mentioned_pins = [
            {
                "lat": mention["lat"],
                "lng": mention["lng"],
                "label": f"{mention['place_text']}({mention['video_title']})",
                "url": mention["video_url"],
            }
            for mention in mentioned
        ]

        return render_template(
            "map.html", visited_pins=visited_pins, mentioned_pins=mentioned_pins
        )

    @app.route("/channels", methods=["GET"])
    def channels_view():
        with get_db() as conn:
            channels = conn.execute(
                "SELECT * FROM watched_channels ORDER BY title"
            ).fetchall()
        return render_template(
            "channels.html",
            channels=channels,
            quick_add_channels=QUICK_ADD_CHANNELS,
            youtube_api_key_configured=bool(app.config["YOUTUBE_API_KEY"]),
            check_token=app.config["CHECK_TOKEN"],
            error=request.args.get("error"),
        )

    @app.route("/channels", methods=["POST"])
    def add_channel():
        api_key = app.config["YOUTUBE_API_KEY"]
        if not api_key:
            return redirect(url_for("channels_view", error="missing_api_key"))

        identifier = request.form.get("identifier", "").strip()
        if identifier:
            resolved = youtube_client.resolve_channel(identifier, api_key)
            if resolved:
                with get_db() as conn:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO watched_channels (channel_id, title)
                        VALUES (?, ?)
                        """,
                        (resolved["channel_id"], resolved["title"]),
                    )
        return redirect(url_for("channels_view"))

    @app.route("/channels/<int:channel_row_id>/delete", methods=["POST"])
    def delete_channel(channel_row_id):
        with get_db() as conn:
            conn.execute(
                "DELETE FROM watched_channels WHERE id = ?", (channel_row_id,)
            )
        return redirect(url_for("channels_view"))

    @app.route("/channels/check", methods=["POST"])
    def check_channels():
        expected_token = app.config["CHECK_TOKEN"]
        if expected_token:
            provided_token = request.headers.get(
                "X-Check-Token"
            ) or request.values.get("token")
            if provided_token != expected_token:
                abort(403)

        api_key = app.config["YOUTUBE_API_KEY"]
        if not api_key:
            return redirect(url_for("channels_view", error="missing_api_key"))

        full = request.values.get("full") == "1"
        max_results = FULL_CHECK_VIDEO_LIMIT if full else DEFAULT_CHECK_VIDEO_LIMIT

        added = 0
        with get_db() as conn:
            # Reuse coordinates already found for a place_text (this run or a
            # past one) instead of asking Nominatim again for the same string.
            geocode_cache = {
                row["place_text"]: (row["lat"], row["lng"])
                for row in conn.execute(
                    "SELECT DISTINCT place_text, lat, lng FROM mentioned_places"
                )
            }

            channels = conn.execute("SELECT * FROM watched_channels").fetchall()

            for channel in channels:
                videos = youtube_client.fetch_recent_videos(
                    channel["channel_id"], api_key, max_results=max_results
                )
                for video in videos:
                    already_scanned = conn.execute(
                        "SELECT 1 FROM scanned_videos WHERE video_id = ?",
                        (video["video_id"],),
                    ).fetchone()
                    if already_scanned:
                        continue

                    text = f"{video['title']}\n{video['description']}"
                    for candidate in places.extract_place_candidates(text):
                        place_text = candidate["place_text"]
                        if place_text in geocode_cache:
                            cached = geocode_cache[place_text]
                            lat, lng = cached if cached else (None, None)
                        else:
                            result = places.geocode(place_text)
                            # Respect Nominatim's fair-use rate limit
                            # (roughly one request per second).
                            time.sleep(1)
                            if result:
                                lat, lng, _ = result
                                geocode_cache[place_text] = (lat, lng)
                            else:
                                lat = lng = None
                                geocode_cache[place_text] = None

                        if lat is None or lng is None:
                            continue

                        cursor = conn.execute(
                            """
                            INSERT OR IGNORE INTO mentioned_places
                                (channel_id, video_id, video_title, video_url,
                                 published_at, place_text, context, lat, lng,
                                 created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                channel["channel_id"],
                                video["video_id"],
                                video["title"],
                                video["url"],
                                video["published_at"],
                                place_text,
                                candidate["context"],
                                lat,
                                lng,
                                datetime.now(timezone.utc).isoformat(),
                            ),
                        )
                        if cursor.rowcount:
                            added += 1

                    conn.execute(
                        "INSERT OR IGNORE INTO scanned_videos (video_id) VALUES (?)",
                        (video["video_id"],),
                    )

        return redirect(url_for("mentions_view", added=added))

    @app.route("/mentions")
    def mentions_view():
        with get_db() as conn:
            mentioned = conn.execute(
                "SELECT * FROM mentioned_places ORDER BY created_at DESC"
            ).fetchall()
        return render_template(
            "mentions.html", mentioned=mentioned, added=request.args.get("added")
        )

    @app.route("/mentions/<int:mention_id>/edit", methods=["POST"])
    def edit_mention(mention_id):
        place_text = request.form.get("place_text", "").strip()
        if place_text:
            result = places.geocode(place_text)
            if result:
                lat, lng, _ = result
                with get_db() as conn:
                    conn.execute(
                        """
                        UPDATE mentioned_places
                        SET place_text = ?, lat = ?, lng = ?
                        WHERE id = ?
                        """,
                        (place_text, lat, lng, mention_id),
                    )
        return redirect(url_for("mentions_view"))

    @app.route("/mentions/<int:mention_id>/delete", methods=["POST"])
    def delete_mention(mention_id):
        with get_db() as conn:
            conn.execute("DELETE FROM mentioned_places WHERE id = ?", (mention_id,))
        return redirect(url_for("mentions_view"))

    init_db()
    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
