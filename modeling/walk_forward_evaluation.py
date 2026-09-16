import pandas as pd

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    log_loss,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from modeling.dataset_split import (
    build_model_dataset,
)


FEATURES = [
    "elo_diff",
]

TARGET = "label_1x2"


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


def evaluate_fold(
    dataset,
    fold,
):
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

    model = build_model()

    model.fit(
        train[FEATURES],
        train[TARGET],
    )

    probabilities = model.predict_proba(
        validation[FEATURES]
    )

    predictions = model.predict(
        validation[FEATURES]
    )

    classes = model.named_steps[
        "model"
    ].classes_

    return {
        "fold": fold["name"],
        "train_seasons":
            f"{fold['train_start']}-{fold['train_end']}",
        "validation_season":
            fold["validation_season"],
        "train_rows":
            len(train),
        "validation_rows":
            len(validation),
        "log_loss":
            log_loss(
                validation[TARGET],
                probabilities,
                labels=classes,
            ),
        "accuracy":
            accuracy_score(
                validation[TARGET],
                predictions,
            ),
    }


if __name__ == "__main__":
    dataset = build_model_dataset()

    results = []

    print(
        "=== WALK-FORWARD ELO BASELINE ==="
    )

    for fold in FOLDS:
        result = evaluate_fold(
            dataset,
            fold,
        )

        results.append(
            result
        )

        print(
            f"\n=== {result['fold']} ==="
        )

        print(
            "Train seasons:",
            result["train_seasons"]
        )

        print(
            "Validation season:",
            result["validation_season"]
        )

        print(
            "Train rows:",
            result["train_rows"]
        )

        print(
            "Validation rows:",
            result["validation_rows"]
        )

        print(
            "Log Loss:",
            round(
                result["log_loss"],
                4,
            )
        )

        print(
            "Accuracy:",
            round(
                result["accuracy"],
                4,
            )
        )

    results_df = pd.DataFrame(
        results
    )

    print(
        "\n=== WALK-FORWARD SUMMARY ==="
    )

    print(
        results_df.to_string(
            index=False,
            formatters={
                "log_loss":
                    lambda x: f"{x:.4f}",
                "accuracy":
                    lambda x: f"{x:.4f}",
            },
        )
    )

    print(
        "\nMean Log Loss:",
        round(
            results_df[
                "log_loss"
            ].mean(),
            4,
        )
    )

    print(
        "Mean Accuracy:",
        round(
            results_df[
                "accuracy"
            ].mean(),
            4,
        )
    )