from collections import defaultdict

from features.elo import (
    DEFAULT_ELO,
    K_FACTOR,
    HOME_ADVANTAGE,
    actual_score,
    expected_score,
    get_finished_matches,
    update_elo,
)


PRIMARY_WINDOW = 19
SECONDARY_WINDOW = 10

CALIBRATION_MAX_TO_SEASON = 2023
VALIDATION_MAX_TO_SEASON = 2025

LEAGUE_GAPS = list(
    range(0, 301, 25)
)


def get_transition_map(matches):

    leagues_by_team_season = defaultdict(set)

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

        leagues_by_team_season[
            (
                home_team_id,
                season,
            )
        ].add(league_id)

        leagues_by_team_season[
            (
                away_team_id,
                season,
            )
        ].add(league_id)

    transitions = {}

    teams = {
        team_id
        for team_id, season
        in leagues_by_team_season.keys()
    }

    seasons = {
        season
        for team_id, season
        in leagues_by_team_season.keys()
    }

    for team_id in teams:

        for season in seasons:

            current_key = (
                team_id,
                season,
            )

            next_key = (
                team_id,
                season + 1,
            )

            if (
                current_key
                not in leagues_by_team_season
            ):
                continue

            if (
                next_key
                not in leagues_by_team_season
            ):
                continue

            current_leagues = (
                leagues_by_team_season[
                    current_key
                ]
            )

            next_leagues = (
                leagues_by_team_season[
                    next_key
                ]
            )

            if (
                len(current_leagues) != 1
                or len(next_leagues) != 1
            ):
                continue

            current_league = next(
                iter(current_leagues)
            )

            next_league = next(
                iter(next_leagues)
            )

            if (
                current_league == 40
                and next_league == 39
            ):
                transition_type = (
                    "promotion"
                )

            elif (
                current_league == 39
                and next_league == 40
            ):
                transition_type = (
                    "relegation"
                )

            else:
                continue

            transitions[
                (
                    team_id,
                    season + 1,
                )
            ] = {
                "type":
                    transition_type,

                "from_league":
                    current_league,

                "to_league":
                    next_league,
            }

    return transitions


def apply_league_transition(
    rating,
    transition_type,
    league_gap,
):

    if transition_type == "promotion":
        return rating - league_gap

    if transition_type == "relegation":
        return rating + league_gap

    return rating


def run_elo_with_gap(
    league_gap,
    evaluation_window,
):

    matches = get_finished_matches()

    transition_map = (
        get_transition_map(matches)
    )

    ratings = {}

    applied_transitions = set()

    games_after_transition = (
        defaultdict(int)
    )

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

                transition = (
                    transition_map[
                        transition_key
                    ]
                )

                ratings[
                    team_id
                ] = apply_league_transition(
                    current_rating,
                    transition["type"],
                    league_gap,
                )

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

        for (
            team_id,
            expected,
            actual,
        ) in (
            (
                home_team_id,
                home_expected,
                home_actual,
            ),
            (
                away_team_id,
                away_expected,
                away_actual,
            ),
        ):

            transition_key = (
                team_id,
                season,
            )

            if (
                transition_key
                not in transition_map
            ):
                continue

            games_played = (
                games_after_transition[
                    transition_key
                ]
            )

            if (
                games_played
                >= evaluation_window
            ):
                continue

            error = (
                actual
                - expected
            ) ** 2

            if (
                    season
                    <= CALIBRATION_MAX_TO_SEASON
            ):
                calibration_errors.append(
                    error
                )

            elif (
                    season
                    <= VALIDATION_MAX_TO_SEASON
            ):
                validation_errors.append(
                    error
                )

            games_after_transition[
                transition_key
            ] += 1

        home_elo_after = update_elo(
            home_elo_before,
            home_expected,
            home_actual,
            K_FACTOR,
        )

        away_elo_after = update_elo(
            away_elo_before,
            away_expected,
            away_actual,
            K_FACTOR,
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
        "league_gap":
            league_gap,

        "evaluation_window":
            evaluation_window,

        "calibration_mse":
            calibration_mse,

        "validation_mse":
            validation_mse,

        "calibration_predictions":
            len(calibration_errors),

        "validation_predictions":
            len(validation_errors),
    }


def calibrate_league_gap(
    evaluation_window,
):

    results = []

    for league_gap in LEAGUE_GAPS:

        result = run_elo_with_gap(
            league_gap,
            evaluation_window,
        )

        results.append(result)

    return results


def print_results(
    results,
    title,
):

    print(
        f"\n{title}"
    )

    print(
        "Calibration predictions:",
        results[0]["calibration_predictions"]
    )

    print(
        "Validation predictions:",
        results[0]["validation_predictions"]
    )

    print(
        "GAP | CALIBRATION MSE | "
        "VALIDATION MSE"
    )

    print(
        "-" * 45
    )

    for result in results:

        gap = result[
            "league_gap"
        ]

        calibration_mse = result[
            "calibration_mse"
        ]

        validation_mse = result[
            "validation_mse"
        ]

        print(
            f"{gap:3d} | "
            f"{calibration_mse:.5f} | "
            f"{validation_mse:.5f}"
        )


if __name__ == "__main__":

    primary_results = (
        calibrate_league_gap(
            PRIMARY_WINDOW
        )
    )

    print_results(
        primary_results,
        "PRIMARY WINDOW - 19 MATCHES",
    )

    secondary_results = (
        calibrate_league_gap(
            SECONDARY_WINDOW
        )
    )

    print_results(
        secondary_results,
        "SECONDARY WINDOW - 10 MATCHES",
    )