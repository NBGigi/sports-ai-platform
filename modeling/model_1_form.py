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


FEATURES = [
    "elo_diff",

    "last5_ppg_diff",
    "last10_ppg_diff",

    "last5_history_min",
    "last10_history_min",
]

TARGET = "label_1x2"


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


if __name__ == "__main__":
    dataset = build_model_dataset()

    splits = split_dataset_by_time(
        dataset
    )

    train = splits["train"]
    validation = splits["validation"]

    model = build_model()

    X_train = train[FEATURES]
    y_train = train[TARGET]

    model.fit(
        X_train,
        y_train,
    )

    print(
        "Features:",
        FEATURES
    )

    print(
        "Classes:",
        model.named_steps[
            "model"
        ].classes_
    )

    print(
        "\nMissing values in TRAIN:"
    )

    print(
        X_train.isna().sum()
    )

    evaluate_model(
        model,
        train,
        "TRAIN — ELO + FORM",
    )

    evaluate_model(
        model,
        validation,
        "VALIDATION — ELO + FORM",
    )