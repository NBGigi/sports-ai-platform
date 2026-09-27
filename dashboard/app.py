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


def get_json(
    path,
    params=None,
):
    response = requests.get(
        f"{API_BASE_URL}{path}",
        params=params,
        timeout=(10, 90),
    )

    response.raise_for_status()

    return response.json()


def probability_percent(value):
    return f"{float(value) * 100:.1f}%"


def render_probability_metrics(
    probabilities,
    labels,
    baseline=None,
):
    keys = (
        "H",
        "D",
        "A",
    )

    columns = st.columns(3)

    for column, key, label in zip(
        columns,
        keys,
        labels,
    ):
        value = float(
            probabilities[key]
        )

        column.metric(
            label,
            probability_percent(value),
        )

        column.progress(value)

        if baseline is not None:
            baseline_value = float(
                baseline[key]
            )

            change_pp = (
                value
                - baseline_value
            ) * 100

            column.caption(
                f"vs pre-match: "
                f"{change_pp:+.1f} pp"
            )


st.title(
    "⚽ Sports AI Platform"
)

st.caption(
    "Premier League probability engine "
    "• Model v1 "
    "• Live updates every 5 seconds"
)

st.info(
    "Pre-match probabilities are generated "
    "independently from football data. "
    "Live probabilities update from the "
    "current score and match minute."
)


@st.fragment(
    run_every="5s"
)
def live_section():
    st.subheader(
        "🔴 Live Matches"
    )

    st.caption(
        "This section automatically "
        "refreshes every 5 seconds."
    )

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
            "No Premier League matches "
            "are live."
        )
        return

    for prediction in data[
        "predictions"
    ]:
        home_team = prediction[
            "home_team"
        ]

        away_team = prediction[
            "away_team"
        ]

        prematch = prediction[
            "prematch_probabilities"
        ]

        live = prediction[
            "live_probabilities"
        ]

        with st.container(
            border=True
        ):
            st.markdown(
                f"## "
                f"{home_team} "
                f"{prediction['home_goals']} "
                f"– "
                f"{prediction['away_goals']} "
                f"{away_team}"
            )

            st.markdown(
                f"**{prediction['minute']}'**"
                f" · "
                f"{prediction['status']}"
            )

            st.markdown(
                "### Live probabilities"
            )

            render_probability_metrics(
                live,
                (
                    home_team,
                    "Draw",
                    away_team,
                ),
                baseline=prematch,
            )

            with st.expander(
                "View pre-match baseline"
            ):
                render_probability_metrics(
                    prematch,
                    (
                        home_team,
                        "Draw",
                        away_team,
                    ),
                )

@st.fragment(run_every="30s")
def upcoming_section():
    st.subheader(
        "📅 Upcoming Matches"
    )

    st.caption(
        "Frozen pre-match predictions "
        "from model v1."
    )

    try:
        data = get_json(
            "/predictions/upcoming",
            params={
                "limit": 10
            },
        )

    except requests.RequestException as error:
        st.error(
            f"Could not reach API: {error}"
        )
        return

    if data["count"] == 0:
        st.info(
            "No upcoming predictions "
            "available."
        )
        return

    rows = []

    for prediction in data[
        "predictions"
    ]:
        rows.append(
            {
                "Fixture":
                    (
                        f"{prediction['home_team']} "
                        f"vs "
                        f"{prediction['away_team']}"
                    ),

                "Home":
                    probability_percent(
                        prediction[
                            "prob_home"
                        ]
                    ),

                "Draw":
                    probability_percent(
                        prediction[
                            "prob_draw"
                        ]
                    ),

                "Away":
                    probability_percent(
                        prediction[
                            "prob_away"
                        ]
                    ),

                "Round":
                    prediction["round"],
            }
        )

    st.dataframe(
        rows,
        hide_index=True,
        use_container_width=True,
    )


live_section()

st.divider()

upcoming_section()


with st.expander(
    "ℹ️ How the model works"
):
    st.markdown(
        """
**Pre-match model**

Model v1 uses a calibrated multiclass
Logistic Regression model based on the
pre-match Elo difference between the teams.

**In-play model**

During a live match, the frozen pre-match
probabilities are converted into expected
goal rates. A Poisson model then recalculates
the probabilities using the current minute
and score.

**Important**

Bookmaker odds are not used as model
features. They are reserved for independent
benchmarking.
"""
    )