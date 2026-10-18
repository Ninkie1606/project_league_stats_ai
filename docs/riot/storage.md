# `riot/storage.py`

Leest en schrijft de SQLite-database `data/league.db`. Elke match wordt meteen opgeslagen, zodat stoppen nooit data kost.

## Gebruik in Python: data inladen

```python
from riot.storage import load_matches, load_timelines

matches = load_matches()           # lijst van dicts, één per match
print(len(matches))

m = matches[0]
print(m["metadata"]["matchId"])
for p in m["info"]["participants"]:
    print(p["championName"], p["teamPosition"], p["kills"], p["deaths"], p["assists"], p["win"])

timelines = load_timelines()       # {match_id: timeline}, alleen als je timelines hebt opgehaald
```

Een match heeft de structuur van Riots [match-v5](https://developer.riotgames.com/apis#match-v5): `metadata` (ID en spelers) en `info` (duur, patch, `teams` en `participants` met ~150 stats per speler).

## Wat zit erin

| Naam | Wat het doet |
|---|---|
| `load_matches()` | Alle opgehaalde matches als lijst van dicts |
| `load_timelines()` | Alle opgehaalde timelines als `{match_id: dict}` |
| `Storage` | Klasse die `collect.py` gebruikt om te lezen en te schrijven |

### Tabellen in de database

| Tabel | Inhoud |
|---|---|
| `players` | Gevonden spelers: `puuid`, `tier`, `division`, `league_points`, en of hun match-ID's al opgehaald zijn |
| `seed_pages` | Welke ladder-pagina's per tier/divisie al opgehaald zijn |
| `matches` | `match_id`, `status` (`pending` / `done` / `missing`) en de ruwe `json` |
| `timelines` | `match_id`, `status` en de ruwe `json` |

Voor statistieken kun je beter de tabellen in `data/stats.db` gebruiken; die zijn veel sneller dan steeds alle JSON inladen. Zie [`stats.md`](stats.md).

### Gelijktijdig gebruik

`Storage` wacht tot 30 seconden als een ander programma de database even vasthoudt (bijvoorbeeld `build-stats` dat aan het lezen is). Draai nooit twee crawlers tegelijk; zie de [limieten](../README.md#limieten-van-een-development-key).

Je kunt de database ook bekijken met een tool als [DB Browser for SQLite](https://sqlitebrowser.org).
