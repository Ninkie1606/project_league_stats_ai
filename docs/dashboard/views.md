# `dashboard/views/`

De vier pagina's van het dashboard. Elk bestand is een gewoon Streamlit-script dat de filters leest met `common.filters()` en data ophaalt met `common.query()`. Ze worden geladen door [`app.py`](app.md).

## `overview.py`: Overzicht

| Onderdeel | Inhoud |
|---|---|
| Drie getallen | Matches in de hele dataset, matches die door het filter komen, aantal patches |
| Staafgrafiek | Matches per patch, de laatste 12 patches |
| Tabel | Matches per tier (binnen het filter), van hoog naar laag |

## `tier_list.py`: Tier list

| Onderdeel | Inhoud |
|---|---|
| Rolkeuze | Top, Jungle, Mid, ADC, Support of alle rollen samen |
| Spreidingsgrafiek | Elke stip is een champion: rechts = vaak gekozen, hoog = vaak gewonnen. De 12 meest gespeelde staan erbij met naam. Beweeg over een stip voor de cijfers |
| Tabel | Games, win rate, pick rate, ban rate, KDA, CS/min. Klik op een kolomkop om te sorteren |

Rechtsboven in de grafiek staan sterke, populaire champions; linksboven sterke champions die weinig gekozen worden.

## `matchups.py`: Matchups & synergy

| Onderdeel | Inhoud |
|---|---|
| Champion en rol | De rol staat standaard op de rol waarin de champion het meest gespeeld wordt |
| **Tegen wie in de lane** | Twee grafieken: de 10 beste en de 10 slechtste tegenstanders. Onder *Alle matchups* staat de volledige tabel met het goudverschil aan het einde van de game |
| **Met wie in het team** | De 10 beste teamgenoten, met de volledige tabel eronder. De rol van de teamgenoot staat standaard op de duo-partner |

Standaard duo-partners:

| Jouw rol | Teamgenoot |
|---|---|
| ADC | Support |
| Support | ADC |
| Jungle | Mid |
| Mid | Jungle |
| Top | Alle rollen |

## `player.py`: Speler

Zoek op (een deel van) een Riot ID, bv. `naam` of `naam#EUW`, en kies de speler uit de lijst.

| Onderdeel | Inhoud |
|---|---|
| Vijf getallen | Games, win rate, KDA, CS/min, vision score per minuut |
| Vorm | Win rate over de laatste 5 games, van oud naar nieuw (vanaf 5 games). Beweeg over de lijn voor datum en champion |
| Champion pool | Per champion: games, win rate, KDA |
| Recente games | Datum, champion, rol, uitslag, K/D/A, CS, duur, patch |

Alleen games die in de database staan tellen mee. Voor spelers die `collect.py` via de ladder heeft gevonden zijn dat meestal hun laatste ~20 ranked games; andere spelers staan er vaak maar een paar keer in, als tegenstander of teamgenoot. De filters in de zijbalk gelden hier niet.
