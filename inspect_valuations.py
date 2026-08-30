import pandas as pd

players = pd.read_csv("data/raw/players.csv.gz")
valuations = pd.read_csv("data/raw/player_valuations.csv.gz")

target_date = pd.Timestamp("2024-08-01")
target_club = "Arsenal FC"

valuations["date"] = pd.to_datetime(valuations["date"])

historical = valuations[
    valuations["date"] <= target_date
].copy()

latest_per_player = (
    historical
    .sort_values("date")
    .groupby("player_id", as_index=False)
    .tail(1)
)

arsenal_squad = latest_per_player[
    latest_per_player["current_club_name"] == target_club
].copy()

arsenal_squad = arsenal_squad.sort_values(
    "market_value_in_eur",
    ascending=False
)

print("\nARSENAL SQUAD ON", target_date.date())
print(
    arsenal_squad[
        [
            "player_id",
            "date",
            "market_value_in_eur",
            "current_club_name"
        ]
    ]
)

print("\nNUMBER OF PLAYERS:", len(arsenal_squad))

arsenal_squad = arsenal_squad.merge(
    players[["player_id", "name"]],
    on="player_id",
    how="left"
)

print(
    arsenal_squad[
        [
            "name",
            "date",
            "market_value_in_eur",
            "current_club_name",
            "current_club_id"
        ]
    ].to_string(index=False)
)
print("\nCLUB IDS FOUND:")
print(
    arsenal_squad[
        ["current_club_id", "current_club_name"]
    ].drop_duplicates()
)

transfers = pd.read_csv("data/raw/transfers.csv.gz")

print("\nTRANSFERS")
print(transfers.shape)
print(transfers.columns.tolist())
print(transfers.head())

rice_transfers = transfers[
    transfers["player_name"].str.contains(
        "Declan Rice",
        case=False,
        na=False
    )
].sort_values("transfer_date")

print("\nDECLAN RICE TRANSFERS")
print(
    rice_transfers[
        [
            "transfer_date",
            "from_club_id",
            "from_club_name",
            "to_club_id",
            "to_club_name",
            "transfer_fee",
            "market_value_in_eur"
        ]
    ].to_string(index=False)
)

vieira_transfers = transfers[
    transfers["player_name"].str.contains(
        "Fábio Vieira",
        case=False,
        na=False
    )
].sort_values("transfer_date")

print("\nFABIO VIEIRA TRANSFERS")
print(
    vieira_transfers[
        [
            "transfer_date",
            "from_club_id",
            "from_club_name",
            "to_club_id",
            "to_club_name",
            "transfer_fee",
            "market_value_in_eur"
        ]
    ].to_string(index=False)
)

target_date = pd.Timestamp("2024-08-01")
arsenal_club_id = 11

transfers["transfer_date"] = pd.to_datetime(transfers["transfer_date"])

historical_transfers = transfers[
    transfers["transfer_date"] <= target_date
].copy()

latest_transfer_per_player = (
    historical_transfers
    .sort_values("transfer_date")
    .groupby("player_id", as_index=False)
    .tail(1)
)

arsenal_members = latest_transfer_per_player[
    latest_transfer_per_player["to_club_id"] == arsenal_club_id
][["player_id", "player_name"]].copy()

valuations_before_date = valuations[
    valuations["date"] <= target_date
].copy()

latest_valuation_per_player = (
    valuations_before_date
    .sort_values("date")
    .groupby("player_id", as_index=False)
    .tail(1)
)

arsenal_snapshot = arsenal_members.merge(
    latest_valuation_per_player[
        [
            "player_id",
            "date",
            "market_value_in_eur"
        ]
    ],
    on="player_id",
    how="left"
)

arsenal_snapshot = arsenal_snapshot.sort_values(
    "market_value_in_eur",
    ascending=False
)

print("\nARSENAL SNAPSHOT FROM TRANSFERS")
print(
    arsenal_snapshot[
        [
            "player_name",
            "date",
            "market_value_in_eur"
        ]
    ].to_string(index=False)
)

print("\nNUMBER OF PLAYERS:", len(arsenal_snapshot))
print(
    "TOTAL SQUAD VALUE:",
    arsenal_snapshot["market_value_in_eur"].sum()
)
clubs = pd.read_csv("data/raw/clubs.csv.gz")

print("\nCLUBS")
print(clubs.shape)
print(clubs.columns.tolist())
print(clubs.head())

