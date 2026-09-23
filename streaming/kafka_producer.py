import json
import os

from confluent_kafka import Producer


KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:9092",
)

TOPIC = "live_match_updates"


def delivery_report(
    error,
    message,
):
    if error is not None:
        print(
            "Delivery failed:",
            error,
        )
        return

    print(
        "Delivered event:"
    )

    print(
        "Topic:",
        message.topic()
    )

    print(
        "Partition:",
        message.partition()
    )

    print(
        "Offset:",
        message.offset()
    )


def build_producer():
    return Producer(
        {
            "bootstrap.servers":
                KAFKA_BOOTSTRAP_SERVERS,
        }
    )


def send_event(
    producer,
    event,
):
    fixture_id = event[
        "fixture_id"
    ]

    message_value = json.dumps(
        event
    )

    producer.produce(
        topic=TOPIC,

        key=str(
            fixture_id
        ),

        value=message_value,

        callback=delivery_report,
    )

    producer.poll(0)


if __name__ == "__main__":
    producer = build_producer()

    event = {
        "fixture_id": 1557424,
        "minute": 25,
        "home_goals": 1,
        "away_goals": 0,
        "home_shots_on_goal": 4,
        "away_shots_on_goal": 2,
    }

    print(
        "Sending event:"
    )

    print(
        json.dumps(
            event,
            indent=4,
        )
    )

    send_event(
        producer,
        event,
    )

    producer.flush()