import pandas as pd

from database.connection import get_connection

from features.elo import calculate_elo_history


PREMIER_LEAGUE_ID = 39


def load_finished_fixtures():
    connection = get_connection()

    query = """
        SELECT
            f.fixture_id,
            f.date,
            f.league_id,
            f.season,
            f.round,

            f.home_team_id,
            home_team.team_name AS home_team_name,

            f.away_team_id,
            away_team.team_name AS away_team_name,

            f.home_goals,
            f.away_goals,

            home_stats.shots_on_goal AS home_shots_on_goal,
            away_stats.shots_on_goal AS away_shots_on_goal

        FROM fixtures f

        JOIN teams home_team
            ON home_team.team_id = f.home_team_id

        JOIN teams away_team
            ON away_team.team_id = f.away_team_id

        LEFT JOIN fixture_statistics home_stats
            ON home_stats.fixture_id = f.fixture_id
            AND home_stats.team_id = f.home_team_id

        LEFT JOIN fixture_statistics away_stats
            ON away_stats.fixture_id = f.fixture_id
            AND away_stats.team_id = f.away_team_id

        WHERE f.league_id = %s
          AND f.status = 'Match Finished'
          AND f.home_goals IS NOT NULL
          AND f.away_goals IS NOT NULL

        ORDER BY
            f.date,
            f.fixture_id;
    """

    with connection.cursor() as cursor:
        cursor.execute(
            query,
            (PREMIER_LEAGUE_ID,)
        )

        rows = cursor.fetchall()

        columns = [
            description.name
            for description in cursor.description
        ]

    connection.close()

    return pd.DataFrame(
        rows,
        columns=columns
    )


def calculate_points(
    goals_for,
    goals_against,
):
    if goals_for > goals_against:
        return 3

    if goals_for == goals_against:
        return 1

    return 0


def build_team_match_history(fixtures):
    team_rows = []

    for fixture in fixtures.itertuples(
        index=False
    ):
        home_points = calculate_points(
            fixture.home_goals,
            fixture.away_goals,
        )

        away_points = calculate_points(
            fixture.away_goals,
            fixture.home_goals,
        )

        team_rows.append(
            {
                "fixture_id":
                    fixture.fixture_id,

                "date":
                    fixture.date,

                "league_id":
                    fixture.league_id,

                "season":
                    fixture.season,

                "round":
                    fixture.round,

                "team_id":
                    fixture.home_team_id,

                "team_name":
                    fixture.home_team_name,

                "opponent_id":
                    fixture.away_team_id,

                "opponent_name":
                    fixture.away_team_name,

                "is_home":
                    True,

                "goals_for":
                    fixture.home_goals,

                "goals_against":
                    fixture.away_goals,

                "points":
                    home_points,

                "shots_on_target_for":
                    fixture.home_shots_on_goal,

                "shots_on_target_against":
                    fixture.away_shots_on_goal,
            }
        )

        team_rows.append(
            {
                "fixture_id":
                    fixture.fixture_id,

                "date":
                    fixture.date,

                "league_id":
                    fixture.league_id,

                "season":
                    fixture.season,

                "round":
                    fixture.round,

                "team_id":
                    fixture.away_team_id,

                "team_name":
                    fixture.away_team_name,

                "opponent_id":
                    fixture.home_team_id,

                "opponent_name":
                    fixture.home_team_name,

                "is_home":
                    False,

                "goals_for":
                    fixture.away_goals,

                "goals_against":
                    fixture.home_goals,

                "points":
                    away_points,

                "shots_on_target_for":
                    fixture.away_shots_on_goal,

                "shots_on_target_against":
                    fixture.home_shots_on_goal,
            }
        )

    team_history = pd.DataFrame(team_rows)

    team_history = team_history.sort_values(
        by=[
            "team_id",
            "date",
            "fixture_id",
        ]
    ).reset_index(drop=True)

    return team_history

def validate_team_match_history(team_history):
    fixture_checks = (
        team_history
        .groupby("fixture_id")
        .agg(
            rows=("fixture_id", "size"),
            teams=("team_id", "nunique"),
            home_rows=("is_home", "sum"),
        )
    )

    invalid = fixture_checks[
        (fixture_checks["rows"] != 2)
        | (fixture_checks["teams"] != 2)
        | (fixture_checks["home_rows"] != 1)
    ]

    if not invalid.empty:
        raise ValueError(
            "Invalid team-perspective structure:\n"
            + invalid.to_string()
        )


def add_pl_spell_id(team_history):
    team_history = team_history.copy()

    season_gap = (
        team_history
        .groupby("team_id")["season"]
        .diff()
    )

    team_history["new_pl_spell"] = (
        season_gap.isna()
        | (season_gap > 1)
    )

    team_history["pl_spell_id"] = (
        team_history
        .groupby("team_id")["new_pl_spell"]
        .cumsum()
        .astype(int)
    )

    return team_history


