import time
from datetime import (
    datetime,
    timezone,
)

from database.connection import (
    get_connection,
)

from streaming.kafka_producer import (
    build_producer,
    send_event,
)

from modeling.live_prediction import (
    predict_live_fixture,
)


PREMIER_LEAGUE_ID = 39


def get_upcoming_fixture():
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    fixture_id,
                    home_team_id,
                    away_team_id,
                    status,
                    minute,
                    home_goals,
                    away_goals
                FROM fixtures
                WHERE league_id = %s
                  AND status = 'Not Started'
                  AND date >= NOW()
                ORDER BY date
                LIMIT 1;
                """,
                (
                    PREMIER_LEAGUE_ID,
                ),
            )

            row = cursor.fetchone()

        if row is None:
            raise RuntimeError(
                "No upcoming Premier League "
                "fixture found."
            )

        return {
            "fixture_id": row[0],
            "home_team_id": row[1],
            "away_team_id": row[2],
            "status": row[3],
            "minute": row[4],
            "home_goals": row[5],
            "away_goals": row[6],
        }

    finally:
        connection.close()


def build_demo_event(
    fixture,
):
    return {
        "event_type":
            "live_match_update",

        "demo":
            True,

        "captured_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "fixture_id":
            fixture["fixture_id"],

        "status":
            "First Half",

        "minute":
            30,

        "home_team_id":
            fixture["home_team_id"],

        "away_team_id":
            fixture["away_team_id"],

        "home_goals":
            1,

        "away_goals":
            0,
    }


def wait_for_database(
    event,
    attempts=20,
):
    for _ in range(attempts):
        connection = get_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM live_fixture_snapshots
                    WHERE fixture_id = %s
                      AND captured_at = %s;
                    """,
                    (
                        event["fixture_id"],
                        event["captured_at"],
                    ),
                )

                snapshot_count = (
                    cursor.fetchone()[0]
                )

                cursor.execute(
                    """
                    SELECT
                        status,
                        minute,
                        home_goals,
                        away_goals
                    FROM fixtures
                    WHERE fixture_id = %s;
                    """,
                    (
                        event["fixture_id"],
                    ),
                )

                fixture_state = (
                    cursor.fetchone()
                )

            if snapshot_count == 2:
                return (
                    snapshot_count,
                    fixture_state,
                )

        finally:
            connection.close()

        time.sleep(0.5)

    return None, None


def cleanup_demo(
    fixture,
    event,
):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM live_fixture_snapshots
                WHERE fixture_id = %s
                  AND captured_at = %s;
                """,
                (
                    event["fixture_id"],
                    event["captured_at"],
                ),
            )

            cursor.execute(
                """
                UPDATE fixtures
                SET
                    status = %s,
                    minute = %s,
                    home_goals = %s,
                    away_goals = %s
                WHERE fixture_id = %s;
                """,
                (
                    fixture["status"],
                    fixture["minute"],
                    fixture["home_goals"],
                    fixture["away_goals"],
                    fixture["fixture_id"],
                ),
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def run_demo():
    fixture = get_upcoming_fixture()

    print(
        "=== DEMO LIVE EVENT ==="
    )

    print(
        "Fixture:",
        fixture["fixture_id"],
    )

    print(
        "Original state:",
        fixture["status"],
        fixture["minute"],
        fixture["home_goals"],
        fixture["away_goals"],
    )

    event = build_demo_event(
        fixture
    )

    producer = build_producer()

    send_event(
        producer,
        event,
    )

    producer.flush()

    print(
        "\nDemo event sent to Kafka."
    )

    snapshot_count, fixture_state = (
        wait_for_database(
            event
        )
    )

    if snapshot_count != 2:
        raise RuntimeError(
            "Demo event was not written "
            "to PostgreSQL."
        )

    print(
        "\n=== DATABASE VERIFIED ==="
    )

    print(
        "Snapshots:",
        snapshot_count,
    )

    print(
        "Fixture state:",
        fixture_state,
    )

    live_prediction = (
        predict_live_fixture(
            event["fixture_id"]
        )
    )

    print(
        "\n=== LIVE PREDICTION ==="
    )

    print(
        live_prediction[
            "home_team"
        ],
        "vs",
        live_prediction[
            "away_team"
        ],
    )

    print(
        "Minute:",
        live_prediction[
            "minute"
        ],
    )

    print(
        "Score:",
        live_prediction[
            "home_goals"
        ],
        "-",
        live_prediction[
            "away_goals"
        ],
    )

    print(
        "\nPre-match:"
    )

    print(
        live_prediction[
            "prematch_probabilities"
        ]
    )

    print(
        "\nIn-play:"
    )

    print(
        live_prediction[
            "live_probabilities"
        ]
    )

    input(
        "\nPress Enter to clean up demo data..."
    )

    cleanup_demo(
        fixture,
        event,
    )

    print(
        "\nDemo data cleaned up."
    )

    print(
        "\nEND-TO-END TEST PASSED"
    )


if __name__ == "__main__":
    run_demo()