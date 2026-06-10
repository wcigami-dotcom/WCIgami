"""
fingerprint.py — builds the canonical match fingerprint.

A fingerprint is the combination of:
  - The final scoreline (e.g. "2-1")
  - A sorted tuple of goal minutes, order-independent, with stoppage time preserved
    e.g. ("23", "45+2", "67")

Penalty shootout goals are EXCLUDED.
Own goals count toward the score and minutes.

Minute encoding:
  - Normal time:    "23"
  - Stoppage time:  "45+2" or "90+3"
  - Extra time:     "ET:95" or "ET:105+1"
"""


import re


def parse_minute(minute_str):
    if minute_str is None:
        return None
    s = str(minute_str).strip()
    match = re.match(r'(\d+)(?:\+(\d+))?', s)
    if not match:
        return None
    base = int(match.group(1))
    extra = int(match.group(2)) if match.group(2) else 0
    if base > 90:
        return f"ET:{base}+{extra}" if extra > 0 else f"ET:{base}"
    return f"{base}+{extra}" if extra > 0 else str(base)


def build_fingerprint(score_home, score_away, goal_minutes):
    score = f"{score_home}-{score_away}"
    parsed = [parse_minute(m) for m in goal_minutes if m is not None]
    parsed = sorted([m for m in parsed if m is not None], key=_sort_key)
    return f"{score}|{','.join(parsed)}"


def _sort_key(minute_str):
    s = minute_str
    et = s.startswith("ET:")
    if et:
        s = s[3:]
    if "+" in s:
        base, extra = s.split("+")
        return (1 if et else 0, int(base), int(extra))
    return (1 if et else 0, int(s), 0)