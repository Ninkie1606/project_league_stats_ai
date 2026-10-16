# Documentatie

Dit project haalt ranked solo/duo-matches van **EUW** op via de Riot API en slaat ze op in een SQLite-database (`data/league.db`), als dataset voor een AI-model.

## Snel starten

```bash
python -m venv league_of_legends          # eenmalig
source league_of_legends/bin/activate      # elke nieuwe terminal
pip install -r requirements.txt            # eenmalig

python collect.py run --tiers GOLD PLATINUM --forever   # ophalen tot de key verloopt
python collect.py stats                                  # wat zit er in de database?
```

Je API key staat in `.env` als `RIOT_API_KEY=RGAPI-...`. Een development key verloopt na 24 uur; haal dan een nieuwe op [developer.riotgames.com](https://developer.riotgames.com) en start het script opnieuw. Het gaat verder waar het gebleven was.

## Overzicht van de bestanden

| Bestand | Wat | Zelf gebruiken? |
|---|---|---|
| [`collect.py`](collect.md) | Het script dat de data ophaalt | **Ja**, vanuit de terminal |
| [`riot/client.py`](riot/client.md) | Praat met de Riot API | **Ja**, in Python voor losse requests |
| [`riot/storage.py`](riot/storage.md) | Leest en schrijft de database | **Ja**, in Python om de data in te laden |
| [`riot/config.py`](riot/config.md) | Instellingen (regio, queue, key) | Nee, alleen aanpassen |
| [`riot/rate_limiter.py`](riot/rate_limiter.md) | Zorgt dat we de limieten niet overschrijden | Nee, wordt door de client gebruikt |
| [`tests/`](tests.md) | Automatische tests | **Ja**, om te controleren of alles werkt |
| `requirements.txt` | Python-packages die nodig zijn (`requests`, `python-dotenv`) | Via `pip install -r requirements.txt` |
| `.gitignore` | Wat niet naar GitHub gaat: `.env`, de venv, `data/` | Nee |
| `data/league.db` | De database (wordt automatisch gemaakt) | Via `riot/storage.py` |

## Hoe het werkt

```
collect.py ──► riot/client.py ──► Riot API
   │              │
   │              └─ riot/rate_limiter.py  (wacht als het te snel gaat)
   │
   └──► riot/storage.py ──► data/league.db
```

1. **Spelers zoeken**: per tier/divisie wordt een pagina van de ranked ladder opgehaald (~205 spelers per pagina).
2. **Match-ID's**: per speler de laatste 20 ranked match-ID's.
3. **Matches**: elke match wordt één keer opgehaald en als ruwe JSON opgeslagen.
4. Zijn alle spelers verwerkt, dan wordt automatisch de volgende pagina spelers opgehaald.

## Limieten van een development key

- 20 requests per seconde **en** 100 requests per 2 minuten, apart voor `euw1` (spelers) en `europe` (matches).
- Het script blijft net onder die limieten (18/s en 95/2 min): ongeveer **3000 matches per uur**.
- Laat niet twee keer tegelijk het script draaien met dezelfde key; ze delen dezelfde limiet.
