import os

import requests
import streamlit as st


API_BASE_URL = os.getenv(
    "SPORTS_AI_API_URL",
    "http://127.0.0.1:8000",
)


st.set_page_config(
    page_title="Sports AI Platform",
    page_icon="⚽",
    layout="wide",
)


st.title("⚽ Sports AI Platform")

st.caption(
    "Premier League pre-match and live win probabilities"
)


def get_json(path, params=None):
    response = requests.get(
        f"{API_BASE_URL}{path}",
        params=params,
        timeout=5,
    )

    response.raise_for_status()

    return response.json()


def probability_percent(value):
    return f"{value * 100:.1f}%"


def render_probabilities(probabilities):
    home_col, draw_col, away_col = st.columns(3)

    home_col.metric(
        "Home",
        probability_percent(
            probabilities["H"]
        ),
    )

    draw_col.metric(
        "Draw",
        probability_percent(
            probabilities["D"]
        ),
    )

    away_col.metric(
        "Away",
        probability_percent(
            probabilities["A"]
        ),
    )


@st.fragment(run_every="5s")
def live_section():
    st.subheader("🔴 Live Matches")

    try:
        data = get_json(
            "/predictions/live"
        )

    except requests.RequestException as error:
        st.error(
            f"Could not reach API: {error}"
        )
        return

    if data["count"] == 0:
        st.info(
            "No Premier League matches are live."
        )
        return

    for prediction in data["predictions"]:
        with st.container(border=True):
            st.markdown(
                f"### "
                f"{prediction['home_team']} "
                f"{prediction['home_goals']} - "
                f"{prediction['away_goals']} "
                f"{prediction['away_team']}"
            )

            st.caption(
                f"{prediction['status']} "
                f"• {prediction['minute']}'"
            )

            st.markdown(
                "**Pre-match probabilities**"
            )

            render_probabilities(
                prediction[
                    "prematch_probabilities"
                ]
            )

            st.markdown(
                "**Live probabilities**"
            )

            render_probabilities(
                prediction[
                    "live_probabilities"
                ]
            )


def upcoming_section():
    st.subheader("📅 Upcoming Matches")

    try:
        data = get_json(
            "/predictions/upcoming",
            params={"limit": 10},
        )

    except requests.RequestException as error:
        st.error(
            f"Could not reach API: {error}"
        )
        return

    if data["count"] == 0:
        st.info(
            "No upcoming predictions available."
        )
        return

    for prediction in data["predictions"]:
        with st.container(border=True):
            st.markdown(
                f"### "
                f"{prediction['home_team']} "
                f"vs "
                f"{prediction['away_team']}"
            )

            render_probabilities(
                {
                    "H": prediction["prob_home"],
                    "D": prediction["prob_draw"],
                    "A": prediction["prob_away"],
                }
            )


live_section()

st.divider()

upcoming_section()