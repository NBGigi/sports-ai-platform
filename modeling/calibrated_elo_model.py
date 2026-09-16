from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
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


def build_base_model():
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

    classes = model.classes_

    logloss = log_loss(
        y,
        probabilities,
        labels=classes,
    )

    accuracy = accuracy_score(
        y,
        predictions,
    )

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
            logloss,
            4,
        )
    )

    print(
        "Accuracy:",
        round(
            accuracy,
            4,
        )
    )

    return {
        "log_loss": logloss,
        "accuracy": accuracy,
        "probabilities": probabilities,
    }


if __name__ == "__main__":
    dataset = build_model_dataset()

    splits = split_dataset_by_time(
        dataset
    )

    train = splits["train"]
    calibration = splits["validation"]
    test = splits["test"]

    print(
        "=== CALIBRATED ELO MODEL ==="
    )

    print(
        "Train rows:",
        len(train)
    )

    print(
        "Calibration rows:",
        len(calibration)
    )

    print(
        "Test rows:",
        len(test)
    )

    # -------------------------
    # 1. Train base Elo model
    # -------------------------

    base_model = build_base_model()

    base_model.fit(
        train[FEATURES],
        train[TARGET],
    )

    print(
        "\nBase model classes:",
        base_model.classes_
    )

    # -------------------------
    # 2. Freeze base model
    # -------------------------

    frozen_base_model = FrozenEstimator(
        base_model
    )

    # -------------------------
    # 3. Learn calibration
    #    using 2024 only
    # -------------------------

    calibrated_model = (
        CalibratedClassifierCV(
            estimator=frozen_base_model,
            method="sigmoid",
        )
    )

    calibrated_model.fit(
        calibration[FEATURES],
        calibration[TARGET],
    )

    # -------------------------
    # 4. Open TEST: 2025
    # -------------------------

    raw_results = evaluate_model(
        base_model,
        test,
        "TEST 2025 — RAW ELO",
    )

    calibrated_results = evaluate_model(
        calibrated_model,
        test,
        "TEST 2025 — CALIBRATED ELO",
    )

    # -------------------------
    # 5. Comparison
    # -------------------------

    log_loss_change = (
        calibrated_results["log_loss"]
        -
        raw_results["log_loss"]
    )

    print(
        "\n=== CALIBRATION EFFECT ==="
    )

    print(
        "Raw Log Loss:",
        round(
            raw_results["log_loss"],
            4,
        )
    )

    print(
        "Calibrated Log Loss:",
        round(
            calibrated_results[
                "log_loss"
            ],
            4,
        )
    )

    print(
        "Change:",
        round(
            log_loss_change,
            4,
        )
    )