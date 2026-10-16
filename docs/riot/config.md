# `riot/config.py`

Vaste instellingen voor de rest van het project. Je roept dit bestand niet zelf aan; pas het alleen aan als je bv. een andere regio wilt.

## Wat zit erin

| Naam | Waarde | Betekenis |
|---|---|---|
| `RIOT_API_KEY` | uit `.env` | Je API key. `.env` heeft altijd voorrang op een oude key in je terminal |
| `PLATFORM` | `"euw1"` | Server voor spelers/ladder (league-v4) |
| `REGION` | `"europe"` | Server voor matches (match-v5) |
| `QUEUE` | `420` | Ranked solo/duo |
| `QUEUE_TYPE` | `"RANKED_SOLO_5x5"` | Zelfde queue, zoals league-v4 hem noemt |
| `DEFAULT_APP_LIMITS` | `[(20, 1), (100, 120)]` | Startlimieten van een development key; worden bijgewerkt met wat Riot terugstuurt |
| `DB_PATH` | `data/league.db` | Waar de database staat |
