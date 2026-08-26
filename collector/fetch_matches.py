import os
import time

import requests
from dotenv import load_dotenv

from database.connection import get_connection
from database.queries import insert_teams, insert_fixtures, insert_fixture_statistics, get_existing_statistics_fixture_ids

load_dotenv()

api_key = os.getenv("API_FOOTBALL_KEY")

url = "https://v3.football.api-sports.io/fixtures"

headers = {
    "x-apisports-key": api_key
}

def fetch_fixtures(league_id, season):
    params = {
        "league": league_id,
        "season": season
    }

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=15
    )

    if response.status_code != 200:
        raise Exception(
            f"API request failed for season {season}: "
            f"status {response.status_code}"
        )

    data = response.json()

    if data["errors"]:
        raise Exception(
            f"API error for season {season}: {data['errors']}"
        )

    return data["response"]


def parse_fixture(match):
    return {
        "fixture_id": match["fixture"]["id"],
        "date": match["fixture"]["date"],
        "status": match["fixture"]["status"]["long"],
        "minute": match["fixture"]["status"]["elapsed"],
        "league_id": match["league"]["id"],
        "league_name": match["league"]["name"],
        "season": match["league"]["season"],
        "home_team_id": match["teams"]["home"]["id"],
        "home_team_name": match["teams"]["home"]["name"],
        "away_team_id": match["teams"]["away"]["id"],
        "away_team_name": match["teams"]["away"]["name"],
        "home_goals": match["goals"]["home"],
        "away_goals": match["goals"]["away"]
    }

seasons = range(2020, 2027)

parsed_matches = []

for season in seasons:
    raw_matches = fetch_fixtures(39, season)

    season_matches = []

    for match in raw_matches:
        parsed_match = parse_fixture(match)
        season_matches.append(parsed_match)

    parsed_matches.extend(season_matches)

    print(f"Season {season}: {len(season_matches)} fixtures")

print(f"Total fixtures: {len(parsed_matches)}")


teams = {}

for match in parsed_matches:
    teams[match["home_team_id"]] = match["home_team_name"]
    teams[match["away_team_id"]] = match["away_team_name"]

print("Number of teams:", len(teams))
print(teams)

connection = get_connection()

insert_teams(connection, teams)
insert_fixtures(connection, parsed_matches)

connection.close()

print("Teams and fixtures saved to database")

statistics_url = "https://v3.football.api-sports.io/fixtures/statistics"


def fetch_fixture_statistics(fixture_id):
    params = {
        "fixture": fixture_id
    }

    response = requests.get(
        statistics_url,
        headers=headers,
        params=params,
        timeout=10
    )

    if response.status_code != 200:
        raise Exception(
            f"Statistics request failed for fixture {fixture_id}: "
            f"status {response.status_code}"
        )

    data = response.json()

    if data["errors"]:
        raise Exception(
            f"Statistics API error for fixture {fixture_id}: "
            f"{data['errors']}"
        )

    return data["response"]

def parse_percentage(value):
    if value is None:
        return None
    return int(value.replace("%", ""))


def parse_float(value):
    if value is None:
        return None
    return float(value)

def parse_int(value):
    if value is None:
        return None
    return int(value)

def parse_team_statistics(team_data):
    stats = {}

    for stat in team_data["statistics"]:
        stats[stat["type"]] = stat["value"]

    return {
        "team_id": team_data["team"]["id"],
        "team_name": team_data["team"]["name"],
        "shots_on_goal": parse_int(stats.get("Shots on Goal")),
        "shots_off_goal": parse_int(stats.get("Shots off Goal")),
        "total_shots": parse_int(stats.get("Total Shots")),
        "blocked_shots": parse_int(stats.get("Blocked Shots")),
        "shots_inside_box": parse_int(stats.get("Shots insidebox")),
        "shots_outside_box": parse_int(stats.get("Shots outsidebox")),
        "corners": parse_int(stats.get("Corner Kicks")),
        "possession": parse_percentage(stats.get("Ball Possession")),
        "yellow_cards": parse_int(stats.get("Yellow Cards")),
        "red_cards": parse_int(stats.get("Red Cards")),
        "xg": parse_float(stats.get("expected_goals"))
    }


finished_matches = [
    match
    for match in parsed_matches
    if match["status"] == "Match Finished"
]

statistics_connection = get_connection()

existing_statistics_fixture_ids = (
    get_existing_statistics_fixture_ids(statistics_connection)
)

pending_matches = [
    match
    for match in finished_matches
    if match["fixture_id"] not in existing_statistics_fixture_ids
]

print("Finished matches:", len(finished_matches))
print(
    "Already have statistics:",
    len(existing_statistics_fixture_ids)
)
print("Statistics still needed:", len(pending_matches))

successful_matches = 0
missing_statistics = 0
failed_matches = 0

total_pending = len(pending_matches)

for index, match in enumerate(pending_matches, start=1):
    fixture_id = match["fixture_id"]

    try:
        time.sleep(0.35)

        raw_statistics = fetch_fixture_statistics(fixture_id)

        if len(raw_statistics) != 2:
            print(
                f"[{index}/{total_pending}] "
                f"{fixture_id} | "
                f"{match['home_team_name']} vs "
                f"{match['away_team_name']} "
                f"| missing/partial statistics"
            )

            missing_statistics += 1
            continue

        parsed_statistics = [
            parse_team_statistics(team_data)
            for team_data in raw_statistics
        ]

        insert_fixture_statistics(
            statistics_connection,
            fixture_id,
            parsed_statistics
        )

        successful_matches += 1

        print(
            f"[{index}/{total_pending}] "
            f"{fixture_id} | "
            f"{match['home_team_name']} vs "
            f"{match['away_team_name']} "
            f"| saved"
        )


    except Exception as error:
        statistics_connection.rollback()

        failed_matches += 1

        print(
            f"[{index}/{total_pending}] "
            f"ERROR | fixture {fixture_id}: {error}"
        )

statistics_connection.close()

print()
print("Historical statistics backfill finished")
print("Successful:", successful_matches)
print("Missing/partial:", missing_statistics)
print("Failed:", failed_matches)