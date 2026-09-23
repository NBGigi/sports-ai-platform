import json
from pathlib import Path

import joblib
import pandas as pd

from sklearn.calibration import (
    CalibratedClassifierCV,
)
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import (
    LogisticRegression,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    StandardScaler,
)

from modeling.dataset_split import (
    build_model_dataset,
)


FEATURES = [
    "elo_diff",
]

TARGET = "label_1x2"

BASE_TRAIN_START = 2021
BASE_TRAIN_END = 2024

CALIBRATION_SEASON = 2025
HOLDOUT_SEASON = 2026


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

ARTIFACT_DIR = (
    PROJECT_ROOT
    / "model_artifacts"
)

MODEL_PATH = (
    ARTIFACT_DIR
    / "football_model_v1.joblib"
)

METADATA_PATH = (
    ARTIFACT_DIR
    / "football_model_v1_metadata.json"
)


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


def train_final_model(
    dataset,
):
    base_train = dataset[
        dataset["season"].between(
            BASE_TRAIN_START,
            BASE_TRAIN_END,
        )
    ].copy()

    calibration = dataset[
        dataset["season"]
        == CALIBRATION_SEASON
    ].copy()

    holdout = dataset[
        dataset["season"]
        == HOLDOUT_SEASON
    ].copy()

    if base_train.empty:
        raise ValueError(
            "Base training set is empty."
        )

    if calibration.empty:
        raise ValueError(
            "Calibration set is empty."
        )

    base_model = build_base_model()

    base_model.fit(
        base_train[FEATURES],
        base_train[TARGET],
    )

    frozen_base_model = FrozenEstimator(
        base_model
    )

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

    return (
        calibrated_model,
        base_train,
        calibration,
        holdout,
    )


def save_model(
    model,
    base_train,
    calibration,
    holdout,
):
    ARTIFACT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        model,
        MODEL_PATH,
    )

    metadata = {
        "model_version":
            "v1",

        "model_family":
            "Multiclass Logistic Regression",

        "features":
            FEATURES,

        "target":
            TARGET,

        "base_training_seasons": [
            BASE_TRAIN_START,
            BASE_TRAIN_END,
        ],

        "calibration_method":
            "sigmoid",

        "calibration_season":
            CALIBRATION_SEASON,

        "holdout_season":
            HOLDOUT_SEASON,

        "base_training_rows":
            len(base_train),

        "calibration_rows":
            len(calibration),

        "holdout_rows_available":
            len(holdout),

        "classes":
            model.classes_.tolist(),

        "model_selection_mean_log_loss":
            0.9700,

        "holdout_evaluated":
            False,
    }

    with open(
        METADATA_PATH,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            metadata,
            file,
            indent=4,
        )

    return metadata


def load_model():
    return joblib.load(
        MODEL_PATH
    )


def predict_from_elo_diff(
    model,
    elo_diff,
):
    features = pd.DataFrame(
        {
            "elo_diff": [
                elo_diff
            ],
        }
    )

    probabilities = (
        model.predict_proba(
            features
        )[0]
    )

    return {
        class_name: float(probability)
        for class_name, probability
        in zip(
            model.classes_,
            probabilities,
        )
    }


def print_sample_predictions(
    model,
):
    print(
        "\n=== SAMPLE ELO-DIFF PREDICTIONS ==="
    )

    for elo_diff in [
        -200,
        -100,
        0,
        100,
        200,
    ]:
        probabilities = (
            predict_from_elo_diff(
                model,
                elo_diff,
            )
        )

        total_probability = sum(
            probabilities.values()
        )

        print(
            f"\nElo diff: {elo_diff:+}"
        )

        print(
            "Away:",
            round(
                probabilities["A"],
                4,
            )
        )

        print(
            "Draw:",
            round(
                probabilities["D"],
                4,
            )
        )

        print(
            "Home:",
            round(
                probabilities["H"],
                4,
            )
        )

        print(
            "Sum:",
            round(
                total_probability,
                6,
            )
        )


if __name__ == "__main__":
    dataset = build_model_dataset()

    (
        model,
        base_train,
        calibration,
        holdout,
    ) = train_final_model(
        dataset
    )

    print(
        "=== FINAL FOOTBALL MODEL V1 ==="
    )

    print(
        "Features:",
        FEATURES
    )

    print(
        "Base training seasons:",
        f"{BASE_TRAIN_START}-"
        f"{BASE_TRAIN_END}"
    )

    print(
        "Base training rows:",
        len(base_train)
    )

    print(
        "Calibration season:",
        CALIBRATION_SEASON
    )

    print(
        "Calibration rows:",
        len(calibration)
    )

    print(
        "Holdout season:",
        HOLDOUT_SEASON
    )

    print(
        "Holdout rows available:",
        len(holdout)
    )

    print(
        "IMPORTANT: Holdout was NOT evaluated."
    )

    print(
        "Classes:",
        model.classes_
    )

    metadata = save_model(
        model,
        base_train,
        calibration,
        holdout,
    )

    print(
        "\nModel saved to:"
    )

    print(
        MODEL_PATH
    )

    print(
        "\nMetadata saved to:"
    )

    print(
        METADATA_PATH
    )

    print_sample_predictions(
        model
    )

    # ------------------------------------
    # Serialization round-trip check
    # ------------------------------------

    loaded_model = load_model()

    original_prediction = (
        predict_from_elo_diff(
            model,
            100,
        )
    )

    loaded_prediction = (
        predict_from_elo_diff(
            loaded_model,
            100,
        )
    )

    max_difference = max(
        abs(
            original_prediction[label]
            -
            loaded_prediction[label]
        )
        for label in model.classes_
    )

    print(
        "\n=== SAVE / LOAD CHECK ==="
    )

    print(
        "Maximum probability difference:",
        max_difference
    )

    print(
        "Artifact round-trip valid:",
        max_difference < 1e-12
    )