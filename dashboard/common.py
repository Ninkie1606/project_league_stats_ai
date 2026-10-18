"""Shared pieces for the dashboard pages: cached queries, the sidebar filters and charts."""
import altair as alt
import streamlit as st

from dashboard import queries
from riot import stats

# Reference data-viz palette: one series hue, and blue <-> red for above / below 50% win rate.
SERIES = "#2a78d6"
GOOD = "#2a78d6"
BAD = "#e34948"
NEUTRAL = "#8a8985"

ROLE_LABELS = {"TOP": "Top", "JUNGLE": "Jungle", "MIDDLE": "Mid", "BOTTOM": "ADC", "UTILITY": "Support"}


@st.cache_data(ttl=600, show_spinner="Gegevens ophalen...")
def query(name, version, *args):
    """Run queries.<name>(conn, *args). `version` changes when stats.db gets new matches, which resets the cache."""
    conn = stats.connect()
    try:
        return getattr(queries, name)(conn, *args)
    finally:
        conn.close()


def filters():
    """The sidebar filters set in app.py: (version, patches, tiers, min_games)."""
    f = st.session_state["filters"]
    return f["version"], f["patches"], f["tiers"], f["min_games"]


def percent_columns(*names):
    return {name: st.column_config.NumberColumn(format="percent") for name in names}


def winrate_bars(df, label, title):
    """Horizontal bars from the 50% line to each win rate: blue above, red below."""
    base = alt.Chart(df, title=title).encode(
        y=alt.Y(f"{label}:N", sort=alt.EncodingSortField("win_rate", order="descending"), title=None),
        tooltip=[
            alt.Tooltip(f"{label}:N", title="Champion"),
            alt.Tooltip("games:Q", title="Games"),
            alt.Tooltip("win_rate:Q", title="Win rate", format=".1%"),
        ],
    )
    bars = base.mark_bar(cornerRadius=2, height={"band": 0.7}).encode(
        x=alt.X("win_rate:Q", title="Win rate", axis=alt.Axis(format="%")),
        x2=alt.datum(0.5),
        color=alt.condition(alt.datum.win_rate >= 0.5, alt.value(GOOD), alt.value(BAD)),
    )
    midline = alt.Chart().mark_rule(color=NEUTRAL, strokeDash=[4, 4]).encode(x=alt.datum(0.5))
    return (bars + midline).properties(height=max(120, 26 * len(df)))
