import altair as alt
import streamlit as st

from dashboard.common import NEUTRAL, ROLE_LABELS, SERIES, filters, percent_columns, query
from dashboard.queries import ROLES

version, patches, tiers, min_games = filters()

st.title("Tier list")
role = st.segmented_control("Rol", ["ALL"] + ROLES, default="TOP",
                            format_func=lambda r: "Alle rollen" if r == "ALL" else ROLE_LABELS[r])
role = None if role in (None, "ALL") else role

total = query("total_games", version, patches, tiers)
df = query("champion_table", version, role, patches, tiers, min_games)
st.caption(f"{total:,} matches in filter · {len(df)} champions met minstens {min_games} games")
if df.empty:
    st.info("Geen champions met genoeg games. Verlaag het minimum of kies meer patches/tiers.")
    st.stop()

labels = df.nlargest(12, "games")
points = alt.Chart(df).mark_circle(size=90, color=SERIES, opacity=0.85, stroke="white", strokeWidth=1).encode(
    x=alt.X("pick_rate:Q", title="Pick rate", axis=alt.Axis(format="%")),
    y=alt.Y("win_rate:Q", title="Win rate", axis=alt.Axis(format="%"), scale=alt.Scale(zero=False)),
    tooltip=[
        alt.Tooltip("champion_name:N", title="Champion"),
        alt.Tooltip("games:Q", title="Games", format=","),
        alt.Tooltip("win_rate:Q", title="Win rate", format=".1%"),
        alt.Tooltip("pick_rate:Q", title="Pick rate", format=".1%"),
        alt.Tooltip("ban_rate:Q", title="Ban rate", format=".1%"),
    ],
)
text = alt.Chart(labels).mark_text(align="left", dx=8, fontSize=11).encode(
    x="pick_rate:Q", y="win_rate:Q", text="champion_name:N"
)
midline = alt.Chart().mark_rule(color=NEUTRAL, strokeDash=[4, 4]).encode(y=alt.datum(0.5))
st.altair_chart((points + text + midline).properties(title="Win rate tegen pick rate", height=420),
                width="stretch")

table = df.rename(columns={
    "champion_name": "Champion", "games": "Games", "win_rate": "Win rate", "pick_rate": "Pick rate",
    "ban_rate": "Ban rate", "kda": "KDA", "cs_per_min": "CS/min",
})[["Champion", "Games", "Win rate", "Pick rate", "Ban rate", "KDA", "CS/min"]]
st.dataframe(
    table, hide_index=True, width="stretch",
    column_config={**percent_columns("Win rate", "Pick rate", "Ban rate"),
                   "KDA": st.column_config.NumberColumn(format="%.2f"),
                   "CS/min": st.column_config.NumberColumn(format="%.1f")},
)
st.caption("Ban rate geldt voor alle rollen samen. Klik op een kolomkop om te sorteren.")
