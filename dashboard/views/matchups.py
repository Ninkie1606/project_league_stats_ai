import streamlit as st

from dashboard.common import ROLE_LABELS, filters, percent_columns, query, winrate_bars
from dashboard.queries import ROLES

DUO = {"BOTTOM": "UTILITY", "UTILITY": "BOTTOM", "JUNGLE": "MIDDLE", "MIDDLE": "JUNGLE"}

version, patches, tiers, min_games = filters()
_, _, champions = query("filter_options", version)

st.title("Matchups & synergy")
left, right = st.columns(2)
champion = left.selectbox("Champion", champions, index=champions.index("Ahri") if "Ahri" in champions else 0)
main = query("main_role", version, champion) or "MIDDLE"
role = right.selectbox("Rol", ROLES, index=ROLES.index(main), format_func=ROLE_LABELS.get)

st.header("Tegen wie in de lane")
m = query("matchups", version, champion, role, patches, tiers, min_games)
if m.empty:
    st.info(f"Geen tegenstanders met minstens {min_games} games. Verlaag het minimum links.")
else:
    st.caption(f"{m.games.sum():,} games van {champion} als {ROLE_LABELS[role]}, "
               f"{len(m)} tegenstanders met minstens {min_games} games")
    best, worst = st.columns(2)
    best.altair_chart(winrate_bars(m.head(10), "opponent", "Beste matchups"), width="stretch")
    worst.altair_chart(winrate_bars(m.tail(10), "opponent", "Slechtste matchups"), width="stretch")
    with st.expander("Alle matchups"):
        st.dataframe(
            m.rename(columns={"opponent": "Tegenstander", "games": "Games", "win_rate": "Win rate",
                              "gold_diff": "Goudverschil"}),
            hide_index=True, width="stretch",
            column_config={**percent_columns("Win rate"),
                           "Goudverschil": st.column_config.NumberColumn(format="%+.0f",
                                                                         help="Gemiddeld aan het einde van de game")},
        )

st.header("Met wie in het team")
options = [None] + ROLES
partner = st.selectbox("Rol van de teamgenoot", options, index=options.index(DUO.get(role)),
                       format_func=lambda r: "Alle rollen" if r is None else ROLE_LABELS[r])
s = query("synergy", version, champion, role, partner, patches, tiers, min_games)
if s.empty:
    st.info(f"Geen teamgenoten met minstens {min_games} games. Verlaag het minimum links.")
else:
    if partner is None:
        s["teammate"] = s.teammate + " (" + s.teammate_role.map(ROLE_LABELS).fillna("?") + ")"
    st.altair_chart(winrate_bars(s.head(10), "teammate", "Beste teamgenoten"), width="stretch")
    with st.expander("Alle teamgenoten"):
        st.dataframe(s.rename(columns={"teammate": "Teamgenoot", "teammate_role": "Rol", "games": "Games",
                                       "win_rate": "Win rate"}),
                     hide_index=True, width="stretch", column_config=percent_columns("Win rate"))
st.caption("Win rates boven of onder 50% met weinig games zijn vaak toeval. Kijk ook naar het aantal games.")
