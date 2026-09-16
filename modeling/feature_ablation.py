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

from modeling.dataset_split import (
    build_model_dataset,
    split_dataset_by_time,
)


TARGET = "label_1x2"


FEATURE_SETS = {
    "Elo only": [
        "elo_diff",
    ],

    "Elo + Form": [
        "elo_diff",

        "last5_ppg_diff",
        "last10_ppg_diff",

        "last5_history_min",
        "last10_history_min",
    ],

    "Elo + Goals": [
        "elo_diff",

        "last5_goals_for_avg_diff",
        "last10_goals_for_avg_diff",

        "last5_goals_against_avg_diff",
        "last10_goals_against_avg_diff",

        "last5_history_min",
        "last10_history_min",
    ],

    "Elo + Shots": [
        "elo_diff",

        "last5_shots_on_target_for_avg_diff",
        "last10_shots_on_target_for_avg_diff",

        "last5_shots_on_target_against_avg_diff",
        "last10_shots_on_target_against_avg_diff",

        "last5_history_min",
        "last10_history_min",
    ],

    "Elo + Form + Goals": [
        "elo_diff",

        "last5_ppg_diff",
        "last10_ppg_diff",

        "last5_goals_for_avg_diff",
        "last10_goals_for_avg_diff",

        "last5_goals_against_avg_diff",
        "last10_goals_against_avg_diff",

        "last5_history_min",
        "last10_history_min",
    ],

    "Elo + Goals + Shots": [
        "elo_diff",

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
    ],

    "Elo + All Rolling": [
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
    ],
}


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


def evaluate_model(
    model,
    dataset,
    features,
):
    X = dataset[features]
    y = dataset[TARGET]

    probabilities = model.predict_proba(X)
    predictions = model.predict(X)

    classes = model.named_steps[
        "model"
    ].classes_

    return {
        "log_loss": log_loss(
            y,
            probabilities,
            labels=classes,
        ),
        "accuracy": accuracy_score(
            y,
            predictions,
        ),
    }


def calculate_naive_baseline(
    train,
    validation,
):
    train_distribution = (
        train[TARGET]
        .value_counts(normalize=True)
    )

    classes = sorted(
        train[TARGET].unique()
    )

    probabilities = np.array(
        [
            train_distribution[label]
            for label in classes
        ]
    )

    validation_probabilities = np.tile(
        probabilities,
        (
            len(validation),
            1,
        ),
    )

    majority_class = train_distribution.idxmax()

    validation_predictions = np.full(
        len(validation),
        majority_class,
    )

    return {
        "validation_log_loss": log_loss(
            validation[TARGET],
            validation_probabilities,
            labels=classes,
        ),
        "validation_accuracy": accuracy_score(
            validation[TARGET],
            validation_predictions,
        ),
    }


if __name__ == "__main__":
    dataset = build_model_dataset()

    splits = split_dataset_by_time(
        dataset
    )

    train = splits["train"]
    validation = splits["validation"]

    print(
        "=== FEATURE ABLATION EXPERIMENT ==="
    )

    print(
        "Train rows:",
        len(train)
    )

    print(
        "Validation rows:",
        len(validation)
    )

    baseline = calculate_naive_baseline(
        train,
        validation,
    )

    print(
        "\nNaive baseline:"
    )

    print(
        "Validation Log Loss:",
        round(
            baseline[
                "validation_log_loss"
            ],
            4,
        )
    )

    print(
        "Validation Accuracy:",
        round(
            baseline[
                "validation_accuracy"
            ],
            4,
        )
    )

    results = []

    for model_name, features in FEATURE_SETS.items():
        model = build_model()

        X_train = train[features]
        y_train = train[TARGET]

        model.fit(
            X_train,
            y_train,
        )

        train_metrics = evaluate_model(
            model,
            train,
            features,
        )

        validation_metrics = evaluate_model(
            model,
            validation,
            features,
        )

        results.append(
            {
                "model": model_name,
                "n_features": len(features),
                "train_log_loss": (
                    train_metrics[
                        "log_loss"
                    ]
                ),
                "validation_log_loss": (
                    validation_metrics[
                        "log_loss"
                    ]
                ),
                "train_accuracy": (
                    train_metrics[
                        "accuracy"
                    ]
                ),
                "validation_accuracy": (
                    validation_metrics[
                        "accuracy"
                    ]
                ),
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

    ranked_results = (
        results_df
        .sort_values(
            "validation_log_loss"
        )
        .reset_index(drop=True)
    )

    print(
        "\n=== RANKED BY VALIDATION LOG LOSS ==="
    )

    print(
        ranked_results[
            [
                "model",
                "validation_log_loss",
                "validation_accuracy",
            ]
        ].to_string(
            index=False,
            formatters={
                "validation_log_loss":
                    lambda x: f"{x:.4f}",
                "validation_accuracy":
                    lambda x: f"{x:.4f}",
            },
        )
    )