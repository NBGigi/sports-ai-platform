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

print(response.status_code)

data = response.json()

print("Errors:", data["errors"])
print("Results:", data["results"])


first_match = data["response"][0]

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

print(f"Parsed matches: {len(parsed_matches)}")
print(parsed_matches[0])
print(parsed_matches[-1])