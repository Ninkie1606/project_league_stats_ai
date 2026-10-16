"""Crawl ranked EUW matches into data/league.db.

Examples:
    python collect.py run --tiers GOLD PLATINUM --max-matches 500
    python collect.py run --tiers CHALLENGER --since 2026-01-08
    python collect.py timelines --max 200
    python collect.py stats

Stop at any time with Ctrl+C; the next run continues where it left off.
"""
import argparse
import logging
import sys
import time
from datetime import datetime, timezone

from riot.client import ApiKeyError, RiotClient
from riot.storage import Storage

APEX_TIERS = ("CHALLENGER", "GRANDMASTER", "MASTER")
DIVISIONS = ("I", "II", "III", "IV")

log = logging.getLogger("collect")


class Progress:
    def __init__(self, client, every=25):
        self.client = client
        self.every = every
        self.started = time.monotonic()
        self.done = 0

    def tick(self, label):
        self.done += 1
        if self.done % self.every == 0:
            minutes = (time.monotonic() - self.started) / 60
            log.info(
                "%d %s opgehaald, %d requests (%.0f req/min)",
                self.done, label, self.client.request_count, self.client.request_count / max(minutes, 1e-9),
            )


def seed(client, storage, tiers, divisions, pages):
    for tier in tiers:
        if tier in APEX_TIERS:
            if storage.has_players(tier, "I"):
                continue
            entries = client.apex_league(tier)
            storage.add_players(entries, tier, "I")
            log.info("%s: %d spelers toegevoegd", tier, len(entries))
            continue
        for division in divisions:
            if storage.has_players(tier, division):
                continue
            total = 0
            for page in range(1, pages + 1):
                entries = client.league_entries(tier, division, page)
                if not entries:
                    break
                storage.add_players(entries, tier, division)
                total += len(entries)
            log.info("%s %s: %d spelers toegevoegd", tier, division, total)


def crawl_matches(client, storage, max_matches, ids_per_player, start_time):
    progress = Progress(client)
    while progress.done < max_matches:
        match_id = storage.next_pending_match()
        if match_id:
            storage.save_match(match_id, client.match(match_id))
            progress.tick("matches")
            continue
        puuid = storage.next_player()
        if puuid is None:
            log.info("Geen spelers meer over; seed meer tiers/pagina's.")
            break
        ids = client.match_ids(puuid, count=ids_per_player, start_time=start_time)
        new = storage.add_match_ids(ids)
        storage.mark_player_done(puuid)
        log.debug("Speler %s: %d ids, %d nieuw", puuid[:8], len(ids), new)


def crawl_timelines(client, storage, maximum):
    progress = Progress(client)
    while progress.done < maximum:
        match_id = storage.next_match_without_timeline()
        if match_id is None:
            log.info("Alle opgehaalde matches hebben een timeline.")
            break
        storage.save_timeline(match_id, client.timeline(match_id))
        progress.tick("timelines")


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
    run.add_argument("--pages", type=int, default=1, help="league-v4 pagina's per tier/divisie (~205 spelers per pagina)")
    run.add_argument("--max-matches", type=int, default=1000)
    run.add_argument("--ids-per-player", type=int, default=20)
    run.add_argument("--since", type=parse_date, help="alleen matches vanaf deze datum (YYYY-MM-DD)")

    tl = sub.add_parser("timelines", help="timelines ophalen voor opgehaalde matches")
    tl.add_argument("--max", type=int, default=1000)

    sub.add_parser("stats", help="toon wat er in de database staat")

    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    storage = Storage()
    if args.command == "stats":
        for key, value in storage.stats().items():
            print(f"{key:16} {value}")
        return

    try:
        client = RiotClient()
        if args.command == "run":
            seed(client, storage, args.tiers, args.divisions, args.pages)
            crawl_matches(client, storage, args.max_matches, args.ids_per_player, args.since)
        else:
            crawl_timelines(client, storage, args.max)
    except ApiKeyError as exc:
        log.error("%s", exc)
        sys.exit(1)
    except KeyboardInterrupt:
        log.info("Gestopt; de volgende run gaat verder waar deze stopte.")
    finally:
        log.info("Database: %s", storage.stats())


if __name__ == "__main__":
    main()
