# `dashboard/common.py`

Gedeelde stukken voor de pagina's in `views/`. Alleen bruikbaar binnen Streamlit.

## Wat zit erin

| Naam | Wat het doet |
|---|---|
| `query(name, version, *args)` | Roept `queries.<name>(conn, *args)` aan op `stats.db` en cachet het resultaat 10 minuten |
| `filters()` | De filters uit de zijbalk: `(version, patches, tiers, min_games)` |
| `percent_columns(*names)` | `column_config` voor `st.dataframe` die die kolommen als percentage toont |
| `winrate_bars(df, label, title)` | Altair-grafiek: liggende balken vanaf de 50%-lijn; blauw erboven, rood eronder. `df` heeft de kolommen `label`, `games` en `win_rate` |
| `ROLE_LABELS` | Riot-rolnamen naar leesbare namen: `BOTTOM` → `ADC`, `UTILITY` → `Support`, ... |
| `SERIES`, `GOOD`, `BAD`, `NEUTRAL` | Kleuren van de grafieken |

## Gebruik in een pagina

```python
from dashboard.common import filters, query

version, patches, tiers, min_games = filters()
df = query("champion_table", version, "TOP", patches, tiers, min_games)
```

### Waarom `version`?

Streamlit herkent een resultaat in de cache aan de argumenten. Zonder `version` zou een query na nieuwe matches het oude antwoord blijven geven tot de 10 minuten om zijn. `version` is het aantal games in `stats.db`: komen er matches bij, dan verandert het getal en wordt alles opnieuw berekend.

## Kleuren

Eén blauw (`#2a78d6`) voor gewone grafieken, en blauw tegenover rood (`#e34948`) voor boven en onder 50% win rate. Grijs (`#8a8985`) voor de gestippelde 50%-lijn. Ze zijn gekozen zodat ze ook met kleurenblindheid en in dark mode van elkaar te onderscheiden zijn. Omdat elke balk ook een naam en een getal in de tooltip heeft, hangt niets alleen van kleur af.
