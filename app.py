import os
import secrets
import sqlite3
from datetime import date
from pathlib import Path
from uuid import uuid4

from flask import Flask, abort, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

ALLOWED_PHOTO_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def create_app(db_path=None, upload_folder=None):
    app = Flask(__name__)

    db_path = Path(db_path or os.environ.get("DATABASE_PATH", "trips.db"))
    upload_folder = Path(
        upload_folder or os.environ.get("UPLOAD_FOLDER", "static/uploads")
    )
    upload_folder.mkdir(parents=True, exist_ok=True)

    app.config["DB_PATH"] = db_path
    app.config["UPLOAD_FOLDER"] = upload_folder

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

    init_db()
    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
