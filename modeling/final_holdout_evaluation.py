import numpy as np

from sklearn.metrics import (
    accuracy_score,
    log_loss,
)

from modeling.dataset_split import (
    build_model_dataset,
)

from modeling.final_elo_model import (
    FEATURES,
    HOLDOUT_SEASON,
    TARGET,
    load_model,
)


EXPECTED_HOLDOUT_ROWS = 50


def multiclass_brier_score(
    y_true,
    probabilities,
    classes,
):
    one_hot = np.zeros_like(
        probabilities,
        dtype=float,
    )

    class_to_index = {
        class_name: index
        for index, class_name
        in enumerate(classes)
    }

    for row_index, label in enumerate(
        y_true
    ):
        one_hot[
            row_index,
            class_to_index[label],
        ] = 1.0

    squared_error = (
        probabilities
        - one_hot
    ) ** 2

    return float(
        squared_error
        .sum(axis=1)
        .mean()
    )


def evaluate_holdout():
    dataset = build_model_dataset()

    holdout = dataset[
        dataset["season"]
        == HOLDOUT_SEASON
    ].copy()

    print(
        "=== FINAL HOLDOUT EVALUATION ==="
    )

    print(
        "Season:",
        HOLDOUT_SEASON,
    )

    print(
        "Rows:",
        len(holdout),
    )

    if len(holdout) != EXPECTED_HOLDOUT_ROWS:
        raise ValueError(
            "Holdout size changed. "
            f"Expected {EXPECTED_HOLDOUT_ROWS}, "
            f"found {len(holdout)}."
        )

    if holdout[
        FEATURES
    ].isna().any().any():
        raise ValueError(
            "Holdout contains missing "
            "model features."
        )

    if holdout[
        "fixture_id"
    ].duplicated().any():
        raise ValueError(
            "Holdout contains duplicate "
            "fixture IDs."
        )

    model = load_model()

    probabilities = (
        model.predict_proba(
            holdout[FEATURES]
        )
    )

    predicted_labels = (
        model.predict(
            holdout[FEATURES]
        )
    )

    actual_labels = (
        holdout[TARGET]
        .to_numpy()
    )

    final_log_loss = log_loss(
        actual_labels,
        probabilities,
        labels=model.classes_,
    )

    final_accuracy = accuracy_score(
        actual_labels,
        predicted_labels,
    )

    final_brier = (
        multiclass_brier_score(
            actual_labels,
            probabilities,
            model.classes_,
        )
    )

    print(
        "\nDate range:"
    )

    print(
        holdout["date"].min(),
        "->",
        holdout["date"].max(),
    )

    print(
        "\nLabel distribution:"
    )

    print(
        holdout[TARGET]
        .value_counts()
    )

    print(
        "\nModel classes:",
        model.classes_,
    )

    print(
        "\n=== FINAL METRICS ==="
    )

    print(
        "Log Loss:",
        round(
            final_log_loss,
            4,
        ),
    )

    print(
        "Accuracy:",
        f"{final_accuracy * 100:.2f}%",
    )

    print(
        "Multiclass Brier Score:",
        round(
            final_brier,
            4,
        ),
    )

    print(
        "\nIMPORTANT:"
    )

    print(
        "This is the final one-time "
        "evaluation of model v1."
    )

    print(
        "Do not tune model v1 using "
        "these holdout results."
    )


if __name__ == "__main__":
    evaluate_holdout()