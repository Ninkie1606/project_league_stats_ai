# `collect.py`

Het hoofdscript: haalt spelers en matches op en slaat ze op in `data/league.db`. Je kunt het altijd stoppen met **Ctrl+C**; de volgende keer gaat het verder waar het gebleven was, zonder iets dubbel op te halen.

## Gebruik

Eerst de venv activeren: `source league_of_legends/bin/activate`.

### `run`: matches ophalen

```bash
python collect.py run --tiers GOLD --max-matches 500            # 500 matches en dan stoppen
python collect.py run --tiers GOLD PLATINUM EMERALD --forever  # doorgaan tot de key verloopt
python collect.py run --tiers CHALLENGER GRANDMASTER --forever  # alleen hoog elo
python collect.py run --tiers SILVER --divisions I II --forever # alleen Silver I en II
python collect.py run --tiers DIAMOND --since 2026-09-01        # alleen matches vanaf die datum
```

| Optie | Standaard | Betekenis |
|---|---|---|
| `--tiers` | `GOLD` | Welke tiers: `IRON BRONZE SILVER GOLD PLATINUM EMERALD DIAMOND MASTER GRANDMASTER CHALLENGER` |
| `--divisions` | `I II III IV` | Welke divisies (geldt niet voor Master+) |
| `--max-matches` | `1000` | Stop na zoveel matches |
| `--forever` | uit | Negeer `--max-matches` en ga door tot de API key verloopt |
| `--ids-per-player` | `20` | Hoeveel recente matches per speler. Lager = meer verschillende spelers |
| `--since` | geen | Alleen matches vanaf deze datum (`YYYY-MM-DD`), bv. het begin van een patch |
| `-v` | uit | Meer details in de log (zet het vóór `run`: `python collect.py -v run ...`) |

### `timelines`: timelines ophalen (optioneel)

Haalt de minuut-per-minuut timeline op voor matches die al in de database staan.

```bash
python collect.py timelines --max 500
python collect.py timelines --forever
```

### `stats`: wat zit er in de database?

```bash
python collect.py stats
```

```
players          710     # gevonden spelers
players_done     16      # spelers waarvan de match-ID's zijn opgehaald
matches_done     313     # opgehaalde matches
matches_pending  7       # match-ID's die nog opgehaald moeten worden
timelines_done   0
```

## Lang laten draaien

Met `--forever` draait het tot de key verloopt (max. 24 uur). Dan stopt het met de melding *"API key verlopen of ongeldig"*. Zet een nieuwe key in `.env` en start opnieuw.

Bij netwerkproblemen wacht het script 60 seconden en probeert het opnieuw, dus een korte internetstoring stopt de run niet.

Om de terminal te kunnen sluiten terwijl het doorloopt, gebruik je **tmux** (aanrader) of `nohup`.

### Met tmux

tmux houdt een terminalsessie open op de achtergrond. Je kunt het venster sluiten en later terugkomen; het script draait gewoon door.

**Installeren** (eenmalig):

```bash
sudo apt install tmux        # Ubuntu / Debian / WSL
brew install tmux            # macOS
```

**Sessie starten en het script draaien:**

```bash
tmux new -s league                              # nieuwe sessie met de naam "league"
cd ~/workspace/project_league_stats_ai
source league_of_legends/bin/activate
python collect.py run --tiers GOLD PLATINUM --forever
```

**Loskoppelen** (het script blijft draaien): druk `Ctrl+B`, laat los, en druk dan `D`. Nu kun je de terminal sluiten.

**Later terugkomen:**

```bash
tmux ls                      # welke sessies zijn er?
tmux attach -t league        # terug naar de sessie "league"
```

**Stoppen:**

```bash
# in de sessie: Ctrl+C stopt het script netjes, daarna `exit` sluit de sessie
tmux kill-session -t league  # of van buitenaf: sessie (en script) meteen afsluiten
```

Gebruik bij voorkeur `Ctrl+C`; dan meldt het script nog wat er in de database staat. Er gaat met `kill-session` geen data verloren, want elke match wordt meteen opgeslagen.

### Met nohup

```bash
nohup python collect.py run --tiers GOLD PLATINUM --forever > data/collect.log 2>&1 &
tail -f data/collect.log     # meekijken (Ctrl+C stopt alleen het meekijken)
pkill -INT -f collect.py     # het script netjes stoppen
```

Let op: als je pc in slaapstand gaat, pauzeert het script ook.
