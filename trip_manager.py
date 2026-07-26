class Trip:
    def __init__(self, event_name, date, place, budget):
        self.event_name = event_name
        self.date = date
        self.place = place
        self.budget = budget

    def __repr__(self):
        return (
            f"Trip(event_name={self.event_name!r}, date={self.date!r}, "
            f"place={self.place!r}, budget={self.budget!r})"
        )


class TripManager:
    def __init__(self):
        self._trips = []

    def add_trip(self, event_name, date, place, budget):
        trip = Trip(event_name, date, place, budget)
        self._trips.append(trip)
        return trip

    def list_trips(self):
        return list(self._trips)

    def total_budget(self):
        return sum(trip.budget for trip in self._trips)
