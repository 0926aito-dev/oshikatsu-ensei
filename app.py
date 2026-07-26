import os
import sqlite3
from pathlib import Path

from flask import Flask, redirect, render_template, request, url_for

DB_PATH = Path(os.environ.get("DATABASE_PATH", "trips.db"))

app = Flask(__name__)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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


@app.route("/")
def index():
    with get_db() as conn:
        trips = conn.execute("SELECT * FROM trips ORDER BY date").fetchall()
        total = conn.execute(
            "SELECT COALESCE(SUM(budget), 0) AS total FROM trips"
        ).fetchone()["total"]
    return render_template("index.html", trips=trips, total=total)


@app.route("/trips", methods=["POST"])
def add_trip():
    event_name = request.form.get("event_name", "").strip()
    date = request.form.get("date", "").strip()
    place = request.form.get("place", "").strip()
    budget_raw = request.form.get("budget", "").strip()
    budget = int(budget_raw) if budget_raw.isdigit() else 0

    if event_name and date and place:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO trips (event_name, date, place, budget) VALUES (?, ?, ?, ?)",
                (event_name, date, place, budget),
            )
    return redirect(url_for("index"))


@app.route("/trips/<int:trip_id>/delete", methods=["POST"])
def delete_trip(trip_id):
    with get_db() as conn:
        conn.execute("DELETE FROM trips WHERE id = ?", (trip_id,))
    return redirect(url_for("index"))


init_db()

if __name__ == "__main__":
    app.run(debug=True)
