import pandas as pd

from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    log_loss,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from xgboost import XGBClassifier

from modeling.dataset_split import (
    build_model_dataset,
)

from modeling.feature_ablation import (
    FEATURE_SETS as ROLLING_FEATURE_SETS,
)

from modeling.squad_value_walk_forward import (
    add_squad_value_features,
)

from modeling.venue_form_walk_forward import (
    build_venue_form_features,
)


TARGET = "label_1x2"

LABEL_MAP = {
    "A": 0,
    "D": 1,
    "H": 2,
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


ELO_FEATURES = [
    "elo_diff",
]


FULL_FEATURES = (
    ROLLING_FEATURE_SETS[
        "Elo + All Rolling"
    ]
    +
    [
        "squad_value_log_ratio",
        "venue_last5_ppg_diff",
        "venue_history_min",
    ]
)


def build_logistic_model():
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


def build_xgboost_model():
    return XGBClassifier(
        objective="multi:softprob",
        num_class=3,
        eval_metric="mlogloss",

        n_estimators=200,
        learning_rate=0.03,
        max_depth=3,

        min_child_weight=5,
        subsample=0.8,
        colsample_bytree=0.8,

        reg_lambda=2.0,

        random_state=42,
        n_jobs=-1,
    )


def build_full_dataset():
    dataset = build_model_dataset()

    # Adds squad_value_log_ratio.
    # This function also limits the data
    # to development seasons 2021-2024.
    dataset = add_squad_value_features(
        dataset
    )

    venue_features = (
        build_venue_form_features()
    )

    venue_features = venue_features[
        [
            "fixture_id",
            "venue_last5_ppg_diff",
            "venue_history_min",
        ]
    ].copy()

    dataset = dataset.merge(
        venue_features,
        on="fixture_id",
        how="left",
        validate="one_to_one",
    )

    return dataset


def evaluate_model(
    model,
    train,
    validation,
    features,
):
    X_train = train[features]
    X_validation = validation[features]

    y_train = (
        train[TARGET]
        .map(LABEL_MAP)
    )

    y_validation = (
        validation[TARGET]
        .map(LABEL_MAP)
    )

    model.fit(
        X_train,
        y_train,
    )

    train_probabilities = (
        model.predict_proba(
            X_train
        )
    )

    validation_probabilities = (
        model.predict_proba(
            X_validation
        )
    )

    train_predictions = model.predict(
        X_train
    )

    validation_predictions = model.predict(
        X_validation
    )

    return {
        "train_log_loss":
            log_loss(
                y_train,
                train_probabilities,
                labels=[0, 1, 2],
            ),

        "validation_log_loss":
            log_loss(
                y_validation,
                validation_probabilities,
                labels=[0, 1, 2],
            ),

        "train_accuracy":
            accuracy_score(
                y_train,
                train_predictions,
            ),

        "validation_accuracy":
            accuracy_score(
                y_validation,
                validation_predictions,
            ),
    }


if __name__ == "__main__":
    dataset = build_full_dataset()

    print(
        "\n=== MODEL SELECTION DATASET AUDIT ==="
    )

    print(
        "Rows:",
        len(dataset)
    )

    print(
        "Seasons:"
    )

    print(
        dataset[
            "season"
        ]
        .value_counts()
        .sort_index()
    )

    print(
        "\nFull feature count:",
        len(FULL_FEATURES)
    )

    print(
        "\nMissing values in full feature set:"
    )

    print(
        dataset[
            FULL_FEATURES
        ]
        .isna()
        .sum()
    )

    experiments = [
        {
            "name":
                "Logistic — Elo",

            "model_builder":
                build_logistic_model,

            "features":
                ELO_FEATURES,
        },

        {
            "name":
                "Logistic — Full",

            "model_builder":
                build_logistic_model,

            "features":
                FULL_FEATURES,
        },

        {
            "name":
                "XGBoost — Elo",

            "model_builder":
                build_xgboost_model,

            "features":
                ELO_FEATURES,
        },

        {
            "name":
                "XGBoost — Full",

            "model_builder":
                build_xgboost_model,

            "features":
                FULL_FEATURES,
        },
    ]

    results = []

    print(
        "\n=== WALK-FORWARD MODEL SELECTION ==="
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

        print(
            f"\n--- {fold['name']} ---"
        )

        print(
            "Train seasons:",
            f"{fold['train_start']}"
            f"-{fold['train_end']}"
        )

        print(
            "Validation season:",
            fold["validation_season"]
        )

        for experiment in experiments:
            model = (
                experiment[
                    "model_builder"
                ]()
            )

            metrics = evaluate_model(
                model,
                train,
                validation,
                experiment["features"],
            )

            print(
                experiment["name"],
                "| Train LL:",
                round(
                    metrics[
                        "train_log_loss"
                    ],
                    4,
                ),
                "| Validation LL:",
                round(
                    metrics[
                        "validation_log_loss"
                    ],
                    4,
                ),
                "| Validation Acc:",
                round(
                    metrics[
                        "validation_accuracy"
                    ],
                    4,
                ),
            )

            results.append(
                {
                    "fold":
                        fold["name"],

                    "validation_season":
                        fold[
                            "validation_season"
                        ],

                    "model":
                        experiment["name"],

                    "n_features":
                        len(
                            experiment[
                                "features"
                            ]
                        ),

                    **metrics,
                }
            )

    results_df = pd.DataFrame(
        results
    )

    print(
        "\n=== ALL RESULTS ==="
    )

    print(
        results_df.to_string(
            index=False,
            formatters={
                "train_log_loss":
                    lambda x: f"{x:.4f}",

                "validation_log_loss":
                    lambda x: f"{x:.4f}",

                "train_accuracy":
                    lambda x: f"{x:.4f}",

                "validation_accuracy":
                    lambda x: f"{x:.4f}",
            },
        )
    )

    summary = (
        results_df
        .groupby(
            [
                "model",
                "n_features",
            ],
            as_index=False,
        )
        .agg(
            mean_train_log_loss=(
                "train_log_loss",
                "mean",
            ),

            mean_validation_log_loss=(
                "validation_log_loss",
                "mean",
            ),

            mean_validation_accuracy=(
                "validation_accuracy",
                "mean",
            ),
        )
        .sort_values(
            "mean_validation_log_loss"
        )
        .reset_index(drop=True)
    )

    print(
        "\n=== MODEL SELECTION SUMMARY ==="
    )

    print(
        summary.to_string(
            index=False,
            formatters={
                "mean_train_log_loss":
                    lambda x: f"{x:.4f}",

                "mean_validation_log_loss":
                    lambda x: f"{x:.4f}",

                "mean_validation_accuracy":
                    lambda x: f"{x:.4f}",
            },
        )
    )