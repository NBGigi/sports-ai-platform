import json
import os

from confluent_kafka import (
    Consumer,
    KafkaException,
)


KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:9092",
)

TOPIC = "live_match_updates"

CONSUMER_GROUP = (
    "sports-ai-live-dev"
)


def build_consumer():
    return Consumer(
        {
            "bootstrap.servers":
                KAFKA_BOOTSTRAP_SERVERS,

            "group.id":
                CONSUMER_GROUP,

            "auto.offset.reset":
                "earliest",

            "enable.auto.commit":
                True,
        }
    )


if __name__ == "__main__":
    consumer = build_consumer()

    consumer.subscribe(
        [
            TOPIC
        ]
    )

    print(
        "=== KAFKA PYTHON CONSUMER ==="
    )

    print(
        "Topic:",
        TOPIC
    )

    print(
        "Consumer group:",
        CONSUMER_GROUP
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

            event = json.loads(
                message
                .value()
                .decode("utf-8")
            )

            print(
                "\n=== EVENT RECEIVED ==="
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

            print(
                "Key:",
                (
                    message.key()
                    .decode("utf-8")
                    if message.key()
                    else None
                )
            )

            print(
                "Payload:"
            )

            print(
                json.dumps(
                    event,
                    indent=4,
                )
            )

    except KeyboardInterrupt:
        print(
            "\nConsumer stopped."
        )

    finally:
        consumer.close()