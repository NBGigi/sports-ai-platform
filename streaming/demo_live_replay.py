import time
from datetime import (
    datetime,
    timezone,
)

from database.connection import (
    get_connection,
)

from modeling.live_prediction import (
    predict_live_fixture,
)

from streaming.demo_live_event import (
    get_upcoming_fixture,
    wait_for_database,
)

from streaming.kafka_producer import (
    build_producer,
    send_event,
)


DELAY_SECONDS = 10


REPLAY_STEPS = [
    {
        "status": "First Half",
        "minute": 1,
        "home_goals": 0,
        "away_goals": 0,
    },
    {
        "status": "First Half",
        "minute": 20,
        "home_goals": 0,
        "away_goals": 0,
    },
    {
        "status": "First Half",
        "minute": 30,
        "home_goals": 1,
        "away_goals": 0,
    },
    {
        "status": "Second Half",
        "minute": 55,
        "home_goals": 1,
        "away_goals": 0,
    },
    {
        "status": "Second Half",
        "minute": 70,
        "home_goals": 1,
        "away_goals": 1,
    },
    {
        "status": "Second Half",
        "minute": 82,
        "home_goals": 2,
        "away_goals": 1,
    },
]


def build_replay_event(
    fixture,
    step,
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
            step["status"],

        "minute":
            step["minute"],

        "home_team_id":
            fixture["home_team_id"],

        "away_team_id":
            fixture["away_team_id"],

        "home_goals":
            step["home_goals"],

        "away_goals":
            step["away_goals"],
    }


def cleanup_replay(
    fixture,
    events,
):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            for event in events:
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


def run_replay():
    fixture = get_upcoming_fixture()

    producer = build_producer()

    sent_events = []

    print(
        "=== LIVE MATCH REPLAY ==="
    )

    print(
        "Fixture:",
        fixture["fixture_id"],
    )

    try:
        for index, step in enumerate(
            REPLAY_STEPS
        ):
            event = build_replay_event(
                fixture,
                step,
            )

            send_event(
                producer,
                event,
            )

            producer.flush()

            sent_events.append(
                event
            )

            snapshot_count, _ = (
                wait_for_database(
                    event
                )
            )

            if snapshot_count != 2:
                raise RuntimeError(
                    "Replay event was not "
                    "written to PostgreSQL."
                )

            prediction = (
                predict_live_fixture(
                    fixture["fixture_id"]
                )
            )

            live = prediction[
                "live_probabilities"
            ]

            print(
                f"\n{step['minute']}' "
                f"{step['home_goals']}-"
                f"{step['away_goals']}"
            )

            print(
                "Home:",
                f"{live['H'] * 100:.1f}%",
            )

            print(
                "Draw:",
                f"{live['D'] * 100:.1f}%",
            )

            print(
                "Away:",
                f"{live['A'] * 100:.1f}%",
            )

            if index < (
                len(REPLAY_STEPS) - 1
            ):
                time.sleep(
                    DELAY_SECONDS
                )

        input(
            "\nReplay finished. "
            "Press Enter to clean up..."
        )

    finally:
        cleanup_replay(
            fixture,
            sent_events,
        )

        print(
            "\nReplay data cleaned up."
        )


if __name__ == "__main__":
    run_replay()