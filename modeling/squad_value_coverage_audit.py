import pandas as pd

from features.squad_value import (
    get_fixture_squad_value_features,
)

from modeling.dataset_split import (
    build_model_dataset,
)


SEASONS = [
    2021,
    2022,
    2023,
    2024,
]


if __name__ == "__main__":
    dataset = build_model_dataset()

    audit_dataset = dataset[
        dataset["season"].isin(SEASONS)
    ].copy()

    print(
        "=== SQUAD VALUE COVERAGE AUDIT ==="
    )

    print(
        "Fixtures to audit:",
        len(audit_dataset)
    )

    results = []

    total = len(audit_dataset)

    for number, row in enumerate(
        audit_dataset.itertuples(),
        start=1,
    ):
        try:
            features = (
                get_fixture_squad_value_features(
                    row.fixture_id
                )
            )

            results.append(
                {
                    "fixture_id":
                        row.fixture_id,

                    "season":
                        row.season,

                    "date":
                        row.date,

                    "home_team_name":
                        row.home_team_name,

                    "away_team_name":
                        row.away_team_name,

                    "home_squad_value":
                        features[
                            "home_squad_value"
                        ],

                    "away_squad_value":
                        features[
                            "away_squad_value"
                        ],

                    "home_coverage":
                        features[
                            "home_valuation_coverage"
                        ],

                    "away_coverage":
                        features[
                            "away_valuation_coverage"
                        ],

                    "home_player_count":
                        features[
                            "home_player_count"
                        ],

                    "away_player_count":
                        features[
                            "away_player_count"
                        ],

                    "home_median_age":
                        features[
                            "home_median_valuation_age_days"
                        ],

                    "away_median_age":
                        features[
                            "away_median_valuation_age_days"
                        ],

                    "home_reliable":
                        features[
                            "home_squad_value_is_reliable"
                        ],

                    "away_reliable":
                        features[
                            "away_squad_value_is_reliable"
                        ],
                }
            )

        except Exception as error:
            print(
                "\nFAILED FIXTURE:",
                row.fixture_id,
                row.home_team_name,
                "vs",
                row.away_team_name,
            )

            print(
                "Error:",
                error,
            )

        if (
            number % 100 == 0
            or number == total
        ):
            print(
                f"Processed {number}/{total}"
            )

    audit = pd.DataFrame(
        results
    )

    audit[
        "both_reliable"
    ] = (
        audit["home_reliable"]
        &
        audit["away_reliable"]
    )

    audit[
        "minimum_coverage"
    ] = audit[
        [
            "home_coverage",
            "away_coverage",
        ]
    ].min(axis=1)

    audit[
        "minimum_player_count"
    ] = audit[
        [
            "home_player_count",
            "away_player_count",
        ]
    ].min(axis=1)

    print(
        "\n=== OVERALL ==="
    )

    print(
        "Successful fixtures:",
        len(audit)
    )

    print(
        "Both reliable:",
        audit[
            "both_reliable"
        ].sum()
    )

    print(
        "Both reliable %:",
        round(
            audit[
                "both_reliable"
            ].mean()
            * 100,
            2,
        )
    )

    print(
        "\n=== BY SEASON ==="
    )

    seasonal_summary = (
        audit
        .groupby("season")
        .agg(
            fixtures=(
                "fixture_id",
                "count",
            ),

            both_reliable=(
                "both_reliable",
                "sum",
            ),

            avg_minimum_coverage=(
                "minimum_coverage",
                "mean",
            ),

            median_minimum_players=(
                "minimum_player_count",
                "median",
            ),
        )
    )

    seasonal_summary[
        "reliable_percent"
    ] = (
        seasonal_summary[
            "both_reliable"
        ]
        /
        seasonal_summary[
            "fixtures"
        ]
        * 100
    )

    print(
        seasonal_summary.to_string(
            formatters={
                "avg_minimum_coverage":
                    lambda x: f"{x:.3f}",

                "median_minimum_players":
                    lambda x: f"{x:.1f}",

                "reliable_percent":
                    lambda x: f"{x:.2f}%",
            }
        )
    )

    print(
        "\n=== UNRELIABLE FIXTURES BY SEASON ==="
    )

    print(
        audit[
            ~audit["both_reliable"]
        ]
        .groupby("season")
        .size()
    )