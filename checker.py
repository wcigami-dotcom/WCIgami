"""
checker.py — looks up a match fingerprint, determines if it's a WCIgami,
and posts the appropriate tweet.
"""

import logging
from database import lookup_fingerprint, insert_fingerprint, mark_tweeted, get_connection
from twitter import (
    build_igami_tweet,
    build_not_igami_tweet,
    post_tweet,
    format_minutes,
)
from flags import get_flag


def get_igami_count():
    """Returns total WCIgamis found so far (stored in a simple counter table)."""
    conn = get_connection()
    c = conn.cursor()
    # We store igami count as a special row in a meta table
    c.execute("""
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)
    """)
    c.execute("SELECT value FROM meta WHERE key = 'igami_count'")
    row = c.fetchone()
    conn.close()
    return int(row[0]) if row else 0


def increment_igami_count():
    conn = get_connection()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
    c.execute("""
        INSERT INTO meta (key, value) VALUES ('igami_count', '1')
        ON CONFLICT(key) DO UPDATE SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT)
    """)
    conn.commit()
    conn.close()
    return get_igami_count()


def process_match(fixture_id, fingerprint, home_team, away_team,
                  home_score, away_score, goal_minutes, match_date):
    """
    Main entry point. Called by poller.py after a match finishes.
    Looks up the fingerprint, tweets, and records everything.
    """
    score_str = f"{home_score}-{away_score}"
    home_flag = get_flag(home_team)
    away_flag = get_flag(away_team)
    minutes_str = ",".join(goal_minutes)

    result = lookup_fingerprint(fingerprint)
    count = result["count"]
    most_recent = result["most_recent"]

    if count == 0:
        # 🎉 It's a WCIgami!
        igami_number = increment_igami_count()

        tweet = build_igami_tweet(
            home_team=home_team,
            away_team=away_team,
            home_flag=home_flag,
            away_flag=away_flag,
            score=score_str,
            goal_minutes_str=minutes_str,
            igami_number=igami_number,
        )
        logging.info(f"WCIgami #{igami_number}! Tweeting...")

    else:
        # Not an igami — build the "has happened before" tweet
        prev_home = most_recent["home_team"]
        prev_away = most_recent["away_team"]
        prev_date = most_recent["match_date"]

        tweet = build_not_igami_tweet(
            home_team=home_team,
            away_team=away_team,
            home_flag=home_flag,
            away_flag=away_flag,
            score=score_str,
            goal_minutes_str=minutes_str,
            count=count,
            prev_home=prev_home,
            prev_away=prev_away,
            prev_date=prev_date,
        )
        logging.info(f"Not a WCIgami (seen {count}x before). Tweeting...")

    # Post the tweet
    try:
        response = post_tweet(tweet)
        logging.info(f"Tweet posted. ID: {response.data['id']}")
    except Exception as e:
        logging.error(f"Failed to post tweet: {e}")
        logging.error(f"Tweet text was:\n{tweet}")
        return

    # Record this match in the historical fingerprints DB (for future matches)
    insert_fingerprint(
        fingerprint=fingerprint,
        match_date=match_date,
        home_team=home_team,
        away_team=away_team,
        score=score_str,
        year=2026,
    )

    # Mark as tweeted so we don't tweet it again
    mark_tweeted(fixture_id)
    logging.info(f"Match {fixture_id} recorded and marked as tweeted.")
