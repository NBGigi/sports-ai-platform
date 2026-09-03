from features.elo import (
    DEFAULT_ELO,
    HOME_ADVANTAGE,
    LEAGUE_GAP,
    actual_score,
    expected_score,
    get_finished_matches,
    get_transition_map,
    apply_league_transition,
    update_elo,
)


K_VALUES = [
    5,
    10,
    15,
    20,
    25,
    30,
    40,
    50,
]

WARMUP_SEASON = 2020
CALIBRATION_MIN_SEASON = 2021
CALIBRATION_MAX_SEASON = 2023
VALIDATION_MAX_SEASON = 2025


def run_elo_with_k(k_factor):

    matches = get_finished_matches()

    transition_map = get_transition_map(
        matches
    )

    ratings = {}

    applied_transitions = set()

    calibration_errors = []
    validation_errors = []

    for match in matches:

        (
            fixture_id,
            date,
            league_id,
            season,
            home_team_id,
            away_team_id,
            home_goals,
            away_goals,
        ) = match

        for team_id in (
            home_team_id,
            away_team_id,
        ):

            transition_key = (
                team_id,
                season,
            )

            if (
                transition_key
                in transition_map
                and transition_key
                not in applied_transitions
            ):

                current_rating = ratings.get(
                    team_id,
                    DEFAULT_ELO,
                )

                transition_type = (
                    transition_map[
                        transition_key
                    ]
                )

                adjusted_rating = (
                    apply_league_transition(
                        current_rating,
                        transition_type,
                    )
                )

                ratings[
                    team_id
                ] = adjusted_rating

                applied_transitions.add(
                    transition_key
                )

        home_elo_before = ratings.get(
            home_team_id,
            DEFAULT_ELO,
        )

        away_elo_before = ratings.get(
            away_team_id,
            DEFAULT_ELO,
        )

        home_expected = expected_score(
            home_elo_before,
            away_elo_before,
            HOME_ADVANTAGE,
        )

        away_expected = (
            1
            - home_expected
        )

        home_actual = actual_score(
            home_goals,
            away_goals,
        )

        away_actual = (
            1
            - home_actual
        )

        home_error = (
            home_actual
            - home_expected
        ) ** 2

        away_error = (
            away_actual
            - away_expected
        ) ** 2

        match_error = (
            home_error
            + away_error
        ) / 2

        if (
                CALIBRATION_MIN_SEASON
                <= season
                <= CALIBRATION_MAX_SEASON
        ):
            calibration_errors.append(
                match_error
            )

        elif (
                CALIBRATION_MAX_SEASON
                < season
                <= VALIDATION_MAX_SEASON
        ):
            validation_errors.append(
                match_error
            )

        home_elo_after = update_elo(
            home_elo_before,
            home_expected,
            home_actual,
            k_factor,
        )

        away_elo_after = update_elo(
            away_elo_before,
            away_expected,
            away_actual,
            k_factor,
        )

        ratings[
            home_team_id
        ] = home_elo_after

        ratings[
            away_team_id
        ] = away_elo_after

    calibration_mse = (
        sum(calibration_errors)
        / len(calibration_errors)
        if calibration_errors
        else None
    )

    validation_mse = (
        sum(validation_errors)
        / len(validation_errors)
        if validation_errors
        else None
    )

    return {
        "k_factor":
            k_factor,

        "calibration_mse":
            calibration_mse,

        "validation_mse":
            validation_mse,

        "calibration_matches":
            len(calibration_errors),

        "validation_matches":
            len(validation_errors),
    }


def calibrate_k():

    results = []

    for k_factor in K_VALUES:

        result = run_elo_with_k(
            k_factor
        )

        results.append(
            result
        )

    return results


def print_results(results):

    print(
        "\nK FACTOR CALIBRATION"
    )

    print(
        "Calibration matches:",
        results[0][
            "calibration_matches"
        ]
    )

    print(
        "Validation matches:",
        results[0][
            "validation_matches"
        ]
    )

    print(
        "\nK | CALIBRATION MSE | "
        "VALIDATION MSE"
    )

    print(
        "-" * 42
    )

    for result in results:

        k_factor = result[
            "k_factor"
        ]

        calibration_mse = result[
            "calibration_mse"
        ]

        validation_mse = result[
            "validation_mse"
        ]

        print(
            f"{k_factor:2d} | "
            f"{calibration_mse:.5f} | "
            f"{validation_mse:.5f}"
        )


if __name__ == "__main__":

    results = calibrate_k()

    print_results(
        results
    )