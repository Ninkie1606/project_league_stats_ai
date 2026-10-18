import altair as alt
import streamlit as st

from dashboard.common import NEUTRAL, ROLE_LABELS, SERIES, filters, percent_columns, query

version, _, _, _ = filters()

st.title("Speler")
text = st.text_input("Zoek op Riot ID", placeholder="bv. naam of naam#EUW")
if not text:
    st.caption("Alleen matches die in de database staan tellen mee; meestal zijn dat de laatste ~20 ranked games.")
    st.stop()

hits = query("find_players", version, text)
if hits.empty:
    st.info("Geen speler gevonden met die Riot ID.")
    st.stop()
puuid = st.selectbox("Speler", hits.puuid, format_func=lambda p: "{} ({} games)".format(
    *hits.loc[hits.puuid == p, ["riot_id", "games"]].iloc[0]))
games = query("player_matches", version, puuid)

minutes = games.game_duration.sum() / 60
cols = st.columns(5)
cols[0].metric("Games", len(games))
cols[1].metric("Win rate", f"{games.win.mean():.0%}")
cols[2].metric("KDA", f"{(games.kills.sum() + games.assists.sum()) / max(games.deaths.sum(), 1):.2f}")
cols[3].metric("CS/min", f"{games.total_cs.sum() / minutes:.1f}")
cols[4].metric("Vision/min", f"{games.vision_score.sum() / minutes:.2f}")

if len(games) >= 5:
    trend = games.sort_values("game_creation").reset_index(drop=True)
    trend["game"] = trend.index + 1
    trend["rolling"] = trend.win.rolling(5, min_periods=5).mean()
    trend = trend.dropna(subset=["rolling"])
    hover = alt.selection_point(fields=["game"], nearest=True, on="pointerover", empty=False)
    base = alt.Chart(trend).encode(x=alt.X("game:Q", title="Game (oud → nieuw)", axis=alt.Axis(tickMinStep=1)))
    line = base.mark_line(color=SERIES, strokeWidth=2).encode(
        y=alt.Y("rolling:Q", title="Win rate (laatste 5 games)", axis=alt.Axis(format="%"),
                scale=alt.Scale(domain=[0, 1])))
    points = base.mark_circle(size=80, color=SERIES).encode(
        y="rolling:Q",
        opacity=alt.condition(hover, alt.value(1), alt.value(0)),
        tooltip=[alt.Tooltip("date:T", title="Datum", format="%d-%m-%Y"),
                 alt.Tooltip("champion_name:N", title="Champion"),
                 alt.Tooltip("rolling:Q", title="Win rate laatste 5", format=".0%")],
    ).add_params(hover)
    rule = base.mark_rule(color=NEUTRAL).encode(opacity=alt.condition(hover, alt.value(0.5), alt.value(0)))
    midline = alt.Chart().mark_rule(color=NEUTRAL, strokeDash=[4, 4]).encode(y=alt.datum(0.5))
    st.altair_chart((line + rule + points + midline).properties(title="Vorm", height=260),
                    width="stretch")

left, right = st.columns([2, 3])
pool = games.groupby("champion_name").agg(
    Games=("win", "size"), **{"Win rate": ("win", "mean")},
    kills=("kills", "sum"), deaths=("deaths", "sum"), assists=("assists", "sum"),
).reset_index()
pool["KDA"] = (pool.kills + pool.assists) / pool.deaths.clip(lower=1)
pool = pool.sort_values("Games", ascending=False).rename(columns={"champion_name": "Champion"})
left.subheader("Champion pool")
left.dataframe(pool[["Champion", "Games", "Win rate", "KDA"]], hide_index=True, width="stretch",
               column_config={**percent_columns("Win rate"), "KDA": st.column_config.NumberColumn(format="%.2f")})

recent = games.assign(
    Uitslag=games.win.map({1: "✅ Winst", 0: "❌ Verlies"}),
    Rol=games.team_position.map(ROLE_LABELS),
    KDA=games.kills.astype(str) + " / " + games.deaths.astype(str) + " / " + games.assists.astype(str),
    Duur=(games.game_duration // 60).astype(str) + " min",
).rename(columns={"date": "Datum", "champion_name": "Champion", "total_cs": "CS", "patch": "Patch"})
right.subheader("Recente games")
right.dataframe(recent[["Datum", "Champion", "Rol", "Uitslag", "KDA", "CS", "Duur", "Patch"]],
                hide_index=True, width="stretch",
                column_config={"Datum": st.column_config.DatetimeColumn(format="DD-MM-YYYY HH:mm")})
