# `tests/`

Automatische tests. Ze gebruiken de echte API **niet** en kosten dus geen requests.

## Gebruik

```bash
python -m unittest -v
```

Alles moet eindigen met `OK`.

## Wat zit erin

| Bestand | Test |
|---|---|
| `test_rate_limiter.py` | De limiter wacht op tijd en komt nooit boven 20/s of 100/2 min (met een nep-klok, dus de test duurt geen 2 minuten) |
| `test_stats.py` | Matches worden goed omgezet naar tabellen (remakes en lege bans overgeslagen, niets dubbel), en de win rates van tier list, matchups en synergy kloppen |
| `test_storage.py` | Ladder-pagina's lopen netjes door, spelers worden per tier gekozen, en match-ID's worden niet dubbel opgeslagen |
