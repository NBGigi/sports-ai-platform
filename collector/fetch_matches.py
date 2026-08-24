import os

import requests
from dotenv import load_dotenv


load_dotenv()

api_key = os.getenv("API_FOOTBALL_KEY")

url = "https://v3.football.api-sports.io/fixtures"

headers = {
    "x-apisports-key": api_key
}

params = {
    "league": 39,
    "season": 2024
}

response = requests.get(
    url,
    headers=headers,
    params=params
)


data = response.json()


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

parsed_matches = []

for match in data["response"]:
    parsed_match = parse_fixture(match)
    parsed_matches.append(parsed_match)

statistics_url = "https://v3.football.api-sports.io/fixtures/statistics"

target_fixture_id = 1208021

statistics_params = {
    "fixture": target_fixture_id
}

statistics_response = requests.get(
    statistics_url,
    headers=headers,
    params=statistics_params
)

statistics_data = statistics_response.json()

def parse_percentage(value):
    if value is None:
        return 0
    return int(value.replace("%", ""))


def parse_float(value):
    if value is None:
        return None
    return float(value)

def parse_team_statistics(team_data):
    stats = {}

    for stat in team_data["statistics"]:
        stats[stat["type"]] = stat["value"]

    return {
        "team_id": team_data["team"]["id"],
        "team_name": team_data["team"]["name"],
        "shots_on_goal": stats.get("Shots on Goal", 0) or 0,
        "shots_off_goal": stats.get("Shots off Goal", 0) or 0,
        "total_shots": stats.get("Total Shots", 0) or 0,
        "blocked_shots": stats.get("Blocked Shots", 0) or 0,
        "shots_inside_box": stats.get("Shots insidebox", 0) or 0,
        "shots_outside_box": stats.get("Shots outsidebox", 0) or 0,
        "corners": stats.get("Corner Kicks", 0) or 0,
        "possession": parse_percentage(stats.get("Ball Possession")),
        "yellow_cards": stats.get("Yellow Cards") or 0,
        "red_cards": stats.get("Red Cards") or 0,
        "xg": parse_float(stats.get("expected_goals"))
    }



target_match = next(
    match
    for match in parsed_matches
    if match["fixture_id"] == target_fixture_id
)
parsed_statistics = [
    parse_team_statistics(team_data)
    for team_data in statistics_data["response"]
]

stats_by_team_id = {
    team_stats["team_id"]: team_stats
    for team_stats in parsed_statistics
}

home_stats = stats_by_team_id[target_match["home_team_id"]]
away_stats = stats_by_team_id[target_match["away_team_id"]]



match_snapshot = {
    "fixture_id": target_match["fixture_id"],
    "date": target_match["date"],
    "status": target_match["status"],
    "minute": target_match["minute"],
    "league_id": target_match["league_id"],
    "league_name": target_match["league_name"],
    "season": target_match["season"],

    "home_team_id": target_match["home_team_id"],
    "home_team_name": target_match["home_team_name"],
    "home_goals": target_match["home_goals"],
    "home_stats": home_stats,

    "away_team_id": target_match["away_team_id"],
    "away_team_name": target_match["away_team_name"],
    "away_goals": target_match["away_goals"],
    "away_stats": away_stats
}

print(match_snapshot)