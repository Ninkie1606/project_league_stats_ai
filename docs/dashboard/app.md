# `dashboard/app.py`

Het startpunt van het dashboard. Je start het met:

```bash
streamlit run dashboard/app.py
streamlit run dashboard/app.py --server.port 8600   # andere poort, als 8501 bezet is
```

Streamlit draait dit bestand bij **elke** klik of filterwijziging opnieuw, voor elke pagina. Daarom staan hier de dingen die overal nodig zijn.

## Wat het doet, in volgorde

1. **Pad instellen**: voegt de projectmap toe aan `sys.path`, zodat `riot` en `dashboard` te importeren zijn (Streamlit zet alleen `dashboard/` zelf op het pad).
2. **Controleren** of `data/league.db` bestaat; zo niet, dan een foutmelding en stoppen.
3. **`stats.db` bijwerken** met `refresh()`: roept `riot.stats.build()` aan en geeft het aantal games terug.
   - Gecachet voor 10 minuten (`st.cache_data(ttl=600)`), dus het bouwen gebeurt hooguit één keer per 10 minuten, niet bij elke klik.
   - Een `threading.Lock` (`build_lock()`) zorgt dat twee browsertabs niet tegelijk bouwen.
   - Het aantal games dient als **versie**: verandert het, dan worden alle gecachete queries vanzelf ongeldig (zie [`common.md`](common.md)).
4. **Zijbalk** met de filters: patch, tier, minimaal aantal games, plus de knop **Nieuwe matches laden** (leegt de cache van `refresh()` en herlaadt).
5. **Filters opslaan** in `st.session_state["filters"]`, zodat de pagina's ze kunnen lezen via `common.filters()`.
6. **Navigatie** met `st.navigation` naar de vier pagina's in `views/`.

## Een pagina toevoegen

1. Maak `dashboard/views/mijn_pagina.py` (kijk naar een bestaande pagina als voorbeeld).
2. Voeg hem toe aan de lijst onderin `app.py`:
   ```python
   st.Page(views / "mijn_pagina.py", title="Mijn pagina", icon="📈"),
   ```

De map heet bewust `views/` en niet `pages/`: een map `pages/` naast het startbestand laat Streamlit de pagina's op de oude manier laden, zonder `app.py`, en dan ontbreken de filters.
