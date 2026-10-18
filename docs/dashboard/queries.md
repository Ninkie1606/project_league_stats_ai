# `dashboard/queries.py`

Alle SQL van het dashboard. Elke functie krijgt een verbinding met `stats.db` en geeft een pandas DataFrame terug. Het bestand gebruikt zelf geen Streamlit, dus je kunt het ook in een notebook of script gebruiken.

## Gebruik in Python

```python
from riot import stats
from dashboard import queries

conn = stats.connect()

mid = queries.champion_table(conn, "MIDDLE", patches=["16.20"], tiers=[], min_games=50)
print(mid.head())

ahri = queries.matchups(conn, "Ahri", "MIDDLE", patches=[], tiers=["MASTER"], min_games=20)
duo  = queries.synergy(conn, "Jinx", "BOTTOM", "UTILITY", patches=[], tiers=[], min_games=20)
```

Draai het vanuit de projectmap, zodat `riot` en `dashboard` gevonden worden.

## Afspraken

- **Rates zijn fracties**: `0.53` betekent 53%.
- **`patches` en `tiers` zijn lijsten**; een lege lijst betekent "alles".
- **Remakes** tellen nergens mee.
- **Rollen** heten zoals bij Riot: `TOP`, `JUNGLE`, `MIDDLE`, `BOTTOM` (ADC), `UTILITY` (support).

## Functies

| Functie | Geeft terug |
|---|---|
| `champion_table(conn, role, patches, tiers, min_games)` | Per champion: `games`, `win_rate`, `kda`, `cs_per_min`, `pick_rate`, `ban_rate`. `role=None` = alle rollen samen |
| `matchups(conn, champion, role, patches, tiers, min_games)` | Per tegenstander in dezelfde rol: `opponent`, `games`, `win_rate` (van jouw champion), `gold_diff` (goud aan het einde, jij min tegenstander) |
| `synergy(conn, champion, role, partner_role, patches, tiers, min_games)` | Per teamgenoot: `teammate`, `teammate_role`, `games`, `win_rate`. `partner_role=None` = alle teamgenoten |
| `main_role(conn, champion)` | De rol waarin de champion het vaakst gespeeld wordt, bv. `"MIDDLE"` |
| `find_players(conn, text, limit=20)` | Spelers waarvan de Riot ID `text` bevat (hoofdletters maken niet uit): `puuid`, `riot_id` (de nieuwste), `games`, `last_played` |
| `player_matches(conn, puuid)` | Alle games van een speler, nieuwste eerst, met `date`, champion, rol, uitslag, K/D/A, CS, vision |
| `overview(conn)` | Aantal games per `patch` en `match_tier` |
| `filter_options(conn)` | `(patches, tiers, champions)` voor de keuzelijsten; patches nieuwste eerst, tiers van laag naar hoog |
| `total_games(conn, patches, tiers)` | Aantal games dat door de filters komt |

| Constante | Inhoud |
|---|---|
| `ROLES` | De vijf rollen in vaste volgorde |
| `TIERS` | Alle tiers van `IRON` tot `CHALLENGER`, voor het sorteren |

## Hoe de cijfers berekend worden

| Cijfer | Berekening |
|---|---|
| **Win rate** | Gewonnen games / gespeelde games |
| **Pick rate** | Games met deze champion (in deze rol) / alle games in het filter |
| **Ban rate** | Games waarin de champion door minstens één team gebanned is / alle games. Geldt voor alle rollen samen |
| **KDA** | (alle kills + alle assists) / alle deaths, over alle games samen. Niet het gemiddelde van de KDA per game, want één game met 0 deaths zou dat scheeftrekken |
| **CS/min** | Alle minions + jungle monsters / totale speeltijd in minuten |
| **Matchup** | De speler van het andere team met dezelfde `team_position` |
| **Synergy** | Elke speler van hetzelfde team, eventueel alleen in `partner_role` |
