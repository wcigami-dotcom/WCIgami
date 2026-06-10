"""
seed.py — loads historical World Cup goal data (1930-2022) into the database.

Usage:
    python seed.py --goals path/to/goals.csv --matches path/to/matches.csv

Download the data from: https://github.com/jfjelstul/worldcup
You need two CSV files from the /data folder:
  - goals.csv
  - matches.csv
"""

import csv
import argparse
from collections import defaultdict
from database import init_db, insert_fingerprint, get_connection
from fingerprint import build_fingerprint


def load_matches(matches_csv):
    """
    Returns a dict keyed by match_id with match metadata.
    """
    matches = {}
    with open(matches_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if "women" in row.get("tournament_name", "").lower():
                continue
            matches[row["match_id"]] = {
                "match_date": row.get("match_date", row.get("date", "")),
                "home_team": row.get("home_team_name", row.get("home_team", "")),
                "away_team": row.get("away_team_name", row.get("away_team", "")),
                "home_score": int(row.get("home_team_score", row.get("home_score", 0)) or 0),
                "away_score": int(row.get("away_team_score", row.get("away_score", 0)) or 0),
                "year": row.get("tournament_id", row.get("year", "0")),
                "stage": row.get("stage_name", row.get("stage", "")),
            }
    return matches


def load_goals(goals_csv):
    """
    Returns a dict keyed by match_id → list of goal minute strings.
    Penalty shootout goals are excluded.
    """
    goals = defaultdict(list)
    with open(goals_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Exclude penalty shootout goals
            penalty_shootout = row.get("penalty_shootout", "0")
            if str(penalty_shootout).strip() in ("1", "True", "true", "yes"):
                continue

            match_id = row["match_id"]
            minute = row.get("minute_label", row.get("minute", row.get("goal_minute", "")))
            if minute:
                goals[match_id].append(str(minute).strip())

    return goals


def seed(goals_csv, matches_csv):
    init_db()

    # Clear existing historical data before re-seeding
    conn = get_connection()
    conn.execute("DELETE FROM fingerprints")
    conn.commit()
    conn.close()
    print("Cleared existing fingerprints.")

    matches = load_matches(matches_csv)
    goals = load_goals(goals_csv)

    count = 0
    skipped = 0

    for match_id, match in matches.items():
        goal_minutes = goals.get(match_id, [])

        # Skip if no goals and score is 0-0 (legitimately goalless)
        # but still fingerprint 0-0 matches
        try:
            fp = build_fingerprint(
                match["home_score"],
                match["away_score"],
                goal_minutes
            )
        except Exception as e:
            print(f"Skipping match {match_id} due to error: {e}")
            skipped += 1
            continue

        # Extract year from tournament_id if it looks like "2022" 
        year = match["year"]
        if isinstance(year, str) and not year.isdigit():
            # tournament_id might be "WC-2022" format
            import re
            m = re.search(r"\d{4}", year)
            year = int(m.group()) if m else 0

        insert_fingerprint(
            fingerprint=fp,
            match_date=match["match_date"],
            home_team=match["home_team"],
            away_team=match["away_team"],
            score=f"{match['home_score']}-{match['away_score']}",
            year=int(year)
        )
        count += 1

    print(f"Seeded {count} historical matches. Skipped {skipped}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed historical WC data")
    parser.add_argument("--goals", required=True, help="Path to goals.csv")
    parser.add_argument("--matches", required=True, help="Path to matches.csv")
    args = parser.parse_args()
    seed(args.goals, args.matches)
