# `dashboard/`

Een Streamlit-dashboard met statistieken uit `data/stats.db`: tier list, matchups & synergy en spelersprofielen.

## Starten

```bash
source league_of_legends/bin/activate
streamlit run dashboard/app.py
```

Open daarna [http://localhost:8501](http://localhost:8501). Stoppen doe je met **Ctrl+C** in de terminal.

De eerste keer wordt `stats.db` opgebouwd; dat duurt een paar minuten (of doe het van tevoren met `python collect.py build-stats`). Daarna komen nieuwe matches er elke 10 minuten automatisch bij, of meteen met de knop **Nieuwe matches laden** links onderin.

Je kunt het dashboard laten draaien terwijl `collect.py run` doorloopt.

## Pagina's

| Pagina | Wat je ziet |
|---|---|
| **Overzicht** | Aantal matches, matches per patch en per tier |
| **Tier list** | Per rol: win rate, pick rate, ban rate, KDA en CS/min per champion, en een grafiek van win rate tegen pick rate |
| **Matchups & synergy** | Voor één champion: beste en slechtste tegenstanders in de lane, en beste teamgenoten (standaard de duo-partner, bv. ADC + support) |
| **Speler** | Zoek op Riot ID: KDA, CS/min, vision, vorm over de laatste games, champion pool en recente games |

Uitleg per pagina staat in [`views.md`](views.md).

## Filters

Links in de zijbalk, ze gelden voor alle pagina's behalve Speler:

| Filter | Standaard | Betekenis |
|---|---|---|
| **Patch** | De nieuwste | Leeg = alle patches |
| **Tier** | Leeg (alle) | De tier van een match: zie [`match_tier`](../riot/stats.md#tabellen-in-statsdb) |
| **Minimaal aantal games** | 20 | Champions, matchups en teamgenoten met minder games worden verborgen |

Let op kleine aantallen: een win rate van 70% over 20 games is vaak toeval. Bij 50 games kan de echte win rate tot zo'n 14 procentpunt hoger of lager liggen dan wat je ziet (95% zekerheid); bij 1000 games nog ~3 procentpunt.

## Bestanden

| Bestand | Wat | Docs |
|---|---|---|
| `app.py` | Startpunt: bouwt `stats.db` bij, toont de filters en de navigatie | [`app.md`](app.md) |
| `views/*.py` | De vier pagina's | [`views.md`](views.md) |
| `queries.py` | Alle SQL; elke functie geeft een pandas DataFrame terug. Ook bruikbaar in een notebook | [`queries.md`](queries.md) |
| `common.py` | Gedeelde stukken: cache, filters, kleuren, de win-rate-grafiek | [`common.md`](common.md) |
| `__init__.py` | Leeg; maakt van `dashboard` een package zodat `from dashboard import queries` werkt | |

## Hoe het samenhangt

```
streamlit run dashboard/app.py
        │
        ├─ riot/stats.build()        league.db ──► stats.db   (max. elke 10 min)
        ├─ zijbalk-filters           ──► st.session_state["filters"]
        └─ st.navigation ──► views/<pagina>.py
                                │
                                └─ common.query("<naam>", ...) ──► queries.<naam>(conn, ...) ──► stats.db
```

## Problemen

| Melding | Oplossing |
|---|---|
| *Geen database gevonden* | Haal eerst matches op met `python collect.py run` |
| *Geen champions met genoeg games* | Verlaag het minimum of kies meer patches/tiers |
| Pagina blijft lang laden bij de eerste start | Normaal: `stats.db` wordt opgebouwd. Of draai van tevoren `python collect.py build-stats` |
| Oude cijfers na een `--rebuild` | Klik **Nieuwe matches laden** of herstart Streamlit |
