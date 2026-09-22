import pandas as pd

from xgboost import XGBClassifier

from modeling.model_selection_walk_forward import (
    ELO_FEATURES,
    FULL_FEATURES,
    FOLDS,
    build_full_dataset,
    evaluate_model,
)


CONFIGS = {
    "XGB Current": {
        "n_estimators": 200,
        "learning_rate": 0.03,
        "max_depth": 3,
        "min_child_weight": 5,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_lambda": 2.0,
        "reg_alpha": 0.0,
        "gamma": 0.0,
    },

    "XGB Conservative": {
        "n_estimators": 120,
        "learning_rate": 0.03,
        "max_depth": 2,
        "min_child_weight": 15,
        "subsample": 0.9,
        "colsample_bytree": 0.8,
        "reg_lambda": 5.0,
        "reg_alpha": 0.5,
        "gamma": 0.1,
    },

    "XGB Strong Regularization": {
        "n_estimators": 80,
        "learning_rate": 0.02,
        "max_depth": 2,
        "min_child_weight": 25,
        "subsample": 0.9,
        "colsample_bytree": 0.8,
        "reg_lambda": 10.0,
        "reg_alpha": 1.0,
        "gamma": 0.2,
    },
}


FEATURE_SETS = {
    "Elo": ELO_FEATURES,
    "Full": FULL_FEATURES,
}


def build_xgboost_model(params):
    return XGBClassifier(
        objective="multi:softprob",
        num_class=3,
        eval_metric="mlogloss",
        random_state=42,
        n_jobs=-1,
        **params,
    )


if __name__ == "__main__":
    dataset = build_full_dataset()

    results = []

    print(
        "\n=== XGBOOST REGULARIZATION TEST ==="
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
            f"\n--- {fold['name']} "
            f"(validation {fold['validation_season']}) ---"
        )

        for config_name, params in CONFIGS.items():
            for feature_name, features in FEATURE_SETS.items():

                model = build_xgboost_model(
                    params
                )

                metrics = evaluate_model(
                    model,
                    train,
                    validation,
                    features,
                )

                experiment_name = (
                    f"{config_name} — {feature_name}"
                )

                print(
                    experiment_name,
                    "| Train LL:",
                    round(
                        metrics["train_log_loss"],
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
                        "fold": fold["name"],
                        "validation_season":
                            fold[
                                "validation_season"
                            ],
                        "model":
                            experiment_name,
                        **metrics,
                    }
                )

    results_df = pd.DataFrame(
        results
    )

    summary = (
        results_df
        .groupby(
            "model",
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

    summary[
        "generalization_gap"
    ] = (
        summary[
            "mean_validation_log_loss"
        ]
        -
        summary[
            "mean_train_log_loss"
        ]
    )

    print(
        "\n=== REGULARIZATION SUMMARY ==="
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
                "generalization_gap":
                    lambda x: f"{x:+.4f}",
            },
        )
    )

    print(
        "\nReference:"
    )

    print(
        "Logistic Elo mean Validation "
        "Log Loss = 0.9700"
    )