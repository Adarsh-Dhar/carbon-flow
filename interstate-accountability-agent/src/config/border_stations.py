"""
Border station configuration for Delhi NCR.
These stations are located at Delhi's state borders and are critical for monitoring cross-border pollution.
"""

DELHI_BORDER_STATIONS = [
    {
        "name": "Alipur",
        "latitude": 28.8,
        "longitude": 77.1,
        "border": "Haryana",
        "district": "North Delhi"
    },
    {
        "name": "Anand Vihar",
        "latitude": 28.65,
        "longitude": 77.32,
        "border": "Uttar Pradesh",
        "district": "East Delhi"
    },
    {
        "name": "Dwarka",
        "latitude": 28.59,
        "longitude": 77.05,
        "border": "Haryana",
        "district": "South West Delhi"
    },
    {
        "name": "Rohini",
        "latitude": 28.74,
        "longitude": 77.12,
        "border": "Haryana",
        "district": "North West Delhi"
    },
]

# Helper function to get border station by name
def get_border_station(station_name: str) -> dict | None:
    """Get border station configuration by name."""
    for station in DELHI_BORDER_STATIONS:
        if station["name"].lower() == station_name.lower():
            return station
    return None

# Helper function to check if a station is a border station
def is_border_station(station_name: str) -> bool:
    """Check if a station is a Delhi border station."""
    return get_border_station(station_name) is not None
