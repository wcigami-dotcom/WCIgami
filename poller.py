"""
poller.py — polls API-Football every 5 minutes for completed World Cup 2026 matches.
Runs continuously. Designed to be started once and left running.

Usage:
    python poller.py
"""

import os
import time
import requests
import logging
from datetime import datetime, timezone

from database import init_db, already_tweeted, mark_tweeted
from fingerprint import build_fingerprint, parse_minute
from checker import process_match

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("wcigami.log"),
        logging.StreamHandler()
    ]
)

API_KEY = os.environ["API_SPORTS_KEY"]
# World Cup 2026 league ID on API-Football (FIFA World Cup = 1)
WC_LEAGUE_ID = 1
WC_SEASON = 2026
POLL_INTERVAL = 300  # 5 minutes


def get_headers():
    return {
        "x-apisports-key": API_KEY
    }


def fetch_fixtures():
    """Fetch all WC 2026 fixtures from API-Football."""
    url = "https://v3.football.api-sports.io/fixtures"
    params = {
        "league": WC_LEAGUE_ID,
        "season": WC_SEASON,
    }
    resp = requests.get(url, headers=get_headers(), params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data.get("response", [])


def fetch_fixture_events(fixture_id):
    """Fetch goal events for a specific fixture."""
    url = "https://v3.football.api-sports.io/fixtures/events"
    params = {
        "fixture": fixture_id,
        "type": "Goal",
    }
    resp = requests.get(url, headers=get_headers(), params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data.get("response", [])


def parse_events_to_minutes(events):
    """
    Parse API-Football goal events into a list of canonical minute strings.
    Excludes penalty shootout goals.
    """
    minutes = []
    for event in events:
        # Skip penalty shootout goals
        detail = event.get("detail", "")
        if "Penalty" in detail and event.get("time", {}).get("elapsed", 0) > 120:
            continue
        if event.get("type", "").lower() != "goal":
            continue
        # Skip missed penalties / own goals that don't count? No — own goals DO count
        if detail in ("Missed Penalty",):
            continue

        elapsed = event.get("time", {}).get("elapsed")
        extra = event.get("time", {}).get("extra")

        if elapsed is None:
            continue

        if extra:
            raw = f"{elapsed}+{extra}"
        else:
            raw = str(elapsed)

        minutes.append(parse_minute(raw))

    return minutes


def run():
    init_db()
    logging.info("WCIgami poller started.")

    while True:
        try:
            logging.info("Polling for completed fixtures...")
            fixtures = fetch_fixtures()

            for fixture in fixtures:
                status = fixture.get("fixture", {}).get("status", {}).get("short", "")
                fixture_id = fixture.get("fixture", {}).get("id")

                # Only process fully completed matches (FT, AET, PEN)
                if status not in ("FT", "AET", "PEN"):
                    continue

                if already_tweeted(fixture_id):
                    continue

                # Extract match info
                home_team = fixture["teams"]["home"]["name"]
                away_team = fixture["teams"]["away"]["name"]
                home_score = fixture["goals"]["home"] or 0
                away_score = fixture["goals"]["away"] or 0
                match_date = fixture["fixture"]["date"][:10]  # YYYY-MM-DD

                logging.info(f"Processing: {home_team} {home_score}-{away_score} {away_team} (ID: {fixture_id})")

                # Fetch goal events
                events = fetch_fixture_events(fixture_id)
                goal_minutes = parse_events_to_minutes(events)

                # Build fingerprint
                fp = build_fingerprint(home_score, away_score, goal_minutes)
                logging.info(f"Fingerprint: {fp}")

                # Process and tweet
                process_match(
                    fixture_id=fixture_id,
                    fingerprint=fp,
                    home_team=home_team,
                    away_team=away_team,
                    home_score=home_score,
                    away_score=away_score,
                    goal_minutes=goal_minutes,
                    match_date=match_date,
                )

        except requests.exceptions.RequestException as e:
            logging.error(f"API request failed: {e}")
        except Exception as e:
            logging.exception(f"Unexpected error: {e}")

        logging.info(f"Sleeping {POLL_INTERVAL}s until next poll...")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run()
