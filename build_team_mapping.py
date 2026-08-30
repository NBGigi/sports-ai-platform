import pandas as pd
from rapidfuzz import process, fuzz
from database.connection import get_connection
from database.queries import insert_team_external_ids

transfers = pd.read_csv("data/raw/transfers.csv.gz")

from_clubs = transfers[
    ["from_club_id", "from_club_name"]
].rename(
    columns={
        "from_club_id": "club_id",
        "from_club_name": "club_name"
    }
)

to_clubs = transfers[
    ["to_club_id", "to_club_name"]
].rename(
    columns={
        "to_club_id": "club_id",
        "to_club_name": "club_name"
    }
)

transfer_clubs = pd.concat(
    [from_clubs, to_clubs],
    ignore_index=True
).drop_duplicates()

api_football_teams = {
    36: "Fulham",
    42: "Arsenal",
    52: "Crystal Palace",
    41: "Southampton",
    40: "Liverpool",
    63: "Leeds",
    48: "West Ham",
    34: "Newcastle",
    60: "West Brom",
    46: "Leicester",
    47: "Tottenham",
    45: "Everton",
    62: "Sheffield Utd",
    39: "Wolves",
    51: "Brighton",
    49: "Chelsea",
    33: "Manchester United",
    44: "Burnley",
    66: "Aston Villa",
    50: "Manchester City",
    55: "Brentford",
    38: "Watford",
    71: "Norwich",
    65: "Nottingham Forest",
    35: "Bournemouth",
    1359: "Luton",
    57: "Ipswich",
    746: "Sunderland",
    1346: "Coventry",
    64: "Hull City",
    70: "Middlesbrough",
    54: "Birmingham",
    1358: "Wycombe",
    73: "Rotherham",
    67: "Blackburn",
    37: "Huddersfield",
    43: "Cardiff",
    74: "Sheffield Wednesday",
    56: "Bristol City",
    58: "Millwall",
    75: "Stoke City",
    59: "Preston",
    76: "Swansea",
    69: "Derby",
    53: "Reading",
    72: "QPR",
    747: "Barnsley",
    1356: "Blackpool",
    1350: "Peterborough",
    61: "Wigan",
    1357: "Plymouth",
    1355: "Portsmouth",
    1338: "Oxford United",
    1837: "Wrexham",
    1335: "Charlton",
    68: "Bolton",
    1379: "Lincoln",
}

club_names = transfer_clubs["club_name"].dropna().tolist()

manual_overrides = {
    "Manchester City": (281, "Man City"),
    "Manchester United": (985, "Man Utd"),
    "Nottingham Forest": (703, "Nottingham Forest"),
    "Sheffield Utd": (350, "Sheff Utd"),
    "Sheffield Wednesday": (1035, "Sheff Wed"),
    "Lincoln": (1198, "Lincoln City"),
}

results = []

for team_id, team_name in api_football_teams.items():

    if team_name in manual_overrides:
        candidate_id, candidate_name = manual_overrides[team_name]
        score = 100.0

    else:
        best_match = process.extractOne(
            team_name,
            club_names,
            scorer=fuzz.WRatio
        )

        candidate_name, score, _ = best_match

        candidate_rows = transfer_clubs[
            transfer_clubs["club_name"] == candidate_name
        ]

        candidate_id = candidate_rows.iloc[0]["club_id"]

    results.append(
        {
            "api_team_id": team_id,
            "api_team_name": team_name,
            "tm_club_id": int(candidate_id),
            "tm_club_name": candidate_name,
            "score": round(score, 1),
        }
    )

mapping_df = pd.DataFrame(results)

print("\nFINAL VERIFIED MAPPING")
print(
    mapping_df
    .sort_values("api_team_name")
    .to_string(index=False)
)

print("\nNUMBER OF TEAMS:", len(mapping_df))
print(
    "UNIQUE API TEAM IDS:",
    mapping_df["api_team_id"].nunique()
)
print(
    "UNIQUE TRANSFERMARKT IDS:",
    mapping_df["tm_club_id"].nunique()
)

mappings = []

for _, row in mapping_df.iterrows():
    mappings.append(
        {
            "team_id": int(row["api_team_id"]),
            "provider": "transfermarkt",
            "external_id": int(row["tm_club_id"]),
        }
    )

connection = get_connection()

insert_team_external_ids(
    connection,
    mappings
)

connection.close()

print("\nTransfermarkt mappings saved to database")