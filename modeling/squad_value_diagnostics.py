import pandas as pd

from modeling.dataset_split import (
    build_model_dataset,
)

from modeling.squad_value_walk_forward import (
    FOLDS,
    TARGET,
    add_squad_value_features,
    build_model,
    evaluate_model,
)


FEATURE_SETS = {
    "Elo only": [
        "elo_diff",
    ],

    "Squad Value only": [
        "squad_value_log_ratio",
    ],

    "Elo + Squad Value": [
        "elo_diff",
        "squad_value_log_ratio",
    ],
}


if __name__ == "__main__":
    dataset = build_model_dataset()

    dataset = add_squad_value_features(
        dataset
    )

    # --------------------------------------------------
    # 1. Correlation diagnostics
    # --------------------------------------------------

    reliable_dataset = dataset[
        dataset[
            "squad_value_log_ratio"
        ].notna()
    ].copy()

    print(
        "\n=== ELO VS SQUAD VALUE CORRELATION ==="
    )

    print(
        "Reliable rows:",
        len(reliable_dataset)
    )

    pearson = (
        reliable_dataset[
            [
                "elo_diff",
                "squad_value_log_ratio",
            ]
        ]
        .corr(
            method="pearson"
        )
        .iloc[0, 1]
    )

    spearman = (
        reliable_dataset[
            [
                "elo_diff",
                "squad_value_log_ratio",
            ]
        ]
        .corr(
            method="spearman"
        )
        .iloc[0, 1]
    )

    print(
        "Overall Pearson correlation:",
        round(
            pearson,
            4,
        )
    )

    print(
        "Overall Spearman correlation:",
        round(
            spearman,
            4,
        )
    )

    print(
        "\n=== CORRELATION BY SEASON ==="
    )

    correlation_rows = []

    for season in sorted(
        reliable_dataset[
            "season"
        ].unique()
    ):
        season_data = reliable_dataset[
            reliable_dataset[
                "season"
            ]
            == season
        ]

        season_pearson = (
            season_data[
                [
                    "elo_diff",
                    "squad_value_log_ratio",
                ]
            ]
            .corr(
                method="pearson"
            )
            .iloc[0, 1]
        )

        season_spearman = (
            season_data[
                [
                    "elo_diff",
                    "squad_value_log_ratio",
                ]
            ]
            .corr(
                method="spearman"
            )
            .iloc[0, 1]
        )

        correlation_rows.append(
            {
                "season":
                    season,

                "rows":
                    len(season_data),

                "pearson":
                    season_pearson,

                "spearman":
                    season_spearman,
            }
        )

    correlation_df = pd.DataFrame(
        correlation_rows
    )

    print(
        correlation_df.to_string(
            index=False,
            formatters={
                "pearson":
                    lambda x: f"{x:.4f}",

                "spearman":
                    lambda x: f"{x:.4f}",
            },
        )
    )

    # --------------------------------------------------
    # 2. Walk-forward predictive comparison
    # --------------------------------------------------

    print(
        "\n=== WALK-FORWARD DIAGNOSTICS ==="
    )

    results = []

    for fold in FOLDS:
        train = dataset[
            dataset["season"].between(
                fold["train_start"],
                fold["train_end"],
            )
        ].copy()

        validation = dataset[
            dataset["season"]
            == fold[
                "validation_season"
            ]
        ].copy()

        fold_results = {}

        for (
            model_name,
            features,
        ) in FEATURE_SETS.items():

            result = evaluate_model(
                train,
                validation,
                features,
            )

            fold_results[
                model_name
            ] = result

        results.append(
            {
                "fold":
                    fold["name"],

                "validation_season":
                    fold[
                        "validation_season"
                    ],

                "elo_log_loss":
                    fold_results[
                        "Elo only"
                    ]["log_loss"],

                "squad_log_loss":
                    fold_results[
                        "Squad Value only"
                    ]["log_loss"],

                "combined_log_loss":
                    fold_results[
                        "Elo + Squad Value"
                    ]["log_loss"],

                "elo_accuracy":
                    fold_results[
                        "Elo only"
                    ]["accuracy"],

                "squad_accuracy":
                    fold_results[
                        "Squad Value only"
                    ]["accuracy"],

                "combined_accuracy":
                    fold_results[
                        "Elo + Squad Value"
                    ]["accuracy"],
            }
        )

    results_df = pd.DataFrame(
        results
    )

    print(
        results_df.to_string(
            index=False,
            formatters={
                "elo_log_loss":
                    lambda x: f"{x:.4f}",

                "squad_log_loss":
                    lambda x: f"{x:.4f}",

                "combined_log_loss":
                    lambda x: f"{x:.4f}",

                "elo_accuracy":
                    lambda x: f"{x:.4f}",

                "squad_accuracy":
                    lambda x: f"{x:.4f}",

                "combined_accuracy":
                    lambda x: f"{x:.4f}",
            },
        )
    )

    print(
        "\n=== MEAN LOG LOSS ==="
    )

    print(
        "Elo only:",
        round(
            results_df[
                "elo_log_loss"
            ].mean(),
            4,
        )
    )

    print(
        "Squad Value only:",
        round(
            results_df[
                "squad_log_loss"
            ].mean(),
            4,
        )
    )

    print(
        "Elo + Squad Value:",
        round(
            results_df[
                "combined_log_loss"
            ].mean(),
            4,
        )
    )