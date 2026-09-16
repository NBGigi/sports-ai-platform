import numpy as np

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


FEATURES = [
    "elo_diff",
]

TARGET = "label_1x2"


def build_elo_model():
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


def evaluate_model(
    model,
    dataset,
    name,
):
    X = dataset[FEATURES]
    y = dataset[TARGET]

    probabilities = model.predict_proba(X)
    predictions = model.predict(X)

    classes = model.named_steps[
        "model"
    ].classes_

    print(
        f"\n=== {name} ==="
    )

    print(
        "Rows:",
        len(dataset)
    )

    print(
        "Log Loss:",
        round(
            log_loss(
                y,
                probabilities,
                labels=classes,
            ),
            4,
        )
    )

    print(
        "Accuracy:",
        round(
            accuracy_score(
                y,
                predictions,
            ),
            4,
        )
    )

    return probabilities


def evaluate_naive_baseline(
    train,
    validation,
):
    train_distribution = (
        train[TARGET]
        .value_counts(
            normalize=True
        )
    )

    classes = np.array(
        sorted(
            train[TARGET].unique()
        )
    )

    class_probabilities = np.array(
        [
            train_distribution[
                label
            ]
            for label in classes
        ]
    )

    probabilities = np.tile(
        class_probabilities,
        (
            len(validation),
            1,
        ),
    )

    print(
        "\n=== NAIVE BASELINE ==="
    )

    print(
        "Probabilities:",
        dict(
            zip(
                classes,
                class_probabilities,
            )
        )
    )

    print(
        "Validation Log Loss:",
        round(
            log_loss(
                validation[TARGET],
                probabilities,
                labels=classes,
            ),
            4,
        )
    )


if __name__ == "__main__":
    dataset = build_model_dataset()

    splits = split_dataset_by_time(
        dataset
    )

    train = splits["train"]
    validation = splits["validation"]

    model = build_elo_model()

    X_train = train[FEATURES]
    y_train = train[TARGET]

    model.fit(
        X_train,
        y_train,
    )

    print(
        "Classes:",
        model.named_steps[
            "model"
        ].classes_
    )

    evaluate_naive_baseline(
        train,
        validation,
    )

    evaluate_model(
        model,
        train,
        "TRAIN — ELO MODEL",
    )

    validation_probabilities = (
        evaluate_model(
            model,
            validation,
            "VALIDATION — ELO MODEL",
        )
    )

    classes = model.named_steps[
        "model"
    ].classes_

    print(
        "\n=== SAMPLE VALIDATION PREDICTIONS ==="
    )

    sample = validation[
        [
            "date",
            "home_team_name",
            "away_team_name",
            "elo_diff",
            "label_1x2",
        ]
    ].head(10).copy()

    for index, label in enumerate(
        classes
    ):
        sample[
            f"prob_{label}"
        ] = (
            validation_probabilities[
                :10,
                index
            ]
        )

    print(
        sample.to_string(
            index=False
        )
    )