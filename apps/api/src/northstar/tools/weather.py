from typing import Any

def get_weather(city: str, date: str | None = None) -> dict[str, Any]:
  stubbed_weather = {
    "kyoto": {"forecast": "Light rain", "high_c": 22, "low_c": 16},
    "tokyo": {"forecast": "Sunny", "high_c": 24, "low_c": 18},
    "london": {"forecast": "Cloudy", "high_c": 17, "low_c": 11},
  }

  weather = stubbed_weather.get(
    city.strip().lower(),
    {"forecast": "Unknown", "high_c": 20, "low_c": 12},
  )

  return {
    "city": city,
    "date": date,
    "forecast": weather["forecast"],
    "high_c": weather["high_c"],
    "low_c": weather["low_c"],
    "source": "stub",
  }

