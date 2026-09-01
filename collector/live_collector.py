import os
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

from database.connection import get_connection
from database.queries import insert_live_snapshot


load_dotenv()

API_KEY = os.getenv("API_FOOTBALL_KEY")
BASE_URL = "https://v3.football.api-sports.io"

PREMIER_LEAGUE_ID = 39


def parse_int(value):

    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_float(value):

    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_percentage(value):

    if value is None:
        return None

    if isinstance(value, str):
        value = value.replace("%", "")

    return parse_float(value)


def get_live_fixtures():

    response = requests.get(
        f"{BASE_URL}/fixtures",
        headers={
            "x-apisports-key": API_KEY
        },
        params={
            "live": "all"
        },
        timeout=30
    )

    response.raise_for_status()

    return response.json()


def get_fixture_statistics(fixture_id):

    response = requests.get(
        f"{BASE_URL}/fixtures/statistics",
        headers={
            "x-apisports-key": API_KEY
        },
        params={
            "fixture": fixture_id
        },
        timeout=30
    )

    response.raise_for_status()

    return response.json()


def get_stat_value(statistics, stat_type):

    for stat in statistics:

        if stat["type"] == stat_type:
            return stat["value"]

    return None


def build_snapshot(
    fixture,
    team_data,
    captured_at
):

    statistics = team_data["statistics"]

    return {
        "fixture_id":
            fixture["fixture"]["id"],

        "team_id":
            team_data["team"]["id"],

        "captured_at":
            captured_at,

        "minute":
            fixture["fixture"]["status"]["elapsed"],

        "home_goals":
            fixture["goals"]["home"],

        "away_goals":
            fixture["goals"]["away"],

        "shots_on_goal":
            parse_int(
                get_stat_value(
                    statistics,
                    "Shots on Goal"
                )
            ),

        "shots_off_goal":
            parse_int(
                get_stat_value(
                    statistics,
                    "Shots off Goal"
                )
            ),

        "total_shots":
            parse_int(
                get_stat_value(
                    statistics,
                    "Total Shots"
                )
            ),

        "blocked_shots":
            parse_int(
                get_stat_value(
                    statistics,
                    "Blocked Shots"
                )
            ),

        "shots_inside_box":
            parse_int(
                get_stat_value(
                    statistics,
                    "Shots insidebox"
                )
            ),

        "shots_outside_box":
            parse_int(
                get_stat_value(
                    statistics,
                    "Shots outsidebox"
                )
            ),

        "corners":
            parse_int(
                get_stat_value(
                    statistics,
                    "Corner Kicks"
                )
            ),

        "possession":
            parse_percentage(
                get_stat_value(
                    statistics,
                    "Ball Possession"
                )
            ),

        "yellow_cards":
            (
                parse_int(
                    get_stat_value(
                        statistics,
                        "Yellow Cards"
                    )
                )
                or 0
            ),

        "red_cards":
            (
                parse_int(
                    get_stat_value(
                        statistics,
                        "Red Cards"
                    )
                )
                or 0
            ),

        "xg":
            parse_float(
                get_stat_value(
                    statistics,
                    "expected_goals"
                )
            ),
    }


def collect_live_snapshots():

    live_data = get_live_fixtures()

    premier_league_matches = [
        match
        for match in live_data["response"]
        if match["league"]["id"] == PREMIER_LEAGUE_ID
    ]

    if not premier_league_matches:
        print("No live Premier League matches found.")
        return

    connection = get_connection()

    total_saved_rows = 0
    successful_matches = 0
    failed_matches = 0

    try:

        for match in premier_league_matches:

            fixture_id = match["fixture"]["id"]

            home_name = match["teams"]["home"]["name"]
            away_name = match["teams"]["away"]["name"]

            minute = (
                match["fixture"]
                ["status"]
                ["elapsed"]
            )

            print(
                f"\n{fixture_id} | "
                f"{home_name} vs {away_name} "
                f"| minute {minute}"
            )

            try:

                statistics_data = get_fixture_statistics(
                    fixture_id
                )

                if "response" not in statistics_data:
                    print(
                        "Invalid statistics response."
                    )

                    failed_matches += 1
                    continue

                if not statistics_data["response"]:
                    print(
                        "No statistics available."
                    )

                    failed_matches += 1
                    continue

                captured_at = datetime.now(
                    timezone.utc
                )

                saved_rows = 0

                for team_data in statistics_data["response"]:

                    snapshot = build_snapshot(
                        match,
                        team_data,
                        captured_at
                    )

                    insert_live_snapshot(
                        connection,
                        snapshot
                    )

                    saved_rows += 1
                    total_saved_rows += 1

                successful_matches += 1

                print(
                    f"Saved {saved_rows} "
                    "snapshot rows."
                )

            except Exception as error:

                connection.rollback()

                failed_matches += 1

                print(
                    f"Failed fixture "
                    f"{fixture_id}: {error}"
                )

        print("\n==============================")
        print("LIVE COLLECTION SUMMARY")
        print("==============================")

        print(
            "Live PL matches:",
            len(premier_league_matches)
        )

        print(
            "Successful matches:",
            successful_matches
        )

        print(
            "Failed matches:",
            failed_matches
        )

        print(
            "Snapshot rows saved:",
            total_saved_rows
        )

    finally:
        connection.close()

if __name__ == "__main__":
    collect_live_snapshots()