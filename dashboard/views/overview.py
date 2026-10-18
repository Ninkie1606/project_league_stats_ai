import altair as alt
import streamlit as st

from dashboard.common import SERIES, filters, query
from dashboard.queries import TIERS

version, patches, tiers, _ = filters()

st.title("League stats: ranked solo/duo EUW")
st.write("Statistieken uit de matches die `collect.py` heeft opgehaald. Kies links de patch en tier; "
         "die filters gelden voor alle pagina's behalve Speler.")

df = query("overview", version)
selected = df
if patches:
    selected = selected[selected.patch.isin(patches)]
if tiers:
    selected = selected[selected.match_tier.isin(tiers)]

a, b, c = st.columns(3)
a.metric("Matches (alle data)", f"{df.games.sum():,}")
b.metric("Matches in filter", f"{selected.games.sum():,}")
c.metric("Patches", df.patch.nunique())

per_patch = df.groupby("patch", as_index=False).games.sum()
per_patch["order"] = per_patch.patch.map(lambda p: tuple(int(x) for x in p.split(".")))
per_patch = per_patch.sort_values("order").tail(12)
st.altair_chart(
    alt.Chart(per_patch, title="Matches per patch (laatste 12)").mark_bar(
        color=SERIES, cornerRadiusTopLeft=4, cornerRadiusTopRight=4
    ).encode(
        x=alt.X("patch:N", sort=per_patch.patch.tolist(), title="Patch"),
        y=alt.Y("games:Q", title="Matches"),
        tooltip=[alt.Tooltip("patch:N", title="Patch"), alt.Tooltip("games:Q", title="Matches", format=",")],
    ),
    width="stretch",
)

per_tier = selected.groupby("match_tier", as_index=False).games.sum()
per_tier = per_tier.sort_values("match_tier", key=lambda s: s.map(TIERS.index), ascending=False)
st.subheader("Matches per tier (in filter)")
st.dataframe(per_tier.rename(columns={"match_tier": "Tier", "games": "Matches"}), hide_index=True)
st.caption("De tier van een match is de meest voorkomende tier van de spelers die `collect.py` "
           "via de ladder heeft gevonden. De andere spelers in die match hebben vaak een vergelijkbare rank.")
