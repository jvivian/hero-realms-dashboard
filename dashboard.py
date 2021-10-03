import os

import pandas as pd
import requests
import streamlit as st
from streamlit_lottie import st_lottie
import altair as alt
from urban import urban_theme

alt.themes.register("Urban", urban_theme)
alt.themes.enable("Urban")

st.set_page_config(
    page_title="Hero Dashboard",
    page_icon="🤘",
    layout="wide",
    initial_sidebar_state="auto",
)

st.markdown(
    """
    <style>
    [data-testid="stSidebar"][aria-expanded="true"] > div:first-child {
        width: 200px;
    }
    [data-testid="stSidebar"][aria-expanded="false"] > div:first-child {
        width: 200px;
        margin-left: -200px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

SHEET_ID = "1DU1JpW27oOWjhTijTSW2tBGyMjHGioCW_E8V1syhAkE"
SHEET_NAME = "Game Records"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"


def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()


def center_text(text, size="h1", container=None):
    txt = f"<{size} style='text-align: center; color: black;'>{text}</{size}>"
    if container is None:
        return st.markdown(txt, unsafe_allow_html=True)
    else:
        return container.markdown(txt, unsafe_allow_html=True)


@st.cache
def get_data(url):
    df = pd.read_csv(url).iloc[:, :10]
    cols = ["opponent_name", "opponent_class", "opponent_level", "opponent_hp"]
    cols += [
        "self_class",
        "self_level",
        "self_hp",
        "starting_turn",
        "turns",
        "won",
    ]  # , 'beta']
    df.columns = cols
    df["won"] = df.won.astype(bool)
    df["starting_turn"] = [
        "Went First" if x == 1 else "Went Second" for x in df.starting_turn
    ]
    return df.dropna()


def banner(df):
    c1, c2, c3 = st.columns([1, 3, 1])
    with c1:
        st_lottie(
            load_lottieurl(
                "https://assets10.lottiefiles.com/packages/lf20_z9ed2jna.json"
            ),
            height=150,
        )
    with c2:
        center_text("Hero Realms Dashboard")
        num_wins = len(df[df.won == True])
        perc = round(num_wins / len(df), 1) * 100
        text = f"{len(df)} Games - {len(df[df.won == True])} Wins - {perc}%"
        center_text(text, size="h2")

        with c3:
            st_lottie(
                load_lottieurl(
                    "https://assets1.lottiefiles.com/packages/lf20_OT15QW.json"
                ),
                height=150,
            )


def class_summary_plot(df):
    games_played = (
        df.groupby("self_class")
        .opponent_class.value_counts()
        .reset_index(name="Games Played")
    )
    games_won = (
        df.groupby(["self_class", "opponent_class"])
        .won.sum()
        .reset_index(name="Games Won")
    )
    data = games_played.merge(games_won)
    data["Win Percentage"] = round(data["Games Won"] / data["Games Played"] * 100, 2)
    data = data.rename(
        {"self_class": "My Hero", "opponent_class": "Opponent"}, axis="columns"
    )
    return (
        alt.Chart(data)
        .mark_circle(opacity=0.5)
        .encode(
            alt.X("Games Played", title="Games Played"),
            alt.Y("My Hero:N"),
            color="Opponent:N",
            size="Win Percentage",
            tooltip=["My Hero", "Opponent", "Win Percentage", "Games Played"],
        )
        .properties(height=250)
    )


def class_stats(df, class_select, level_range, opponent_class=None):
    sub = (
        df.loc[df.self_class == class_select]
        .loc[lambda x: level_range[0] <= x.self_level]
        .loc[lambda x: x.self_level <= level_range[1]]
    )
    sub = sub[sub.opponent_class == opponent_class] if opponent_class else sub
    if opponent_class:
        center_text(
            f"Vs {opponent_class} - {len(sub)} Games - {len(sub[sub.won == True])} Wins"
        )
    else:
        center_text(
            f"{class_select} Stats - {len(sub)} Games - {len(sub[sub.won == True])} Wins"
        )
    c1, c2 = st.columns([1, 1])

    # Total WIN %age when going first/second
    chart = (
        alt.Chart(sub)
        .transform_aggregate(count="count()", groupby=["won", "starting_turn"])
        .transform_joinaggregate(total="sum(count)", groupby=["starting_turn"])
        .transform_calculate(frac=alt.datum.count / alt.datum.total)
        .mark_bar()
        .encode(
            x=alt.X("starting_turn:N", title="Starting Turn"),
            y=alt.Y(
                "count:Q",
                stack="normalize",
                axis=alt.Axis(title="Percentage", format="%"),
            ),
            color=alt.Color(
                "won:N",
                title="I Won",
                scale=alt.Scale(domain=[True, False], range=["#1696d2", "#d2d2d2"]),
            ),
            tooltip=[
                alt.Tooltip("count:Q", title="Games"),
                alt.Tooltip("frac:Q", title="Percentage of Games", format=".0%"),
            ],
        )
    )
    c1.altair_chart(chart, use_container_width=True)

    # Average turns when going first/second
    chart = (
        alt.Chart(sub)
        .mark_boxplot()
        .encode(
            alt.X("turns:Q", title="Number of Turns"),
            alt.Y("starting_turn:N", title="Starting Turn"),
            color=alt.Color("starting_turn:N", title="Starting Turn", legend=None),
        )
    )
    c2.altair_chart(chart, use_container_width=True)


def level_plot(df, as_class):
    center_text(f"Win Rate by Level - {as_class}")
    df = df[df.self_class == as_class] if as_class else df
    perc = (
        df.groupby(["self_level", "opponent_class"])
        .won.value_counts(normalize=True)
        .rename("Win Percentage")
    )
    counts = (
        df.groupby(["self_level", "opponent_class"])
        .won.value_counts()
        .rename("Games Won")
    )
    cat = pd.concat([perc, counts], axis=1).reset_index().loc[lambda x: x.won == True]
    line = (
        alt.Chart(cat)
        .mark_line()
        .encode(
            alt.X("self_level:N", title="My Level"),
            alt.Y("Win Percentage", axis=alt.Axis(title="Win Percentage", format="%")),
        )
        .facet(column=alt.Y("opponent_class", title="Opponent"))
    )
    # dot = alt.Chart(cat).mark_circle().encode(
    #     alt.X('self_level:N', title="My Level"),
    #     alt.Y('Win Percentage', title='Win Percentage'),
    #     alt.Color('opponent_class', title='Opponent'),
    #     size='Games Won',
    #     tooltip=['Win Percentage', 'Games Won']
    # )
    st.altair_chart(line, use_container_width=True)


def main():
    # Get Google Sheet ID
    id_container = st.empty()
    form = id_container.form(key="my_form")
    sheet_id = form.text_input(
        label="Enter ID of Hero Realms Spreadsheet", value=SHEET_ID
    )
    sheet_name = form.text_input(label="Enter sheet name", value=SHEET_NAME).replace(
        " ", "%20"
    )
    submit = form.form_submit_button(label="Submit")
    if not submit:
        st.stop()

    # Fetch data and display banner
    id_container.empty()
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    df = get_data(url)
    banner(df)

    # Class Summary Plot
    st.altair_chart(class_summary_plot(df), use_container_width=True)

    # Class Stats
    class_select = st.sidebar.selectbox(
        "Class", sorted(df.self_class.unique()), index=1
    )
    lvl_max = int(df.self_level.max()) + 1
    level_range = st.sidebar.slider("Level Range", 1, lvl_max, (1, lvl_max))
    class_stats(df, class_select, level_range)
    opponent_class_select = st.sidebar.selectbox(
        "Opponent Class", sorted(df.opponent_class.unique()), index=4
    )
    class_stats(df, class_select, level_range, opponent_class_select)

    # Univariates
    center_text("Misc. Univariate Distributions")
    g = (
        df.groupby(["won", "starting_turn", "self_class", "opponent_class"])
        .agg(
            {
                "opponent_level": "mean",
                "opponent_hp": "mean",
                "self_hp": "mean",
                "turns": "mean",
            }
        )
        .reset_index()
    )
    cols = ["opponent_hp", "turns", "opponent_level", "self_hp"]
    names = ["Opponent Health", "Num Turns", "Opponent Level", "My Health"]
    for name, col in zip(names, cols):
        with st.expander(name, expanded=False):
            chart = (
                alt.Chart(df)
                .mark_boxplot()
                .encode(
                    y=alt.Y("self_class:N", title="My Class"),
                    x=alt.X(f"{col}:Q", title=name),
                    color=alt.Color("self_class:N", title="My Class"),
                )
                .properties(width=135)
                .facet(column=alt.Y("opponent_class:N", title="Opponent"), row="won")
            )
            st.altair_chart(chart, use_container_width=True)

    # Raw data
    with st.expander("Raw Data"):
        st.dataframe(df)
        st.markdown(
            """
            - A: Other player's name
            - B: Other player's class
            - C: Other player's level
            - D: Other player's ending HP
            - E: My class
            - F: My level
            - G: My ending HP
            - H: Did I go first?
            - I: Num turns
            - J: Did I win?
            """
        )


if __name__ == "__main__":
    main()
