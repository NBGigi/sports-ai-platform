import pandas as pd

from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    log_loss,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from features.rolling_feature import (
    load_finished_fixtures,
    build_team_match_history,
    validate_team_match_history,
    add_pl_spell_id,
)

from modeling.dataset_split import (
    build_model_dataset,
)


TARGET = "label_1x2"


FEATURE_SETS = {
    "Elo only": [
        "elo_diff",
    ],

    "Elo + Venue Form": [
        "elo_diff",
        "venue_last5_ppg_diff",
        "venue_history_min",
    ],
}


FOLDS = [
    {
        "name": "Fold 1",
        "train_start": 2021,
        "train_end": 2021,
        "validation_season": 2022,
    },
    {
        "name": "Fold 2",
        "train_start": 2021,
        "train_end": 2022,
        "validation_season": 2023,
    },
    {
        "name": "Fold 3",
        "train_start": 2021,
        "train_end": 2023,
        "validation_season": 2024,
    },
]


def build_model():
    return Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="median",
                    add_indicator=True,
                ),
            ),
            (
                "scaler",
                StandardScaler(),
            ),
            (
                "model",
                LogisticRegression(
                    solver="lbfgs",
                    max_iter=1000,
                ),
            ),
        ]
    )


def build_venue_form_features():
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

    # Separate history by:
    # team + PL spell + home/away venue.
    venue_groups = team_history.groupby(
        [
            "team_id",
            "pl_spell_id",
            "is_home",
        ],
        sort=False,
    )

    # Number of previous matches at this venue.
    team_history[
        "venue_history_matches"
    ] = (
        venue_groups.cumcount()
    )

    team_history[
        "last5_venue_matches_available"
    ] = (
        team_history[
            "venue_history_matches"
        ]
        .clip(upper=5)
    )

    # Important:
    # shift(1) removes the current match
    # before calculating the rolling average.
    team_history[
        "last5_venue_ppg"
    ] = (
        venue_groups["points"]
        .transform(
            lambda series:
                series
                .shift(1)
                .rolling(
                    window=5,
                    min_periods=1,
                )
                .mean()
        )
    )

    home_rows = (
        team_history[
            team_history["is_home"]
        ][
            [
                "fixture_id",
                "last5_venue_ppg",
                "last5_venue_matches_available",
            ]
        ]
        .copy()
        .rename(
            columns={
                "last5_venue_ppg":
                    "home_last5_home_ppg",

                "last5_venue_matches_available":
                    "home_venue_matches_available",
            }
        )
    )

    away_rows = (
        team_history[
            ~team_history["is_home"]
        ][
            [
                "fixture_id",
                "last5_venue_ppg",
                "last5_venue_matches_available",
            ]
        ]
        .copy()
        .rename(
            columns={
                "last5_venue_ppg":
                    "away_last5_away_ppg",

                "last5_venue_matches_available":
                    "away_venue_matches_available",
            }
        )
    )

    venue_features = home_rows.merge(
        away_rows,
        on="fixture_id",
        how="inner",
        validate="one_to_one",
    )

    venue_features[
        "venue_last5_ppg_diff"
    ] = (
        venue_features[
            "home_last5_home_ppg"
        ]
        -
        venue_features[
            "away_last5_away_ppg"
        ]
    )

    venue_features[
        "venue_history_min"
    ] = (
        venue_features[
            [
                "home_venue_matches_available",
                "away_venue_matches_available",
            ]
        ]
        .min(axis=1)
    )

    return venue_features


def evaluate_model(
    train,
    validation,
    features,
):
    model = build_model()

    model.fit(
        train[features],
        train[TARGET],
    )

    probabilities = model.predict_proba(
        validation[features]
    )

    predictions = model.predict(
        validation[features]
    )

    classes = model.named_steps[
        "model"
    ].classes_

    return {
        "log_loss": log_loss(
            validation[TARGET],
            probabilities,
            labels=classes,
        ),

        "accuracy": accuracy_score(
            validation[TARGET],
            predictions,
        ),
    }


if __name__ == "__main__":
    dataset = build_model_dataset()

    venue_features = (
        build_venue_form_features()
    )

    dataset = dataset.merge(
        venue_features,
        on="fixture_id",
        how="left",
        validate="one_to_one",
    )

    # Development years only.
    dataset = dataset[
        dataset["season"].between(
            2021,
            2024,
        )
    ].copy()

    print(
        "=== VENUE FORM FEATURE AUDIT ==="
    )

    print(
        "Rows:",
        len(dataset)
    )

    print(
        "Missing venue PPG diff:",
        dataset[
            "venue_last5_ppg_diff"
        ].isna().sum()
    )

    print(
        "\nMissing by season:"
    )

    print(
        dataset
        .assign(
            venue_missing=
                dataset[
                    "venue_last5_ppg_diff"
                ].isna()
        )
        .groupby("season")[
            "venue_missing"
        ]
        .sum()
    )

    print(
        "\nVenue PPG diff range:"
    )

    print(
        dataset[
            "venue_last5_ppg_diff"
        ].agg(
            [
                "min",
                "median",
                "max",
            ]
        )
    )

    print(
        "\n=== WALK-FORWARD: "
        "ELO VS ELO + VENUE FORM ==="
    )

    results = []

    for fold in FOLDS:
        train = dataset[
            dataset["season"].between(
                fold["train_start"],
                fold["train_end"],
            )
        ].copy()

        validation = dataset[
            dataset["season"]
            == fold[
                "validation_season"
            ]
        ].copy()

        elo_result = evaluate_model(
            train,
            validation,
            FEATURE_SETS[
                "Elo only"
            ],
        )

        venue_result = evaluate_model(
            train,
            validation,
            FEATURE_SETS[
                "Elo + Venue Form"
            ],
        )

        change = (
            venue_result["log_loss"]
            -
            elo_result["log_loss"]
        )

        results.append(
            {
                "fold":
                    fold["name"],

                "validation_season":
                    fold[
                        "validation_season"
                    ],

                "elo_log_loss":
                    elo_result[
                        "log_loss"
                    ],

                "elo_venue_log_loss":
                    venue_result[
                        "log_loss"
                    ],

                "log_loss_change":
                    change,

                "elo_accuracy":
                    elo_result[
                        "accuracy"
                    ],

                "elo_venue_accuracy":
                    venue_result[
                        "accuracy"
                    ],

                "validation_missing_venue":
                    validation[
                        "venue_last5_ppg_diff"
                    ].isna().sum(),
            }
        )

    results_df = pd.DataFrame(
        results
    )

    print(
        "\n=== RESULTS ==="
    )

    print(
        results_df.to_string(
            index=False,
            formatters={
                "elo_log_loss":
                    lambda x: f"{x:.4f}",

                "elo_venue_log_loss":
                    lambda x: f"{x:.4f}",

                "log_loss_change":
                    lambda x: f"{x:+.4f}",

                "elo_accuracy":
                    lambda x: f"{x:.4f}",

                "elo_venue_accuracy":
                    lambda x: f"{x:.4f}",
            },
        )
    )

    print(
        "\n=== MEAN PERFORMANCE ==="
    )

    print(
        "Elo mean Log Loss:",
        round(
            results_df[
                "elo_log_loss"
            ].mean(),
            4,
        )
    )

    print(
        "Elo + Venue mean Log Loss:",
        round(
            results_df[
                "elo_venue_log_loss"
            ].mean(),
            4,
        )
    )

    print(
        "Mean change:",
        round(
            results_df[
                "log_loss_change"
            ].mean(),
            4,
        )
    )