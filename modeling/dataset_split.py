from features.rolling_feature import (
    load_finished_fixtures,
    build_team_match_history,
    validate_team_match_history,
    add_pl_spell_id,
    add_rolling_features,
    build_fixture_feature_dataset,
    add_elo_features,
)


def build_model_dataset():
    fixtures = load_finished_fixtures()

    team_history = build_team_match_history(
        fixtures
    )

    validate_team_match_history(
        team_history
    )

    team_history = add_pl_spell_id(
        team_history
    )

    team_history = add_rolling_features(
        team_history
    )

    fixture_dataset = (
        build_fixture_feature_dataset(
            team_history
        )
    )

    fixture_dataset = add_elo_features(
        fixture_dataset
    )

    return fixture_dataset


def split_dataset_by_time(dataset):
    warmup = dataset[
        dataset["season"] == 2020
    ].copy()

    train = dataset[
        dataset["season"].between(
            2021,
            2023,
        )
    ].copy()

    validation = dataset[
        dataset["season"] == 2024
    ].copy()

    test = dataset[
        dataset["season"] == 2025
    ].copy()

    holdout = dataset[
        dataset["season"] == 2026
    ].copy()

    return {
        "warmup": warmup,
        "train": train,
        "validation": validation,
        "test": test,
        "holdout": holdout,
    }


def print_split_summary(
    dataset,
    splits,
):
    print(
        "\n=== CHRONOLOGICAL DATASET SPLIT ==="
    )

    print(
        "Full dataset:",
        len(dataset)
    )

    total_split_rows = 0

    for name, split in splits.items():
        total_split_rows += len(split)

        print(
            f"\n{name.upper()}"
        )

        print(
            "Rows:",
            len(split)
        )

        print(
            "Date range:",
            split["date"].min(),
            "->",
            split["date"].max(),
        )

        print(
            "Labels:"
        )

        print(
            split[
                "label_1x2"
            ]
            .value_counts()
        )

    print(
        "\nTotal rows across splits:",
        total_split_rows
    )

    print(
        "Matches full dataset:",
        total_split_rows == len(dataset)
    )


if __name__ == "__main__":
    dataset = build_model_dataset()

    splits = split_dataset_by_time(
        dataset
    )

    print_split_summary(
        dataset,
        splits,
    )