# `riot/stats.py`

Zet de ruwe match-JSON uit `data/league.db` om naar gewone tabellen in een aparte database, `data/stats.db`. Het dashboard en je eigen analyses lezen uit die tabellen. Dat is veel sneller dan elke keer alle JSON uitpakken (milliseconden in plaats van minuten).

`league.db` blijft de bron. `stats.db` is een afgeleide kopie: je kunt hem altijd weggooien en opnieuw opbouwen, bijvoorbeeld als er een kolom bij moet.

## Gebruik

```bash
python collect.py build-stats            # alleen nieuwe matches toevoegen (snel)
python collect.py build-stats --rebuild  # stats.db weggooien en alles opnieuw (~3 min per 80.000 matches)
```

Het dashboard doet dit zelf ook, maximaal elke 10 minuten. Het kan gewoon terwijl `collect.py run` draait: er wordt steeds maar kort uit `league.db` gelezen, zodat de crawler nooit hoeft te wachten.

## In Python

```python
import pandas as pd
from riot import stats

conn = stats.connect()   # alleen-lezen
df = pd.read_sql("SELECT champion_name, AVG(win) AS win_rate, COUNT(*) AS games "
                 "FROM participants WHERE team_position = 'MIDDLE' GROUP BY 1 ORDER BY games DESC", conn)
```

## Wat zit erin

| Naam | Wat het doet |
|---|---|
| `build(source, target, rebuild=False)` | Voegt alle opgehaalde matches toe die nog niet in `stats.db` staan; geeft het aantal toegevoegde matches terug. `rebuild=True` gooit `stats.db` eerst weg |
| `flatten(match, seed_tiers)` | Zet één match-dict om naar `(game, spelers, bans)` als rijen voor de tabellen. Hier voeg je velden toe |
| `connect(path)` | Alleen-lezen verbinding met `stats.db` |
| `patch_of(game_version)` | `"16.20.824.8524"` → `"16.20"`; `None` als de versie leeg is |
| `STATS_DB_PATH` | `data/stats.db` |
| `REMAKE_SECONDS` | `300`: korter dan dit telt als remake |
| `BATCH` | `200`: zoveel matches worden per keer uit `league.db` gelezen |
| `SCHEMA` | De `CREATE TABLE`- en `CREATE INDEX`-opdrachten |

Waarom de tabellen in een apart bestand staan en hoe dat samengaat met een draaiende crawler: zie [`datamodel.md`](../datamodel.md).

## Tabellen in `stats.db`

| Tabel | Eén rij per | Kolommen |
|---|---|---|
| `games` | match | `match_id`, `game_creation` (ms), `game_duration` (s), `patch` (bv. `16.20`), `match_tier`, `remake` |
| `participants` | speler per match (10 per match) | `match_id`, `puuid`, `riot_id`, `team_id` (100/200), `team_position`, `champion_id`, `champion_name`, `win`, `kills`, `deaths`, `assists`, `total_cs`, `gold_earned`, `damage_to_champions`, `vision_score` |
| `bans` | ban | `match_id`, `team_id`, `champion_id` |
| `champions` | champion | `champion_id`, `champion_name` |

- **`match_tier`**: de meest voorkomende tier van de spelers in die match die we via de ladder kennen (tabel `players` in `league.db`).
- **Remakes** (korter dan 5 minuten) staan in `games` met `remake = 1`, maar zonder spelers en bans.
- **`patch`** is leeg (`NULL`) bij de paar matches waarvan Riot geen versie meestuurt.
- **`riot_id`** is `naam#tag` zoals op het moment van die match; spelers kunnen hun naam veranderen.
- **`team_position`** is `TOP`, `JUNGLE`, `MIDDLE`, `BOTTOM` (ADC) of `UTILITY` (support), of leeg als Riot het niet kon bepalen.

Meer velden nodig, bijvoorbeeld voor een AI-model? Voeg ze toe in `flatten()` en het `SCHEMA`, en draai `build-stats --rebuild`.
