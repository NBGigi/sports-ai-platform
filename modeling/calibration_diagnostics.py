import pandas as pd

from sklearn.calibration import calibration_curve
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    brier_score_loss,
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


def print_class_calibration(
    y_true,
    probabilities,
    classes,
):
    for class_index, class_name in enumerate(classes):
        binary_target = (
            y_true == class_name
        ).astype(int)

        class_probabilities = probabilities[
            :,
            class_index
        ]

        brier = brier_score_loss(
            binary_target,
            class_probabilities,
        )

        fraction_positive, mean_predicted_value = (
            calibration_curve(
                binary_target,
                class_probabilities,
                n_bins=5,
                strategy="quantile",
            )
        )

        print(
            f"\n=== CLASS {class_name} ==="
        )

        print(
            "Brier Score:",
            round(
                brier,
                4,
            )
        )

        calibration_table = pd.DataFrame(
            {
                "mean_predicted_probability":
                    mean_predicted_value,
                "actual_frequency":
                    fraction_positive,
            }
        )

        calibration_table[
            "calibration_error"
        ] = (
            calibration_table[
                "actual_frequency"
            ]
            -
            calibration_table[
                "mean_predicted_probability"
            ]
        )

        print(
            calibration_table.to_string(
                index=False,
                formatters={
                    "mean_predicted_probability":
                        lambda x: f"{x:.3f}",
                    "actual_frequency":
                        lambda x: f"{x:.3f}",
                    "calibration_error":
                        lambda x: f"{x:+.3f}",
                },
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

    X_validation = validation[
        FEATURES
    ]

    y_validation = validation[
        TARGET
    ]

    probabilities = model.predict_proba(
        X_validation
    )

    classes = model.named_steps[
        "model"
    ].classes_

    print(
        "=== ELO MODEL CALIBRATION DIAGNOSTICS ==="
    )

    print(
        "Validation rows:",
        len(validation)
    )

    print(
        "Classes:",
        classes
    )

    print(
        "\nValidation Log Loss:",
        round(
            log_loss(
                y_validation,
                probabilities,
                labels=classes,
            ),
            4,
        )
    )

    print_class_calibration(
        y_validation,
        probabilities,
        classes,
    )