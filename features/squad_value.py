from pathlib import Path

import pandas as pd

from database.connection import get_connection
from database.queries import (
    get_external_team_id,
    get_fixture,
)


# --------------------------------------------------
# Paths
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

transfers_path = (
    BASE_DIR
    / "data"
    / "raw"
    / "transfers.csv.gz"
)

valuations_path = (
    BASE_DIR
    / "data"
    / "raw"
    / "player_valuations.csv.gz"
)

game_lineups_path = (
    BASE_DIR
    / "data"
    / "raw"
    / "game_lineups.csv.gz"
)


# --------------------------------------------------
# Load datasets
# --------------------------------------------------

transfers = pd.read_csv(
    transfers_path
)

valuations = pd.read_csv(
    valuations_path
)

game_lineups = pd.read_csv(
    game_lineups_path,
    low_memory=False,
)


# --------------------------------------------------
# Convert dates
# --------------------------------------------------

transfers["transfer_date"] = pd.to_datetime(
    transfers["transfer_date"]
)

valuations["date"] = pd.to_datetime(
    valuations["date"]
)

game_lineups["date"] = pd.to_datetime(
    game_lineups["date"]
)


# --------------------------------------------------
# Historical squad reconstruction
# --------------------------------------------------

def get_historical_squad_value(
    club_id,
    target_date,
    squad_window_days=120,
):

    target_date = pd.Timestamp(
        target_date
    )

    if target_date.tzinfo is not None:
        target_date = (
            target_date.tz_localize(None)
        )

    # Transfermarkt data has day-level dates.
    # We intentionally use information strictly
    # BEFORE the match date to avoid leakage.
    target_date = target_date.normalize()

    window_start = (
        target_date
        - pd.Timedelta(
            days=squad_window_days
        )
    )

    # --------------------------------------------------
    # 1. Players seen in recent matchday squads
    # --------------------------------------------------

    recent_lineups = game_lineups[
        (
            game_lineups["club_id"]
            == club_id
        )
        &
        (
            game_lineups["date"]
            >= window_start
        )
        &
        (
            game_lineups["date"]
            < target_date
        )
    ].copy()

    if len(recent_lineups) > 0:

        recent_players = (
            recent_lineups
            .sort_values("date")
            .groupby(
                "player_id",
                as_index=False,
            )
            .tail(1)
        )

        recent_players = (
            recent_players[
                [
                    "player_id",
                    "player_name",
                    "date",
                ]
            ]
            .rename(
                columns={
                    "date":
                        "last_lineup_date"
                }
            )
        )

    else:

        recent_players = pd.DataFrame(
            columns=[
                "player_id",
                "player_name",
                "last_lineup_date",
            ]
        )

    # --------------------------------------------------
    # 2. Recent transfers INTO the club
    #
    # This catches a new signing who joined before
    # target_date but has not appeared yet.
    # --------------------------------------------------

    recent_incoming_transfers = (
        transfers[
            (
                transfers["to_club_id"]
                == club_id
            )
            &
            (
                transfers["transfer_date"]
                >= window_start
            )
            &
            (
                transfers["transfer_date"]
                < target_date
            )
        ][
            [
                "player_id",
                "player_name",
            ]
        ]
        .copy()
    )

    recent_incoming_transfers[
        "last_lineup_date"
    ] = pd.NaT

    # --------------------------------------------------
    # 3. Combine lineup players + new signings
    # --------------------------------------------------

    squad_candidates = pd.concat(
        [
            recent_players,
            recent_incoming_transfers,
        ],
        ignore_index=True,
    )

    squad_candidates = (
        squad_candidates
        .sort_values(
            "last_lineup_date",
            na_position="first",
        )
        .drop_duplicates(
            subset=["player_id"],
            keep="last",
        )
    )

    if len(squad_candidates) == 0:
        return {
            "club_id": club_id,
            "date": target_date,
            "player_count": 0,
            "valuation_count": 0,
            "valuation_coverage": 0,
            "squad_value_eur": 0,
            "players": squad_candidates,
            "median_valuation_age_days": None,
            "max_valuation_age_days": None,
            "squad_value_is_reliable": False,
        }

    candidate_player_ids = (
        squad_candidates[
            "player_id"
        ].tolist()
    )

    # --------------------------------------------------
    # 4. Find each candidate's latest transfer
    # before target_date
    # --------------------------------------------------

    candidate_transfers = transfers[
        transfers["player_id"].isin(
            candidate_player_ids
        )
        &
        (
            transfers["transfer_date"]
            < target_date
        )
    ].copy()

    latest_transfer_per_player = (
        candidate_transfers
        .sort_values(
            "transfer_date"
        )
        .groupby(
            "player_id",
            as_index=False,
        )
        .tail(1)
    )

    latest_transfer_per_player = (
        latest_transfer_per_player[
            [
                "player_id",
                "transfer_date",
                "to_club_id",
            ]
        ]
        .rename(
            columns={
                "transfer_date":
                    "latest_transfer_date",
                "to_club_id":
                    "latest_transfer_to_club_id",
            }
        )
    )

    squad_candidates = (
        squad_candidates.merge(
            latest_transfer_per_player,
            on="player_id",
            how="left",
        )
    )

    # --------------------------------------------------
    # 5. Remove players who left AFTER their last
    # appearance for this club.
    #
    # Example:
    # player appeared for Arsenal in May,
    # transferred to another club in July,
    # target date is August.
    #
    # Without this check, he would still be counted.
    # --------------------------------------------------

    def player_is_still_at_club(row):

        latest_transfer_date = (
            row["latest_transfer_date"]
        )

        latest_transfer_club = (
            row[
                "latest_transfer_to_club_id"
            ]
        )

        last_lineup_date = (
            row["last_lineup_date"]
        )

        # No transfer history available.
        if pd.isna(
            latest_transfer_date
        ):
            return True

        # Latest known transfer says
        # the player joined this club.
        if latest_transfer_club == club_id:
            return True

        # Player has no lineup appearance,
        # and latest transfer says another club.
        if pd.isna(
            last_lineup_date
        ):
            return False

        # Player transferred away after
        # his latest lineup appearance.
        if (
            latest_transfer_date
            > last_lineup_date
        ):
            return False

        return True

    still_at_club_mask = (
        squad_candidates.apply(
            player_is_still_at_club,
            axis=1,
        )
    )

    squad = (
        squad_candidates[
            still_at_club_mask
        ]
        .copy()
    )

    # --------------------------------------------------
    # 6. Latest historical valuation
    #
    # Strictly BEFORE target_date.
    # This prevents using a valuation published
    # later on the match date.
    # --------------------------------------------------

    squad_player_ids = (
        squad[
            "player_id"
        ].tolist()
    )

    historical_valuations = valuations[
        valuations[
            "player_id"
        ].isin(
            squad_player_ids
        )
        &
        (
            valuations["date"]
            < target_date
        )
    ].copy()

    latest_valuation_per_player = (
        historical_valuations
        .sort_values("date")
        .groupby(
            "player_id",
            as_index=False,
        )
        .tail(1)
    )

    squad = squad.merge(
        latest_valuation_per_player[
            [
                "player_id",
                "date",
                "market_value_in_eur",
            ]
        ],
        on="player_id",
        how="left",
    )

    # --------------------------------------------------
    # 7. Squad value
    # --------------------------------------------------

    total_value = (
        squad[
            "market_value_in_eur"
        ]
        .sum()
    )

    players_with_valuation = (
        squad[
            squad[
                "market_value_in_eur"
            ].notna()
        ]
        .copy()
    )

    valuation_count = len(
        players_with_valuation
    )

    coverage = (
        valuation_count
        / len(squad)
        if len(squad) > 0
        else 0
    )

    # --------------------------------------------------
    # 8. Valuation freshness
    # --------------------------------------------------

    if valuation_count > 0:

        players_with_valuation[
            "valuation_age_days"
        ] = (
            target_date
            - players_with_valuation[
                "date"
            ]
        ).dt.days

        median_valuation_age_days = (
            players_with_valuation[
                "valuation_age_days"
            ].median()
        )

        max_valuation_age_days = (
            players_with_valuation[
                "valuation_age_days"
            ].max()
        )

    else:

        median_valuation_age_days = None
        max_valuation_age_days = None

    # --------------------------------------------------
    # Result
    # --------------------------------------------------
    squad_value_is_reliable = (
            len(squad) >= 18
            and coverage >= 0.75
            and (
                    median_valuation_age_days is not None
                    and median_valuation_age_days <= 365
            )
    )

    return {
        "club_id": club_id,
        "date": target_date,
        "player_count": len(squad),
        "valuation_count": valuation_count,
        "valuation_coverage": coverage,
        "squad_value_eur": total_value,
        "players": squad,
        "median_valuation_age_days":
            median_valuation_age_days,
        "max_valuation_age_days":
            max_valuation_age_days,
        "squad_value_is_reliable": squad_value_is_reliable,
    }


