import os
from datetime import (
    datetime,
    timezone,
)

import requests
from dotenv import load_dotenv

from streaming.kafka_producer import (
    build_producer,
    send_event,
)


load_dotenv()


API_KEY = os.getenv(
    "API_FOOTBALL_KEY"
)

API_URL = (
    "https://v3.football.api-sports.io/fixtures"
)

PREMIER_LEAGUE_ID = 39


def fetch_live_premier_league_matches():
    if not API_KEY:
        raise ValueError(
            "API_FOOTBALL_KEY is missing."
        )

    headers = {
        "x-apisports-key":
            API_KEY,
    }

    params = {
        "live": "all",
    }

    response = requests.get(
        API_URL,
        headers=headers,
        params=params,
        timeout=15,
    )

    response.raise_for_status()

    data = response.json()

    if data.get("errors"):
        raise RuntimeError(
            f"API-Football error: "
            f"{data['errors']}"
        )

    live_matches = data[
        "response"
    ]

    premier_league_matches = [
        match
        for match in live_matches
        if match[
            "league"
        ][
            "id"
        ] == PREMIER_LEAGUE_ID
    ]

    return premier_league_matches


def build_live_event(
    match,
):
    fixture = match[
        "fixture"
    ]

    league = match[
        "league"
    ]

    teams = match[
        "teams"
    ]

    goals = match[
        "goals"
    ]

    return {
        "event_type":
            "live_match_update",

        "captured_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "fixture_id":
            fixture["id"],

        "league_id":
            league["id"],

        "season":
            league["season"],

        "round":
            league["round"],

        "status":
            fixture[
                "status"
            ]["long"],

        "minute":
            fixture[
                "status"
            ]["elapsed"],

        "home_team_id":
            teams[
                "home"
            ]["id"],

        "home_team_name":
            teams[
                "home"
            ]["name"],

        "away_team_id":
            teams[
                "away"
            ]["id"],

        "away_team_name":
            teams[
                "away"
            ]["name"],

        "home_goals":
            goals["home"],

        "away_goals":
            goals["away"],
    }


def publish_live_matches():
    print(
        "=== LIVE KAFKA PRODUCER ==="
    )

    live_matches = (
        fetch_live_premier_league_matches()
    )

    print(
        "Live Premier League matches:",
        len(live_matches),
    )

    if not live_matches:
        print(
            "No live Premier League "
            "matches found."
        )

        return 0

    producer = build_producer()

    sent = 0

    for match in live_matches:
        event = build_live_event(
            match
        )

        print(
            "\nPublishing:"
        )

        print(
            event[
                "home_team_name"
            ],
            "vs",
            event[
                "away_team_name"
            ],
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

        send_event(
            producer,
            event,
        )

        sent += 1

    producer.flush()

    print(
        "\nEvents published:",
        sent,
    )

    return sent


if __name__ == "__main__":
    publish_live_matches()