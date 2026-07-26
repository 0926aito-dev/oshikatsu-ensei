import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from trip_manager import TripManager


def test_add_trip_returns_trip_with_given_fields():
    manager = TripManager()
    trip = manager.add_trip("〇〇ライブ", "2026-08-15", "東京", 25000)

    assert trip.event_name == "〇〇ライブ"
    assert trip.date == "2026-08-15"
    assert trip.place == "東京"
    assert trip.budget == 25000


def test_list_trips_returns_all_added_trips():
    manager = TripManager()
    manager.add_trip("〇〇ライブ", "2026-08-15", "東京", 25000)
    manager.add_trip("△△イベント", "2026-09-01", "大阪", 18000)

    trips = manager.list_trips()

    assert len(trips) == 2
    assert trips[0].event_name == "〇〇ライブ"
    assert trips[1].event_name == "△△イベント"


def test_total_budget_sums_all_trip_budgets():
    manager = TripManager()
    manager.add_trip("〇〇ライブ", "2026-08-15", "東京", 25000)
    manager.add_trip("△△イベント", "2026-09-01", "大阪", 18000)

    assert manager.total_budget() == 43000


def test_total_budget_is_zero_when_no_trips():
    manager = TripManager()

    assert manager.total_budget() == 0
