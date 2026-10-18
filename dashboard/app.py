"""League stats dashboard. Start with: streamlit run dashboard/app.py"""
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # so `riot` and `dashboard` import

import streamlit as st  # noqa: E402

from dashboard import queries  # noqa: E402
from riot import config, stats  # noqa: E402

st.set_page_config(page_title="League stats", page_icon="📊", layout="wide")


@st.cache_resource
def build_lock():
    return threading.Lock()


@st.cache_data(ttl=600, show_spinner=False)
def refresh():
    """Add new matches from league.db to stats.db (at most every 10 minutes). Returns the number of games."""
    with build_lock():
        stats.build()
    conn = stats.connect()
    try:
        return conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
    finally:
        conn.close()


if not config.DB_PATH.exists():
    st.error(f"Geen database gevonden op `{config.DB_PATH}`. Haal eerst matches op met `python collect.py run`.")
    st.stop()

first_build = not stats.STATS_DB_PATH.exists()
with st.spinner("stats.db voor het eerst opbouwen; dat duurt een paar minuten..." if first_build
                else "Nieuwe matches verwerken..."):
    version = refresh()

conn = stats.connect()
patches, tiers, _ = queries.filter_options(conn)
conn.close()

with st.sidebar:
    st.header("Filters")
    chosen_patches = st.multiselect("Patch", patches, default=patches[:1], placeholder="Alle patches")
    chosen_tiers = st.multiselect("Tier", tiers, placeholder="Alle tiers")
    min_games = st.number_input("Minimaal aantal games", min_value=1, value=20, step=10,
                                help="Champions en matchups met minder games worden verborgen.")
    st.caption(f"{version:,} matches in stats.db")
    if st.button("Nieuwe matches laden"):
        refresh.clear()
        st.rerun()

st.session_state["filters"] = {
    "version": version, "patches": chosen_patches, "tiers": chosen_tiers, "min_games": int(min_games),
}

views = Path(__file__).parent / "views"
st.navigation([
    st.Page(views / "overview.py", title="Overzicht", icon="🏠", default=True),
    st.Page(views / "tier_list.py", title="Tier list", icon="🏆"),
    st.Page(views / "matchups.py", title="Matchups & synergy", icon="⚔️"),
    st.Page(views / "player.py", title="Speler", icon="👤"),
]).run()
