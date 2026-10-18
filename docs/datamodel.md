# Datamodel: ruwe JSON plus tabellen

Het project bewaart de data op twee plekken. Hier staat waarom.

| Database | Inhoud | Wie schrijft | Wie leest |
|---|---|---|---|
| `data/league.db` | De ruwe JSON van Riot, precies zoals die binnenkomt | `collect.py` | `riot/stats.py`, je eigen scripts |
| `data/stats.db` | Gewone tabellen (`games`, `participants`, `bans`, `champions`) met indexen | `riot/stats.py` | Het dashboard, je eigen analyses |

`stats.db` is volledig afgeleid van `league.db`. Je kunt hem altijd weggooien en opnieuw opbouwen met `python collect.py build-stats --rebuild`.

## Waarom niet alleen JSON?

Om iets uit te rekenen (een win rate, een matchup) moet je bij alleen JSON elke match uitpakken, bij elke vraag opnieuw. Een match is 20–90 KB tekst; uitpakken kost 1–3 ms per match.

| Matches | Alleen JSON | Tabellen met index |
|---|---|---|
| 5.000 | 5–15 seconden | < 0,05 seconde |
| 80.000 (± 1 dag crawlen) | 1–3 minuten | 0,1–2 seconden (gemeten) |
| 500.000 | 10–25 minuten | geschat tot ~10 seconden voor de tier list; dan loont een extra tabel met vooraf berekende cijfers |

Het dashboard rekent opnieuw bij elke filterwijziging, dus alleen JSON zou na een dag crawlen al te traag zijn. Ook zijn vragen als "tegen wie speelt Ahri in de lane" met tabellen één korte SQL-query; met JSON moet je in Python door alle tien spelers van elke match lopen.

## Waarom de JSON bewaren?

- **Niets kwijt**: Riot stuurt ~150 velden per speler, de tabellen gebruiken er nu zo'n 15. Wil je later meer, bijvoorbeeld voor een AI-model (first blood, wards, items), dan voeg je een kolom toe en bouw je opnieuw op. Er hoeft niets opnieuw opgehaald te worden.
- **De crawler blijft simpel**: `collect.py` slaat alleen op wat binnenkomt en kan altijd verder waar hij was.

De prijs is klein: `stats.db` is ongeveer 5% van de grootte van `league.db` (± 380 MB bij 83.000 matches), en het bouwen kost ~3 minuten per 80.000 matches. Daarna worden alleen nieuwe matches toegevoegd, wat een paar seconden duurt.

## Waarom een aparte database?

Een SQLite-bestand kan maar door één programma tegelijk beschreven worden. Als `build-stats` lang in `league.db` zou schrijven, moet de crawler wachten. Na 30 seconden geeft hij een fout en stopt hij. (Een crawler die al draaide vóór deze wijziging wacht maar 5 seconden; dat geldt tot je hem herstart.)

Daarom:

- schrijft `build-stats` alleen naar `stats.db`;
- leest het uit `league.db` in kleine stukjes van 200 matches (± 0,3 seconde per stukje), zodat de crawler nooit lang hoeft te wachten;
- opent het dashboard `stats.db` alleen-lezen.

Zo kunnen de crawler, `build-stats` en het dashboard tegelijk draaien.

## Van JSON naar tabellen

```
league.db: matches.json  (1 match = 1 JSON-tekst)
      │
      │  riot/stats.flatten()
      ▼
stats.db
  games         1 rij per match       match_id, patch, duur, match_tier, remake
  participants  10 rijen per match    speler, team, rol, champion, win, K/D/A, CS, goud, schade, vision
  bans          ~10 rijen per match   team, champion_id
  champions     1 rij per champion    champion_id → naam
```

Alle kolommen staan in [`riot/stats.md`](riot/stats.md).