def add_rolling_features(team_history):
    team_history = team_history.copy()

    groups = team_history.groupby(
        [
            "team_id",
            "pl_spell_id",
        ],
        sort=False,
    )

    team_history["history_matches"] = (
        groups.cumcount()
    )

    for window in [5, 10]:
        team_history[
            f"last{window}_matches_available"
        ] = (
            team_history["history_matches"]
            .clip(upper=window)
        )

    rolling_metrics = {
        "points":
            "ppg",

        "goals_for":
            "goals_for_avg",

        "goals_against":
            "goals_against_avg",

        "shots_on_target_for":
            "shots_on_target_for_avg",

        "shots_on_target_against":
            "shots_on_target_against_avg",
    }

    for source_column, feature_name in (
        rolling_metrics.items()
    ):
        for window in [5, 10]:

            output_column = (
                f"last{window}_"
                f"{feature_name}"
            )

            team_history[output_column] = (
                groups[source_column]
                .transform(
                    lambda series:
                        series
                        .shift(1)
                        .rolling(
                            window=window,
                            min_periods=1,
                        )
                        .mean()
                )
            )

    return team_history

def build_fixture_feature_dataset(team_history):
    rolling_columns = [
        "last5_ppg",
        "last10_ppg",

        "last5_goals_for_avg",
        "last10_goals_for_avg",

        "last5_goals_against_avg",
        "last10_goals_against_avg",

        "last5_shots_on_target_for_avg",
        "last10_shots_on_target_for_avg",

        "last5_shots_on_target_against_avg",
        "last10_shots_on_target_against_avg",
    ]

    home_rows = (
        team_history[
            team_history["is_home"]
        ]
        .copy()
    )

    away_rows = (
        team_history[
            ~team_history["is_home"]
        ]
        .copy()
    )

    home_columns = [
                       "fixture_id",
                       "date",
                       "season",
                       "team_id",
                       "team_name",
                       "goals_for",
                       "goals_against",
                       "history_matches",
                       "last5_matches_available",
                       "last10_matches_available",
                   ] + rolling_columns

    away_columns = [
                       "fixture_id",
                       "team_id",
                       "team_name",
                       "history_matches",
                       "last5_matches_available",
                       "last10_matches_available",
                   ] + rolling_columns

    home_rows = home_rows[
        home_columns
    ].copy()

    away_rows = away_rows[
        away_columns
    ].copy()

    home_rename = {
        "team_id":
            "home_team_id",

        "team_name":
            "home_team_name",

        "goals_for":
            "home_goals",

        "goals_against":
            "away_goals",

        "history_matches":
            "home_history_matches",

        "last5_matches_available":
            "home_last5_matches_available",

        "last10_matches_available":
            "home_last10_matches_available",
    }

    away_rename = {
        "team_id":
            "away_team_id",

        "team_name":
            "away_team_name",

        "history_matches":
            "away_history_matches",

        "last5_matches_available":
            "away_last5_matches_available",

        "last10_matches_available":
            "away_last10_matches_available",
    }

    for column in rolling_columns:
        home_rename[column] = (
            f"home_{column}"
        )

        away_rename[column] = (
            f"away_{column}"
        )

    home_rows = home_rows.rename(
        columns=home_rename
    )

    away_rows = away_rows.rename(
        columns=away_rename
    )

    dataset = home_rows.merge(
        away_rows,
        on="fixture_id",
        how="inner",
        validate="one_to_one",
    )

    dataset["last5_history_min"] = (
        dataset[
            [
                "home_last5_matches_available",
                "away_last5_matches_available",
            ]
        ]
        .min(axis=1)
    )

    dataset["last10_history_min"] = (
        dataset[
            [
                "home_last10_matches_available",
                "away_last10_matches_available",
            ]
        ]
        .min(axis=1)
    )

    for column in rolling_columns:
        dataset[
            f"{column}_diff"
        ] = (
            dataset[f"home_{column}"]
            - dataset[f"away_{column}"]
        )

    dataset["label_1x2"] = "D"

    dataset.loc[
        dataset["home_goals"]
        > dataset["away_goals"],
        "label_1x2"
    ] = "H"

    dataset.loc[
        dataset["home_goals"]
        < dataset["away_goals"],
        "label_1x2"
    ] = "A"

    dataset = dataset.sort_values(
        by=[
            "date",
            "fixture_id",
        ]
    ).reset_index(drop=True)

    return dataset

def add_elo_features(fixture_dataset):
    elo_history, _ = calculate_elo_history()

    elo_df = pd.DataFrame(
        elo_history
    )

    elo_df = elo_df[
        elo_df["league_id"]
        == PREMIER_LEAGUE_ID
    ][
        [
            "fixture_id",
            "home_elo_before",
            "away_elo_before",
            "elo_difference_before",
        ]
    ].copy()

    dataset = fixture_dataset.merge(
        elo_df,
        on="fixture_id",
        how="left",
        validate="one_to_one",
    )

    dataset = dataset.rename(
        columns={
            "elo_difference_before":
                "elo_diff"
        }
    )

    return dataset

