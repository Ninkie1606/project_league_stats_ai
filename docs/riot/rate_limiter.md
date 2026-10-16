# `riot/rate_limiter.py`

Houdt bij hoeveel requests er gedaan zijn en laat het script wachten voordat een limiet bereikt wordt. Wordt automatisch gebruikt door `RiotClient`; je roept het niet zelf aan.

## Wat zit erin

| Naam | Wat het doet |
|---|---|
| `RateLimiter` | Houdt per "bucket" (bv. `europe` of `europe:match`) de tijdstippen van recente requests bij |
| `RateLimiter.acquire(*keys)` | Wacht tot een request in alle opgegeven buckets mag, en telt hem |
| `RateLimiter.set_limits(key, limits)` | Stelt de limieten van een bucket in, bv. `[(20, 1), (100, 120)]` |
| `RateLimiter.sync_counts(key, counts)` | Neemt Riots teller over, zodat een herstart weet wat een vorige run al gebruikt heeft |
| `safe_limit(limit)` | Veiligheidsmarge: 20 → 18, 100 → 95 |
| `parse_limit_header(value)` | Leest Riots header `"20:1,100:120"` als `[(20, 1), (100, 120)]` |

## Buckets

Riot heeft limieten op twee niveaus, en de limiter volgt ze allebei:

- **App-limiet** per server (`euw1`, `europe`): 20/s en 100/2 min voor een development key.
- **Method-limiet** per endpoint (bv. `euw1:league-entries` = 50 per 10 s). Die leert de client uit Riots headers.
