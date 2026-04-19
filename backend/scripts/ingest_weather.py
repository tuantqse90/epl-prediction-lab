"""Kickoff-time weather forecast via open-meteo (no API key).

For each upcoming match in the next 48h with a known home-stadium coord,
fetches the forecast hour matching kickoff time and writes a row. Free tier
caps at 10,000 calls/day — we run maybe 15-30 calls/day even on busy weeks.

Usage:
    python scripts/ingest_weather.py [--window-minutes 2880]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings
from app.weather.stadiums import STADIUMS


WEATHER_CODE_MAP = {
    0: "clear", 1: "clear", 2: "partly-cloudy", 3: "cloudy",
    45: "fog", 48: "fog",
    51: "drizzle", 53: "drizzle", 55: "drizzle",
    61: "rain", 63: "rain", 65: "rain-heavy",
    71: "snow", 73: "snow", 75: "snow-heavy",
    80: "rain", 81: "rain", 82: "rain-heavy",
    95: "thunderstorm", 96: "thunderstorm", 99: "thunderstorm",
}


def _fetch_forecast(lat: float, lon: float, iso_hour: str) -> dict | None:
    # iso_hour like "2025-04-19T16:00"
    params = {
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "hourly": "temperature_2m,wind_speed_10m,precipitation,weather_code",
        "start_hour": iso_hour,
        "end_hour": iso_hour,
        "timezone": "UTC",
        "wind_speed_unit": "kmh",
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"[weather] fetch failed ({lat},{lon}): {type(e).__name__}: {e}")
        return None


async def run(window_minutes: int) -> None:
    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        rows = await pool.fetch(
            """
            SELECT m.id, m.kickoff_time, ht.slug AS home_slug
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            WHERE m.status = 'scheduled'
              AND m.kickoff_time BETWEEN NOW() AND NOW() + ($1 || ' minutes')::INTERVAL
            ORDER BY m.kickoff_time ASC
            """,
            str(window_minutes),
        )
        fetched = 0
        for r in rows:
            coord = STADIUMS.get(r["home_slug"])
            if coord is None:
                continue
            lat, lon = coord
            # Round kickoff to its hour in UTC for open-meteo's start_hour param.
            ko = r["kickoff_time"].replace(minute=0, second=0, microsecond=0)
            iso_hour = ko.strftime("%Y-%m-%dT%H:00")
            body = _fetch_forecast(lat, lon, iso_hour)
            if not body:
                continue
            hourly = body.get("hourly") or {}
            temps = hourly.get("temperature_2m") or []
            winds = hourly.get("wind_speed_10m") or []
            precips = hourly.get("precipitation") or []
            codes = hourly.get("weather_code") or []
            if not temps:
                continue
            temp = float(temps[0])
            wind = float(winds[0]) if winds else None
            precip = float(precips[0]) if precips else None
            code = WEATHER_CODE_MAP.get(int(codes[0])) if codes else None
            await pool.execute(
                """
                INSERT INTO match_weather (match_id, temp_c, wind_kmh, precip_mm, condition, fetched_at)
                VALUES ($1, $2, $3, $4, $5, NOW())
                ON CONFLICT (match_id) DO UPDATE SET
                    temp_c = EXCLUDED.temp_c,
                    wind_kmh = EXCLUDED.wind_kmh,
                    precip_mm = EXCLUDED.precip_mm,
                    condition = EXCLUDED.condition,
                    fetched_at = NOW()
                """,
                r["id"], temp, wind, precip, code,
            )
            fetched += 1
        print(f"[weather] updated {fetched}/{len(rows)} matches")
    finally:
        await pool.close()


def main() -> None:
    logging.disable(logging.CRITICAL)
    p = argparse.ArgumentParser()
    p.add_argument("--window-minutes", type=int, default=2880)
    args = p.parse_args()
    asyncio.run(run(args.window_minutes))


if __name__ == "__main__":
    main()
