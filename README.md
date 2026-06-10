# ⚽ WCIgami Bot

A Twitter/X bot that tweets after every FIFA World Cup 2026 match, checking whether the exact combination of scoreline + goal minutes has ever occurred in World Cup history.

- **WCIgami**: The scoreline and goal timing has NEVER happened before in World Cup history
- **Not a WCIgami**: It has happened before — the tweet says how many times and the most recent occurrence

---

## How It Works

Every match gets a **fingerprint** — a string combining:
- The final score (e.g. `2-1`)
- A sorted list of goal minutes, with stoppage time preserved (e.g. `23,45+2,67`)

Example fingerprint: `2-1|23,45+2,67`

Penalty shootout goals are excluded. Own goals count. Goal order doesn't matter (it's sorted).

---

## Setup

### 1. Clone / download this project

```bash
git clone <your-repo-url>
cd wcigami
```

### 2. Install Python dependencies

Requires Python 3.9+.

```bash
pip install -r requirements.txt
```

### 3. Set up environment variables

Copy the example file and fill in your keys:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```
TWITTER_API_KEY=...         # Consumer Key from X Developer Portal
TWITTER_API_SECRET=...      # Secret Key from X Developer Portal
TWITTER_ACCESS_TOKEN=...    # Access Token (Read & Write)
TWITTER_ACCESS_TOKEN_SECRET=...
API_SPORTS_KEY=...          # From dashboard.api-sports.io
```

### 4. Download historical World Cup data

1. Go to https://github.com/jfjelstul/worldcup
2. Click the green **Code** button → **Download ZIP**
3. Unzip it — you need two files from the `/data` folder:
   - `goals.csv`
   - `matches.csv`

### 5. Seed the historical database

```bash
python seed.py --goals path/to/goals.csv --matches path/to/matches.csv
```

You should see output like:
```
Database initialised.
Cleared existing fingerprints.
Seeded 853 historical matches. Skipped 0.
```

### 6. Run the bot

```bash
python poller.py
```

The bot will poll every 5 minutes. During a live match it checks for completion. When a match finishes it tweets immediately.

---

## Deploying to Railway (free hosting)

Railway runs your bot 24/7 for free.

1. Go to [railway.app](https://railway.app) and sign up with GitHub
2. Create a **New Project** → **Deploy from GitHub repo**
3. Push this project to a GitHub repo and connect it
4. In Railway, go to your project → **Variables** and add all 5 environment variables from your `.env` file
5. Railway will detect the `Procfile` and run `python poller.py` automatically
6. To add the database file, use Railway's **Volume** feature (under your service settings) so the SQLite DB persists between restarts

> **Important**: Before deploying, run `seed.py` locally first to generate `wcigami.db`, then upload it to Railway via their CLI:
> ```bash
> npm install -g @railway/cli
> railway login
> railway up
> ```

---

## Project Structure

```
wcigami/
├── poller.py        # Main loop — polls API-Football every 5 mins
├── checker.py       # Fingerprint lookup + tweet decision logic
├── fingerprint.py   # Builds canonical match fingerprints
├── database.py      # SQLite helpers
├── twitter.py       # Tweet formatting and posting
├── flags.py         # Country name → flag emoji
├── seed.py          # One-time historical data loader
├── requirements.txt
├── Procfile         # For Railway deployment
├── .env.example     # Template for your credentials
└── wcigami.db       # Generated after running seed.py (not in git)
```

---

## Tweet Formats

**WCIgami:**
```
⚽ WCIgami #47

🇦🇷 Argentina 2-1 France 🇫🇷
⏱ Goals: 23', 45+2', 67'

This exact scoreline & timing has never happened in World Cup history. Ever.

#WorldCup2026 #WCIgami
```

**Not a WCIgami:**
```
🇦🇷 Argentina 2-1 France 🇫🇷
⏱ Goals: 23', 45+2', 67'

Not a WCIgami. This exact scoreline & timing has occurred 3 times before in World Cup history.

Most recently: Italy 2-1 Brazil — 2006-06-14

#WorldCup2026 #WCIgami
```

---

## Notes

- The bot tweets **once per match**, after the final whistle (status: FT, AET, or PEN)
- After each 2026 match, the result is added to the database so future matches are compared against it too
- The free API-Football tier gives 100 requests/day — more than enough for 64 matches across ~30 match days
- Logs are written to `wcigami.log`
