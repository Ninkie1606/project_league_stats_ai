"""Crawl ranked EUW matches into data/league.db.

Examples:
    python collect.py run --tiers GOLD PLATINUM --max-matches 500
    python collect.py run --tiers GOLD PLATINUM EMERALD --forever
    python collect.py run --tiers CHALLENGER --since 2026-01-08
    python collect.py timelines --max 200
    python collect.py stats
    python collect.py build-stats          # tabellen voor het dashboard bijwerken

Stop at any time with Ctrl+C; the next run continues where it left off.
With --forever the crawl keeps going until the API key expires.
"""
import argparse
import logging
import sys
import time
from datetime import datetime, timezone

import requests

from riot import stats
from riot.client import ApiKeyError, RiotClient
from riot.storage import Storage

APEX_TIERS = ("CHALLENGER", "GRANDMASTER", "MASTER")
DIVISIONS = ("I", "II", "III", "IV")
NETWORK_PAUSE = 60  # seconds to wait after a network outage in --forever mode

log = logging.getLogger("collect")


class Progress:
    def __init__(self, client, every=100):
        self.client = client
        self.every = every
        self.started = time.monotonic()
        self.done = 0

    def tick(self, label):
        self.done += 1
        if self.done % self.every == 0:
            hours = (time.monotonic() - self.started) / 3600
            log.info(
                "%d %s opgehaald, %d requests, %.0f %s/uur",
                self.done, label, self.client.request_count, self.done / max(hours, 1e-9), label,
            )


def seed(client, storage, tiers, divisions):
    """Fetch one more league page for every tier/division. Returns the number of players added."""
    added = 0
    for tier in tiers:
        tier_divisions = ["I"] if tier in APEX_TIERS else divisions
        for division in tier_divisions:
            page = storage.next_seed_page(tier, division)
            if page is None:
                continue
            if tier in APEX_TIERS:
                # Apex tiers are a single list; mark page 2 as empty so it isn't fetched again.
                entries = client.apex_league(tier)
                storage.mark_seed_page(tier, division, 2, 0)
            else:
                entries = client.league_entries(tier, division, page)
            storage.add_players(entries, tier, division)
            storage.mark_seed_page(tier, division, page, len(entries))
            added += len(entries)
            log.info("%s %s pagina %d: %d spelers", tier, division, page, len(entries))
    return added


def fetch_one_match(client, storage, match_id):
    try:
        data = client.match(match_id)
    except requests.HTTPError as exc:
        if exc.response is not None and 400 <= exc.response.status_code < 500:
            log.warning("Match %s overgeslagen (HTTP %s)", match_id, exc.response.status_code)
            data = None
        else:
            raise
    storage.save_match(match_id, data)


def crawl_matches(client, storage, tiers, divisions, max_matches, ids_per_player, start_time, forever):
    progress = Progress(client)
    while forever or progress.done < max_matches:
        try:
            match_id = storage.next_pending_match()
            if match_id:
                fetch_one_match(client, storage, match_id)
                progress.tick("matches")
                continue
            puuid = storage.next_player(tiers)
            if puuid is None:
                if seed(client, storage, tiers, divisions) == 0:
                    log.info("Alle league-pagina's van deze tiers zijn op; kies meer tiers.")
                    break
                continue
            ids = client.match_ids(puuid, count=ids_per_player, start_time=start_time)
            new = storage.add_match_ids(ids)
            storage.mark_player_done(puuid)
            log.debug("Speler %s: %d ids, %d nieuw", puuid[:8], len(ids), new)
        except requests.RequestException as exc:
            if not forever:
                raise
            log.warning("Netwerkprobleem (%s); opnieuw over %ds", exc, NETWORK_PAUSE)
            time.sleep(NETWORK_PAUSE)


def crawl_timelines(client, storage, maximum, forever):
    progress = Progress(client)
    while forever or progress.done < maximum:
        try:
            match_id = storage.next_match_without_timeline()
            if match_id is None:
                log.info("Alle opgehaalde matches hebben een timeline.")
                break
            storage.save_timeline(match_id, client.timeline(match_id))
            progress.tick("timelines")
        except requests.RequestException as exc:
            if not forever:
                raise
            log.warning("Netwerkprobleem (%s); opnieuw over %ds", exc, NETWORK_PAUSE)
            time.sleep(NETWORK_PAUSE)


def parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="spelers seeden en matches ophalen")
    run.add_argument("--tiers", nargs="+", default=["GOLD"], type=str.upper,
                     help="bv. IRON BRONZE SILVER GOLD PLATINUM EMERALD DIAMOND MASTER GRANDMASTER CHALLENGER")
    run.add_argument("--divisions", nargs="+", default=list(DIVISIONS), type=str.upper)
    run.add_argument("--max-matches", type=int, default=1000)
    run.add_argument("--forever", action="store_true", help="doorgaan tot de API key verloopt (negeert --max-matches)")
    run.add_argument("--ids-per-player", type=int, default=20)
    run.add_argument("--since", type=parse_date, help="alleen matches vanaf deze datum (YYYY-MM-DD)")

    tl = sub.add_parser("timelines", help="timelines ophalen voor opgehaalde matches")
    tl.add_argument("--max", type=int, default=1000)
    tl.add_argument("--forever", action="store_true", help="doorgaan tot alles binnen is of de key verloopt")

    sub.add_parser("stats", help="toon wat er in de database staat")

    bs = sub.add_parser("build-stats", help="matches omzetten naar tabellen in data/stats.db (voor het dashboard)")
    bs.add_argument("--rebuild", action="store_true", help="stats.db weggooien en helemaal opnieuw opbouwen")

    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    if args.command == "build-stats":
        added = stats.build(rebuild=args.rebuild)
        log.info("%d matches toegevoegd aan %s", added, stats.STATS_DB_PATH)
        return

    storage = Storage()
    if args.command == "stats":
        for key, value in storage.stats().items():
            print(f"{key:16} {value}")
        return

    try:
        client = RiotClient()
        if args.command == "run":
            crawl_matches(client, storage, args.tiers, args.divisions, args.max_matches,
                          args.ids_per_player, args.since, args.forever)
        else:
            crawl_timelines(client, storage, args.max, args.forever)
    except ApiKeyError as exc:
        log.error("%s", exc)
        sys.exit(1)
    except KeyboardInterrupt:
        log.info("Gestopt; de volgende run gaat verder waar deze stopte.")
    finally:
        log.info("Database: %s", storage.stats())


if __name__ == "__main__":
    main()
