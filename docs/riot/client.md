# `riot/client.py`

Doet de requests naar de Riot API. Wacht automatisch als je te snel gaat, probeert opnieuw bij serverfouten en stopt met een duidelijke fout als de key verlopen is.

## Gebruik in Python

```python
from riot.client import RiotClient

client = RiotClient()          # leest RIOT_API_KEY uit .env

spelers = client.league_entries("GOLD", "I", page=1)   # lijst van ~205 spelers
top     = client.apex_league("CHALLENGER")             # alle Challenger-spelers
puuid   = spelers[0]["puuid"]

ids      = client.match_ids(puuid, count=20)            # recente ranked match-ID's
match    = client.match(ids[0])                         # volledige match als dict
timeline = client.timeline(ids[0])                      # minuut-per-minuut verloop

print(match["info"]["participants"][0]["championName"])
```

Deze calls slaan **niets** op; daarvoor gebruik je `collect.py`.

## Wat zit erin

| Naam | Wat het doet |
|---|---|
| `RiotClient(api_key=None)` | Maakt de client; zonder argument wordt de key uit `.env` gebruikt |
| `league_entries(tier, division, page=1)` | Spelers van een tier/divisie (Iron t/m Diamond) |
| `apex_league(tier)` | Spelers van `MASTER`, `GRANDMASTER` of `CHALLENGER` |
| `match_ids(puuid, count=20, start=0, start_time=None)` | Ranked solo match-ID's van een speler |
| `match(match_id)` | Volledige match-data (`None` als hij niet bestaat) |
| `timeline(match_id)` | Timeline van een match |
| `get(routing, path, params, method)` | De onderliggende request, voor andere endpoints |
| `request_count` | Hoeveel requests deze client gedaan heeft |
| `ApiKeyError` | Fout als de key ontbreekt, verlopen of ongeldig is |

## Foutafhandeling

| Antwoord | Wat de client doet |
|---|---|
| 200 | Geeft de JSON terug |
| 404 | Geeft `None` terug |
| 401 / 403 | Gooit `ApiKeyError` (key verlopen) |
| 429 | Wacht zo lang als Riot zegt (`Retry-After`) en probeert opnieuw |
| 500–504 / netwerkfout | Probeert tot 5 keer opnieuw met steeds langere pauzes |
