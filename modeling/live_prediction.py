from database.connection import (
    get_connection,
)

from database.queries import (
    get_current_fixture_state,
    get_fixture_prediction,
)

from modeling.in_play_probability import (
    calculate_in_play_probabilities,
)


MODEL_VERSION = "v1"


def predict_live_fixture(
    fixture_id,
    model_version=MODEL_VERSION,
):
    connection = get_connection()

    try:
        fixture = (
            get_current_fixture_state(
                connection,
                fixture_id,
            )
        )

        if fixture is None:
            raise ValueError(
                "Fixture not found: "
                f"{fixture_id}"
            )

        prediction = (
            get_fixture_prediction(
                connection,
                fixture_id,
                model_version,
            )
        )

        if prediction is None:
            raise ValueError(
                "Pre-match prediction "
                "not found for fixture "
                f"{fixture_id}"
            )

    finally:
        connection.close()

    if fixture["minute"] is None:
        raise ValueError(
            "Fixture does not have "
            "a live minute yet."
        )

    if (
        fixture["home_goals"] is None
        or fixture["away_goals"] is None
    ):
        raise ValueError(
            "Fixture does not have "
            "a live score yet."
        )

    prematch_probabilities = {
        "H":
            prediction["prob_home"],

        "D":
            prediction["prob_draw"],

        "A":
            prediction["prob_away"],
    }

    in_play = (
        calculate_in_play_probabilities(
            prematch_probabilities,
            fixture["minute"],
            fixture["home_goals"],
            fixture["away_goals"],
        )
    )

    return {
        "fixture_id":
            fixture_id,

        "home_team":
            fixture["home_team_name"],

        "away_team":
            fixture["away_team_name"],

        "status":
            fixture["status"],

        "minute":
            fixture["minute"],

        "home_goals":
            fixture["home_goals"],

        "away_goals":
            fixture["away_goals"],

        "model_version":
            model_version,

        "prematch_probabilities":
            prematch_probabilities,

        "live_probabilities":
            in_play["probabilities"],

        "lambda_home":
            in_play["lambda_home"],

        "lambda_away":
            in_play["lambda_away"],

        "remaining_lambda_home":
            in_play[
                "remaining_lambda_home"
            ],

        "remaining_lambda_away":
            in_play[
                "remaining_lambda_away"
            ],
    }