# --------------------------------------------------
# Internal team ID -> Transfermarkt club ID
# --------------------------------------------------

def get_team_historical_squad_value(
    team_id,
    target_date,
):

    connection = get_connection()

    transfermarkt_club_id = (
        get_external_team_id(
            connection,
            team_id,
            "transfermarkt",
        )
    )

    connection.close()

    if transfermarkt_club_id is None:
        raise ValueError(
            "No Transfermarkt mapping found "
            f"for team_id {team_id}"
        )

    return get_historical_squad_value(
        transfermarkt_club_id,
        target_date,
    )


# --------------------------------------------------
# Fixture-level features
# --------------------------------------------------

def get_fixture_squad_value_features(
    fixture_id,
):

    connection = get_connection()

    fixture = get_fixture(
        connection,
        fixture_id,
    )

    connection.close()

    if fixture is None:
        raise ValueError(
            f"Fixture {fixture_id} "
            "was not found"
        )

    match_date = fixture["date"]

    home = (
        get_team_historical_squad_value(
            fixture["home_team_id"],
            match_date,
        )
    )

    away = (
        get_team_historical_squad_value(
            fixture["away_team_id"],
            match_date,
        )
    )

    home_value = (
        home["squad_value_eur"]
    )

    away_value = (
        away["squad_value_eur"]
    )

    value_difference = (
        home_value
        - away_value
    )

    value_ratio = (
        home_value / away_value
        if away_value > 0
        else None
    )

    return {
        "fixture_id": fixture_id,
        "date": match_date,

        "home_team_id":
            fixture["home_team_id"],

        "away_team_id":
            fixture["away_team_id"],

        "home_squad_value":
            home_value,

        "away_squad_value":
            away_value,

        "squad_value_difference":
            value_difference,

        "squad_value_ratio":
            value_ratio,

        "home_valuation_coverage":
            home[
                "valuation_coverage"
            ],

        "away_valuation_coverage":
            away[
                "valuation_coverage"
            ],

        "home_player_count":
            home[
                "player_count"
            ],

        "away_player_count":
            away[
                "player_count"
            ],

        "home_median_valuation_age_days":
            home[
                "median_valuation_age_days"
            ],

        "away_median_valuation_age_days":
            away[
                "median_valuation_age_days"
            ],

        "home_max_valuation_age_days":
            home[
                "max_valuation_age_days"
            ],

        "away_max_valuation_age_days":
            away[
                "max_valuation_age_days"
            ],

        "home_squad_value_is_reliable":
            home["squad_value_is_reliable"],

        "away_squad_value_is_reliable":
            away["squad_value_is_reliable"],
    }


# --------------------------------------------------
# Manual test
# --------------------------------------------------

if __name__ == "__main__":

    result = (
        get_fixture_squad_value_features(
            fixture_id=1557381
        )
    )

    for key, value in result.items():
        print(
            key,
            "=",
            value,
        )

    print(
        "\nLATEST VALUATION DATE "
        "IN DATASET:"
    )

    print(
        valuations[
            "date"
        ].max()
    )