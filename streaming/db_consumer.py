import json
import os

from confluent_kafka import (
    Consumer,
    KafkaException,
)

from database.connection import (
    get_connection,
)

from database.queries import (
    persist_live_fixture_event,
)


KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:9092",
)

TOPIC = "live_match_updates"

CONSUMER_GROUP = (
    "sports-ai-db-writer-v1"
)


REQUIRED_FIELDS = {
    "event_type",
    "captured_at",
    "fixture_id",
    "status",
    "minute",
    "home_team_id",
    "away_team_id",
    "home_goals",
    "away_goals",
}


def validate_event(event):
    missing_fields = (
        REQUIRED_FIELDS
        - event.keys()
    )

    if missing_fields:
        raise ValueError(
            "Missing fields: "
            f"{sorted(missing_fields)}"
        )

    if (
        event["event_type"]
        != "live_match_update"
    ):
        raise ValueError(
            "Unsupported event type: "
            f"{event['event_type']}"
        )


def build_consumer():
    return Consumer(
        {
            "bootstrap.servers":
                KAFKA_BOOTSTRAP_SERVERS,

            "group.id":
                CONSUMER_GROUP,

            "auto.offset.reset":
                "latest",

            "enable.auto.commit":
                False,
        }
    )


def run_consumer():
    consumer = build_consumer()
    connection = get_connection()

    consumer.subscribe(
        [TOPIC]
    )

    print(
        "=== KAFKA DB CONSUMER ==="
    )

    print(
        "Topic:",
        TOPIC,
    )

    print(
        "Consumer group:",
        CONSUMER_GROUP,
    )

    print(
        "\nWaiting for events..."
    )

    try:
        while True:
            message = consumer.poll(
                timeout=1.0
            )

            if message is None:
                continue

            if message.error():
                raise KafkaException(
                    message.error()
                )

            try:
                event = json.loads(
                    message
                    .value()
                    .decode("utf-8")
                )

                validate_event(
                    event
                )

            except (
                json.JSONDecodeError,
                ValueError,
            ) as error:
                print(
                    "\nInvalid event:"
                )

                print(error)

                consumer.commit(
                    message=message,
                    asynchronous=False,
                )

                continue

            try:
                persist_live_fixture_event(
                    connection,
                    event,
                )

            except Exception as error:
                print(
                    "\nDatabase write failed:"
                )

                print(error)

                raise

            consumer.commit(
                message=message,
                asynchronous=False,
            )

            print(
                "\n=== EVENT STORED ==="
            )

            print(
                "Fixture:",
                event["fixture_id"],
            )

            print(
                "Minute:",
                event["minute"],
            )

            print(
                "Score:",
                event["home_goals"],
                "-",
                event["away_goals"],
            )

            print(
                "Partition:",
                message.partition(),
            )

            print(
                "Offset committed:",
                message.offset(),
            )

    except KeyboardInterrupt:
        print(
            "\nDB consumer stopped."
        )

    finally:
        connection.close()
        consumer.close()


if __name__ == "__main__":
    run_consumer()