english_clubs = clubs[
    clubs["domestic_competition_id"].isin(["GB1", "GB2"])
].copy()

print("\nPREMIER LEAGUE + CHAMPIONSHIP CLUBS")
print(
    english_clubs[
        [
            "club_id",
            "name",
            "domestic_competition_id",
            "last_season"
        ]
    ]
    .sort_values(["domestic_competition_id", "name"])
    .to_string(index=False)
)

print("\nNUMBER OF CLUBS:", len(english_clubs))

print("\nCOMPETITIONS IN PLAYER VALUATIONS")
print(
    valuations[
        "player_club_domestic_competition_id"
    ].value_counts()
)

championship_clubs = (
    valuations[
        valuations["player_club_domestic_competition_id"] == "GB2"
    ][
        [
            "current_club_id",
            "current_club_name"
        ]
    ]
    .drop_duplicates()
    .sort_values("current_club_name")
)

print("\nCHAMPIONSHIP CLUBS FROM VALUATIONS")
print(championship_clubs.to_string(index=False))

print("\nNUMBER OF GB2 CLUBS:", len(championship_clubs))

transfer_clubs_from = transfers[
    ["from_club_id", "from_club_name"]
].rename(
    columns={
        "from_club_id": "club_id",
        "from_club_name": "club_name"
    }
)

transfer_clubs_to = transfers[
    ["to_club_id", "to_club_name"]
].rename(
    columns={
        "to_club_id": "club_id",
        "to_club_name": "club_name"
    }
)

transfer_clubs = pd.concat(
    [transfer_clubs_from, transfer_clubs_to]
).drop_duplicates()

print("\nTRANSFER CLUBS")
print("NUMBER OF UNIQUE CLUB IDS:", transfer_clubs["club_id"].nunique())


names_to_check = [
    "Coventry",
    "Blackburn",
    "Bristol City",
    "Millwall",
    "Preston",
    "Portsmouth",
    "Oxford United",
    "Wrexham",
    "Charlton"
]

for name in names_to_check:
    result = transfer_clubs[
        transfer_clubs["club_name"].str.contains(
            name,
            case=False,
            na=False
        )
    ]

    print(f"\n{name}")
    print(result.to_string(index=False))

appearances = pd.read_csv("data/raw/appearances.csv.gz")

appearances["date"] = pd.to_datetime(
    appearances["date"]
)

arsenal_id = 11
target_date = pd.Timestamp("2024-08-01")

window_start = target_date - pd.Timedelta(days=120)
window_end = target_date + pd.Timedelta(days=30)

arsenal_recent_players = (
    appearances[
        (appearances["player_club_id"] == arsenal_id)
        & (appearances["date"] >= window_start)
        & (appearances["date"] <= window_end)
    ][
        [
            "player_id",
            "player_name",
            "date",
            "minutes_played"
        ]
    ]
    .sort_values("date")
)

print("\nARSENAL APPEARANCES AROUND 2024-08-01")
print(
    arsenal_recent_players
    .to_string(index=False)
)

print(
    "\nUNIQUE PLAYERS:",
    arsenal_recent_players["player_id"].nunique()
)

print("\nAPPEARANCES")
print(appearances.shape)
print(appearances.columns.tolist())
print(appearances.head())

game_lineups = pd.read_csv(
    "data/raw/game_lineups.csv.gz"
)

print("\nGAME LINEUPS")
print(game_lineups.shape)
print(game_lineups.columns.tolist())
print(game_lineups.head())

game_lineups["date"] = pd.to_datetime(
    game_lineups["date"]
)

arsenal_id = 11
target_date = pd.Timestamp("2024-08-01")

window_start = target_date - pd.Timedelta(days=120)

arsenal_lineup_players = game_lineups[
    (game_lineups["club_id"] == arsenal_id)
    & (game_lineups["date"] >= window_start)
    & (game_lineups["date"] < target_date)
].copy()

print("\nLINEUP TYPES")
print(
    arsenal_lineup_players["type"].value_counts()
)

print("\nARSENAL MATCHDAY-SQUAD PLAYERS BEFORE 2024-08-01")

unique_players = (
    arsenal_lineup_players[
        [
            "player_id",
            "player_name"
        ]
    ]
    .drop_duplicates()
    .sort_values("player_name")
)

print(unique_players.to_string(index=False))

print(
    "\nUNIQUE PLAYERS:",
    unique_players["player_id"].nunique()
)