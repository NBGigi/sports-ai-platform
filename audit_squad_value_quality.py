import pandas as pd

from database.connection import get_connection
from features.squad_value import get_fixture_squad_value_features


TARGET_LEAGUES = [39, 40]
TARGET_SEASONS = [2021, 2024, 2025]

SAMPLE_PER_GROUP = 10


def get_sample_fixtures():
    connection = get_connection()

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                fixture_id,
                league_id,
                season,
                date
            FROM fixtures
            WHERE status = 'Match Finished'
              AND league_id = ANY(%s)
              AND season = ANY(%s)
            ORDER BY league_id, season, date;
            """,
            (
                TARGET_LEAGUES,
                TARGET_SEASONS,
            )
        )

        rows = cursor.fetchall()

    connection.close()

    df = pd.DataFrame(
        rows,
        columns=[
            "fixture_id",
            "league_id",
            "season",
            "date",
        ]
    )

    if df.empty:
        return df

    sampled = (
        df.groupby(
            ["league_id", "season"],
            group_keys=False
        )
        .sample(
            n=SAMPLE_PER_GROUP,
            random_state=42
        )
        .reset_index(drop=True)
    )

    return sampled


fixtures = get_sample_fixtures()

results = []


for _, fixture in fixtures.iterrows():

    fixture_id = fixture["fixture_id"]
    league_id = fixture["league_id"]
    season = fixture["season"]
    date = fixture["date"]

    try:
        features = get_fixture_squad_value_features(
            fixture_id
        )

        results.append(
            {
                "fixture_id":
                    fixture_id,

                "league_id":
                    league_id,

                "season":
                    season,

                "date":
                    date,

                "home_player_count":
                    features[
                        "home_player_count"
                    ],

                "away_player_count":
                    features[
                        "away_player_count"
                    ],

                "home_coverage":
                    features[
                        "home_valuation_coverage"
                    ],

                "away_coverage":
                    features[
                        "away_valuation_coverage"
                    ],

                "home_median_age":
                    features[
                        "home_median_valuation_age_days"
                    ],

                "away_median_age":
                    features[
                        "away_median_valuation_age_days"
                    ],

                "home_max_age":
                    features[
                        "home_max_valuation_age_days"
                    ],

                "away_max_age":
                    features[
                        "away_max_valuation_age_days"
                    ],

                "home_value":
                    features[
                        "home_squad_value"
                    ],

                "away_value":
                    features[
                        "away_squad_value"
                    ],

                "home_reliable":
                    features[
                        "home_squad_value_is_reliable"
                    ],

                "away_reliable":
                    features[
                        "away_squad_value_is_reliable"
                    ],
            }
        )

    except Exception as error:
        print(
            f"Failed fixture "
            f"{fixture_id}: {error}"
        )


df = pd.DataFrame(results)


print("\n==============================")
print("INDIVIDUAL AUDIT RESULTS")
print("==============================\n")

print(
    df.to_string(
        index=False
    )
)


# --------------------------------------------------
# Convert home / away rows into team-level rows
# --------------------------------------------------

home_rows = df[
    [
        "fixture_id",
        "league_id",
        "season",
        "date",
        "home_player_count",
        "home_coverage",
        "home_median_age",
        "home_max_age",
        "home_value",
        "home_reliable",
    ]
].copy()

home_rows = home_rows.rename(
    columns={
        "home_player_count":
            "player_count",

        "home_coverage":
            "coverage",

        "home_median_age":
            "median_age",

        "home_max_age":
            "max_age",

        "home_value":
            "squad_value",

        "home_reliable":
            "reliable",
    }
)


away_rows = df[
    [
        "fixture_id",
        "league_id",
        "season",
        "date",
        "away_player_count",
        "away_coverage",
        "away_median_age",
        "away_max_age",
        "away_value",
        "away_reliable",
    ]
].copy()

away_rows = away_rows.rename(
    columns={
        "away_player_count":
            "player_count",

        "away_coverage":
            "coverage",

        "away_median_age":
            "median_age",

        "away_max_age":
            "max_age",

        "away_value":
            "squad_value",

        "away_reliable":
            "reliable",
    }
)


team_rows = pd.concat(
    [
        home_rows,
        away_rows,
    ],
    ignore_index=True
)


# --------------------------------------------------
# Summary by league and season
# --------------------------------------------------

summary = (
    team_rows
    .groupby(
        [
            "league_id",
            "season",
        ]
    )
    .agg(
        samples=(
            "fixture_id",
            "count"
        ),

        player_count_mean=(
            "player_count",
            "mean"
        ),

        player_count_median=(
            "player_count",
            "median"
        ),

        player_count_min=(
            "player_count",
            "min"
        ),

        player_count_max=(
            "player_count",
            "max"
        ),

        coverage_mean=(
            "coverage",
            "mean"
        ),

        coverage_median=(
            "coverage",
            "median"
        ),

        coverage_min=(
            "coverage",
            "min"
        ),

        median_age_median=(
            "median_age",
            "median"
        ),

        median_age_max=(
            "median_age",
            "max"
        ),

        max_age_median=(
            "max_age",
            "median"
        ),

        max_age_max=(
            "max_age",
            "max"
        ),
    )
    .reset_index()
)


print("\n==============================")
print("SUMMARY BY LEAGUE AND SEASON")
print("==============================\n")

print(
    summary.to_string(
        index=False
    )
)


# --------------------------------------------------
# Basic quality audit
#
# These thresholds are only for analysis.
# The real reliability flag now comes from
# squad_value.py itself.
# --------------------------------------------------

team_rows["player_count_ok"] = (
    team_rows["player_count"] >= 18
)

team_rows["coverage_ok"] = (
    team_rows["coverage"] >= 0.75
)

team_rows["freshness_ok"] = (
    team_rows["median_age"].notna()
    &
    (
        team_rows["median_age"] <= 365
    )
)

team_rows["basic_quality_ok"] = (
    team_rows["player_count_ok"]
    &
    team_rows["coverage_ok"]
    &
    team_rows["freshness_ok"]
)


quality_summary = (
    team_rows
    .groupby(
        [
            "league_id",
            "season",
        ]
    )
    .agg(
        samples=(
            "fixture_id",
            "count"
        ),

        player_count_pass_rate=(
            "player_count_ok",
            "mean"
        ),

        coverage_pass_rate=(
            "coverage_ok",
            "mean"
        ),

        freshness_pass_rate=(
            "freshness_ok",
            "mean"
        ),

        overall_pass_rate=(
            "basic_quality_ok",
            "mean"
        ),
    )
    .reset_index()
)


print("\n==============================")
print("BASIC QUALITY PASS RATES")
print("==============================\n")

print(
    quality_summary.to_string(
        index=False
    )
)


# --------------------------------------------------
# Reliability flag coming directly from
# features/squad_value.py
# --------------------------------------------------

reliability_summary = (
    team_rows
    .groupby(
        [
            "league_id",
            "season",
        ]
    )
    .agg(
        samples=(
            "fixture_id",
            "count"
        ),

        reliable_count=(
            "reliable",
            "sum"
        ),

        reliable_rate=(
            "reliable",
            "mean"
        ),
    )
    .reset_index()
)


print("\n==============================")
print("SQUAD VALUE RELIABILITY")
print("==============================\n")

print(
    reliability_summary.to_string(
        index=False
    )
)


# --------------------------------------------------
# Show unreliable observations
# --------------------------------------------------

unreliable_rows = team_rows[
    team_rows["reliable"] == False
].copy()


print("\n==============================")
print("UNRELIABLE SQUAD VALUES")
print("==============================\n")

if unreliable_rows.empty:
    print("No unreliable squad values found.")

else:
    print(
        unreliable_rows[
            [
                "fixture_id",
                "league_id",
                "season",
                "date",
                "player_count",
                "coverage",
                "median_age",
                "max_age",
                "squad_value",
            ]
        ]
        .sort_values(
            [
                "league_id",
                "season",
                "date",
            ]
        )
        .to_string(
            index=False
        )
    )