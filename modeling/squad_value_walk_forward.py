import numpy as np
import pandas as pd

from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    log_loss,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from features.squad_value import (
    get_fixture_squad_value_features,
)

from modeling.dataset_split import (
    build_model_dataset,
)


TARGET = "label_1x2"


FEATURE_SETS = {
    "Elo only": [
        "elo_diff",
    ],

    "Elo + Squad Value": [
        "elo_diff",
        "squad_value_log_ratio",
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


def add_squad_value_features(
    dataset,
):
    development = dataset[
        dataset["season"].between(
            2021,
            2024,
        )
    ].copy()

    squad_rows = []

    total = len(development)

    print(
        "Building squad-value features..."
    )

    for number, row in enumerate(
        development.itertuples(),
        start=1,
    ):
        features = (
            get_fixture_squad_value_features(
                row.fixture_id
            )
        )

        both_reliable = (
            features[
                "home_squad_value_is_reliable"
            ]
            and
            features[
                "away_squad_value_is_reliable"
            ]
        )

        home_value = features[
            "home_squad_value"
        ]

        away_value = features[
            "away_squad_value"
        ]

        if (
            both_reliable
            and home_value > 0
            and away_value > 0
        ):
            log_ratio = np.log(
                home_value
                /
                away_value
            )

        else:
            log_ratio = np.nan

        squad_rows.append(
            {
                "fixture_id":
                    row.fixture_id,

                "squad_value_log_ratio":
                    log_ratio,

                "squad_value_both_reliable":
                    both_reliable,
            }
        )

        if (
            number % 100 == 0
            or number == total
        ):
            print(
                f"Processed {number}/{total}"
            )

    squad_features = pd.DataFrame(
        squad_rows
    )

    development = development.merge(
        squad_features,
        on="fixture_id",
        how="left",
        validate="one_to_one",
    )

    return development


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

    dataset = add_squad_value_features(
        dataset
    )

    print(
        "\n=== SQUAD VALUE FEATURE CHECK ==="
    )

    print(
        "Rows:",
        len(dataset)
    )

    print(
        "Reliable:",
        dataset[
            "squad_value_both_reliable"
        ].sum()
    )

    print(
        "Missing log ratio:",
        dataset[
            "squad_value_log_ratio"
        ].isna().sum()
    )

    print(
        "Log-ratio range:"
    )

    print(
        dataset[
            "squad_value_log_ratio"
        ].agg(
            [
                "min",
                "median",
                "max",
            ]
        )
    )

    results = []

    print(
        "\n=== WALK-FORWARD: "
        "ELO VS ELO + SQUAD VALUE ==="
    )

    for fold in FOLDS:
        train = dataset[
            dataset["season"].between(
                fold["train_start"],
                fold["train_end"],
            )
        ].copy()

        validation = dataset[
            dataset["season"]
            == fold["validation_season"]
        ].copy()

        elo_result = evaluate_model(
            train,
            validation,
            FEATURE_SETS[
                "Elo only"
            ],
        )

        squad_result = evaluate_model(
            train,
            validation,
            FEATURE_SETS[
                "Elo + Squad Value"
            ],
        )

        log_loss_change = (
            squad_result["log_loss"]
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

                "elo_squad_log_loss":
                    squad_result[
                        "log_loss"
                    ],

                "log_loss_change":
                    log_loss_change,

                "elo_accuracy":
                    elo_result[
                        "accuracy"
                    ],

                "elo_squad_accuracy":
                    squad_result[
                        "accuracy"
                    ],

                "validation_missing_squad":
                    validation[
                        "squad_value_log_ratio"
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

                "elo_squad_log_loss":
                    lambda x: f"{x:.4f}",

                "log_loss_change":
                    lambda x: f"{x:+.4f}",

                "elo_accuracy":
                    lambda x: f"{x:.4f}",

                "elo_squad_accuracy":
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
        "Elo + Squad mean Log Loss:",
        round(
            results_df[
                "elo_squad_log_loss"
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