if __name__ == "__main__":
    fixtures = load_finished_fixtures()

    team_history = build_team_match_history(
        fixtures
    )

    validate_team_match_history(
        team_history
    )

    team_history = add_pl_spell_id(
        team_history
    )

    team_history = add_rolling_features(
        team_history
    )

    fixture_dataset = (
        build_fixture_feature_dataset(
            team_history
        )
    )

    fixture_dataset = add_elo_features(
        fixture_dataset
    )

    fixture_dataset["minimum_history"] = (
        fixture_dataset[
            [
                "home_history_matches",
                "away_history_matches",
            ]
        ]
        .min(axis=1)
    )

    print(
        "\nFixtures by minimum available PL history:"
    )

    for threshold in [0, 1, 2, 3, 4, 5, 10]:
        count = (
                fixture_dataset[
                    "minimum_history"
                ] < threshold
        ).sum()

        print(
            f"Less than {threshold}:",
            count
        )

    missing_feature_rows = fixture_dataset[
        fixture_dataset[
            "last5_ppg_diff"
        ].isna()
    ][
        [
            "date",
            "season",

            "home_team_name",
            "away_team_name",

            "home_history_matches",
            "away_history_matches",
        ]
    ]

    print(
        "\nFixtures with no rolling history:"
    )

    print(
        missing_feature_rows.to_string(
            index=False
        )
    )

    print(
        "\nMissing rolling source values:"
    )

    print(
        team_history[
            [
                "points",
                "goals_for",
                "goals_against",
                "shots_on_target_for",
                "shots_on_target_against",
            ]
        ]
        .isna()
        .sum()
    )

    print(
        "Finished PL fixtures:",
        len(fixtures)
    )

    print(
        "Team-perspective rows:",
        len(team_history)
    )

    print(
        "Team-perspective validation: OK"
    )

    print(
        "\nManchester United sample:"
    )

    sample = team_history[
        team_history["team_name"]
        == "Manchester United"
        ][
        [
            "date",
            "opponent_name",

            "points",

            "last5_ppg",
            "last10_ppg",

            "last5_goals_for_avg",
            "last5_goals_against_avg",

            "last5_shots_on_target_for_avg",
            "last5_shots_on_target_against_avg",
        ]
    ]

    print(
        sample
        .head(12)
        .to_string(index=False)
    )

    print(
        "\nFixture dataset rows:",
        len(fixture_dataset)
    )

    print(
        "Unique fixtures:",
        fixture_dataset[
            "fixture_id"
        ].nunique()
    )

    print(
        "\n1X2 label distribution:"
    )

    print(
        fixture_dataset[
            "label_1x2"
        ].value_counts()
    )

    diff_columns = [
        "last5_ppg_diff",
        "last10_ppg_diff",

        "last5_goals_for_avg_diff",
        "last10_goals_for_avg_diff",

        "last5_goals_against_avg_diff",
        "last10_goals_against_avg_diff",

        "last5_shots_on_target_for_avg_diff",
        "last10_shots_on_target_for_avg_diff",

        "last5_shots_on_target_against_avg_diff",
        "last10_shots_on_target_against_avg_diff",
    ]

    print(
        "\nMissing difference features:"
    )

    print(
        fixture_dataset[
            diff_columns
        ]
        .isna()
        .sum()
    )

    print(
        "\nLatest 10 fixture feature rows:"
    )

    print(
        fixture_dataset[
            [
                "date",
                "home_team_name",
                "away_team_name",

                "home_last5_ppg",
                "away_last5_ppg",
                "last5_ppg_diff",

                "home_last5_goals_for_avg",
                "away_last5_goals_for_avg",
                "last5_goals_for_avg_diff",

                "label_1x2",
            ]
        ]
        .tail(10)
        .to_string(index=False)
    )
    model_features = [
        "elo_diff",

        "last5_ppg_diff",
        "last10_ppg_diff",

        "last5_goals_for_avg_diff",
        "last10_goals_for_avg_diff",

        "last5_goals_against_avg_diff",
        "last10_goals_against_avg_diff",

        "last5_shots_on_target_for_avg_diff",
        "last10_shots_on_target_for_avg_diff",

        "last5_shots_on_target_against_avg_diff",
        "last10_shots_on_target_against_avg_diff",

        "last5_history_min",
        "last10_history_min",
    ]

    print(
        "\n=== FINAL FEATURE DATASET AUDIT ==="
    )

    print(
        "Rows:",
        len(fixture_dataset)
    )

    print(
        "Unique fixtures:",
        fixture_dataset["fixture_id"].nunique()
    )

    print(
        "Duplicate fixture IDs:",
        fixture_dataset["fixture_id"].duplicated().sum()
    )

    print(
        "\nMissing values:"
    )

    print(
        fixture_dataset[
            model_features
        ]
        .isna()
        .sum()
    )

    print(
        "\nFeature ranges:"
    )

    print(
        fixture_dataset[
            model_features
        ]
        .agg(["min", "max"])
        .T
    )

    print(
        "\nFixtures by season:"
    )

    print(
        fixture_dataset[
            "season"
        ]
        .value_counts()
        .sort_index()
    )

    print(
        "\nLabels:"
    )

    print(
        fixture_dataset[
            "label_1x2"
        ]
        .value_counts()
    )

    print(
        "\nDate range:"
    )

    print(
        fixture_dataset["date"].min(),
        "->",
        fixture_dataset["date"].max()
    )

