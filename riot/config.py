import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# override=True: a stale RIOT_API_KEY in the shell must not win over .env,
# since dev keys are replaced every 24 h.
load_dotenv(PROJECT_ROOT / ".env", override=True)

RIOT_API_KEY = (os.getenv("RIOT_API_KEY") or "").strip() or None

PLATFORM = "euw1"    # league-v4, summoner-v4
REGION = "europe"    # match-v5, account-v1
QUEUE = 420          # ranked solo/duo
QUEUE_TYPE = "RANKED_SOLO_5x5"

# Development key limits. These are the starting values; the client updates
# them from the X-App-Rate-Limit headers Riot sends back.
DEFAULT_APP_LIMITS = [(20, 1), (100, 120)]

DB_PATH = PROJECT_ROOT / "data" / "league.db"
