"""
twitter.py — posts tweets via the Twitter API v2 using Tweepy.
"""

import os
import tweepy


def get_client():
    return tweepy.Client(
        consumer_key=os.environ["TWITTER_API_KEY"],
        consumer_secret=os.environ["TWITTER_API_SECRET"],
        access_token=os.environ["TWITTER_ACCESS_TOKEN"],
        access_token_secret=os.environ["TWITTER_ACCESS_TOKEN_SECRET"],
    )


def get_igami_count():
    """Returns the total number of WCIgamis tweeted so far."""
    from database import get_connection
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM tweeted_matches")
    # We track igamis separately via a flag, so just count tweeted for now
    # This will be refined in checker.py
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0


def format_minutes(goal_minutes_str):
    """Converts stored "23,45+2,67" into "23', 45+2', 67'" """
    if not goal_minutes_str:
        return "No goals"
    minutes = goal_minutes_str.split(",")
    return ", ".join(f"{m}'" for m in minutes)


def build_igami_tweet(home_team, away_team, home_flag, away_flag,
                      score, goal_minutes_str, igami_number):
    minutes_formatted = format_minutes(goal_minutes_str)
    tweet = (
        f"⚽ WCIgami #{igami_number}\n\n"
        f"{home_flag} {home_team} {score} {away_team} {away_flag}\n"
        f"⏱ Goals: {minutes_formatted}\n\n"
        f"This exact scoreline & timing has never happened "
        f"in World Cup history. Ever.\n\n"
        f"#WorldCup2026 #WCIgami"
    )
    return tweet


def build_not_igami_tweet(home_team, away_team, home_flag, away_flag,
                           score, goal_minutes_str, count,
                           prev_home, prev_away, prev_date):
    minutes_formatted = format_minutes(goal_minutes_str)
    times_word = "time" if count == 1 else "times"
    tweet = (
        f"{home_flag} {home_team} {score} {away_team} {away_flag}\n"
        f"⏱ Goals: {minutes_formatted}\n\n"
        f"Not a WCIgami. This exact scoreline & timing has occurred "
        f"{count} {times_word} before in World Cup history.\n\n"
        f"Most recently: {prev_home} {score} {prev_away} — {prev_date}\n\n"
        f"#WorldCup2026 #WCIgami"
    )
    return tweet


def post_tweet(text):
    client = get_client()
    response = client.create_tweet(text=text)
    return response
