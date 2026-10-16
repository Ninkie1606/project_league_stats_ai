# project_league_stats_ai

Haalt ranked League of Legends-matches (EUW) op via de Riot API als dataset voor een AI-model.

```bash
python -m venv league_of_legends && source league_of_legends/bin/activate
pip install -r requirements.txt
python collect.py run --tiers GOLD PLATINUM --forever
```

Zie [`docs/`](docs/README.md) voor de uitleg per bestand.
