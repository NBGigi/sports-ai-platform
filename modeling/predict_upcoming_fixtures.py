import pandas as pd

from database.connection import (
    get_connection,
)

from features.elo import (
    calculate_elo_history,
)

from modeling.final_elo_model import (
    MODEL_PATH,
    load_model,
    predict_from_elo_diff,
)


PREMIER_LEAGUE_ID = 39
CURRENT_SEASON = 2026


def load_upcoming_fixtures(
    limit=10,
):
    connection = get_connection()

    query = """
        SELECT
            f.fixture_id,
            f.date,
            f.round,

            f.home_team_id,
            home_team.team_name
                AS home_team_name,

            f.away_team_id,
            away_team.team_name
                AS away_team_name,

            f.status

        FROM fixtures f

        JOIN teams home_team
            ON home_team.team_id
            = f.home_team_id

        JOIN teams away_team
            ON away_team.team_id
            = f.away_team_id

        WHERE f.league_id = %s
          AND f.season = %s
          AND f.status = 'Not Started'
          AND f.date >= NOW()

        ORDER BY
            f.date,
            f.fixture_id

        LIMIT %s;
    """

    with connection.cursor() as cursor:
        cursor.execute(
            query,
            (
                PREMIER_LEAGUE_ID,
                CURRENT_SEASON,
                limit,
            ),
        )

        rows = cursor.fetchall()

        columns = [
            description.name
            for description
            in cursor.description
        ]

    connection.close()

    return pd.DataFrame(
        rows,
        columns=columns,
    )


def build_current_elo_ratings():
    _, ratings = (
        calculate_elo_history()
    )

    return ratings


def predict_fixture(
    model,
    fixture,
    ratings,
):
    home_team_id = (
        fixture.home_team_id
    )

    away_team_id = (
        fixture.away_team_id
    )

    if home_team_id not in ratings:
        raise ValueError(
            "Missing current Elo rating for "
            f"{fixture.home_team_name} "
            f"(team_id={home_team_id})"
        )

    if away_team_id not in ratings:
        raise ValueError(
            "Missing current Elo rating for "
            f"{fixture.away_team_name} "
            f"(team_id={away_team_id})"
        )

    home_elo = ratings[
        home_team_id
    ]

    away_elo = ratings[
        away_team_id
    ]

    elo_diff = (
        home_elo
        -
        away_elo
    )

    probabilities = (
        predict_from_elo_diff(
            model,
            elo_diff,
        )
    )

    return {
        "fixture_id":
            fixture.fixture_id,

        "date":
            fixture.date,

        "round":
            fixture.round,

        "home_team":
            fixture.home_team_name,

        "away_team":
            fixture.away_team_name,

        "home_elo":
            home_elo,

        "away_elo":
            away_elo,

        "elo_diff":
            elo_diff,

        "prob_away":
            probabilities["A"],

        "prob_draw":
            probabilities["D"],

        "prob_home":
            probabilities["H"],
    }


if __name__ == "__main__":

    print(
        "=== UPCOMING FIXTURE "
        "PREDICTION PIPELINE ==="
    )

    print(
        "Model artifact:"
    )

    print(
        MODEL_PATH
    )

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "Final model artifact does not exist. "
            "Run modeling/final_elo_model.py first."
        )

    model = load_model()

    print(
        "\nModel classes:",
        model.classes_
    )

    fixtures = (
        load_upcoming_fixtures(
            limit=10,
        )
    )

    print(
        "\nUpcoming fixtures found:",
        len(fixtures)
    )

    if fixtures.empty:
        print(
            "No upcoming Premier League "
            "fixtures found."
        )

        raise SystemExit

    ratings = (
        build_current_elo_ratings()
    )

    print(
        "Current Elo ratings available:",
        len(ratings)
    )

    prediction_rows = []

    for fixture in fixtures.itertuples(
        index=False
    ):
        prediction = (
            predict_fixture(
                model,
                fixture,
                ratings,
            )
        )

        prediction_rows.append(
            prediction
        )

    predictions = pd.DataFrame(
        prediction_rows
    )

    predictions[
        "probability_sum"
    ] = (
        predictions[
            [
                "prob_away",
                "prob_draw",
                "prob_home",
            ]
        ]
        .sum(axis=1)
    )

    print(
        "\n=== UPCOMING PREDICTIONS ==="
    )

    display = predictions.copy()

    for column in [
        "home_elo",
        "away_elo",
        "elo_diff",
    ]:
        display[column] = (
            display[column]
            .round(1)
        )

    for column in [
        "prob_away",
        "prob_draw",
        "prob_home",
        "probability_sum",
    ]:
        display[column] = (
            display[column]
            .round(4)
        )

    print(
        display.to_string(
            index=False
        )
    )

    print(
        "\n=== PIPELINE AUDIT ==="
    )

    max_probability_error = (
        (
            predictions[
                "probability_sum"
            ]
            - 1.0
        )
        .abs()
        .max()
    )

    print(
        "Maximum probability-sum error:",
        max_probability_error
    )

    print(
        "All probabilities valid:",
        (
            (
                predictions[
                    [
                        "prob_away",
                        "prob_draw",
                        "prob_home",
                    ]
                ]
                >= 0
            )
            &
            (
                predictions[
                    [
                        "prob_away",
                        "prob_draw",
                        "prob_home",
                    ]
                ]
                <= 1
            )
        )
        .all()
        .all()
    )