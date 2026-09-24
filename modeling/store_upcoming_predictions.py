from database.connection import (
    get_connection,
)

from database.queries import (
    insert_fixture_prediction,
)

from modeling.final_elo_model import (
    MODEL_PATH,
    load_model,
)

from modeling.predict_upcoming_fixtures import (
    load_upcoming_fixtures,
    build_current_elo_ratings,
    predict_fixture,
)


MODEL_VERSION = "v1"


def store_upcoming_predictions():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "Model artifact not found. "
            "Run final_elo_model first."
        )

    model = load_model()

    fixtures = load_upcoming_fixtures(
        limit=10
    )

    if fixtures.empty:
        print(
            "No upcoming fixtures found."
        )
        return

    ratings = build_current_elo_ratings()

    connection = get_connection()

    inserted_count = 0
    existing_count = 0

    try:
        print(
            "=== STORE PRE-MATCH PREDICTIONS ==="
        )

        for fixture in fixtures.itertuples(
            index=False
        ):
            prediction = predict_fixture(
                model,
                fixture,
                ratings,
            )

            database_row = {
                "fixture_id":
                    prediction["fixture_id"],

                "model_version":
                    MODEL_VERSION,

                "home_elo":
                    prediction["home_elo"],

                "away_elo":
                    prediction["away_elo"],

                "elo_diff":
                    prediction["elo_diff"],

                "prob_home":
                    prediction["prob_home"],

                "prob_draw":
                    prediction["prob_draw"],

                "prob_away":
                    prediction["prob_away"],
            }

            inserted = insert_fixture_prediction(
                connection,
                database_row,
            )

            if inserted:
                inserted_count += 1
                status = "STORED"

            else:
                existing_count += 1
                status = "ALREADY EXISTS"

            print(
                prediction["home_team"],
                "vs",
                prediction["away_team"],
                "|",
                status,
            )

        print(
            "\nInserted:",
            inserted_count,
        )

        print(
            "Already existed:",
            existing_count,
        )

    finally:
        connection.close()


if __name__ == "__main__":
    store_upcoming_predictions()