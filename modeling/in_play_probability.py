import numpy as np

from scipy.optimize import minimize
from scipy.stats import poisson


MATCH_MINUTES = 90
MAX_GOALS = 10


def normalize_probabilities(
    probabilities,
):
    total = sum(
        probabilities.values()
    )

    if total <= 0:
        raise ValueError(
            "Probability total must be positive."
        )

    return {
        key: value / total
        for key, value
        in probabilities.items()
    }


def poisson_match_probabilities(
    lambda_home,
    lambda_away,
):
    goals = np.arange(
        MAX_GOALS + 1
    )

    home_goal_probabilities = (
        poisson.pmf(
            goals,
            lambda_home,
        )
    )

    away_goal_probabilities = (
        poisson.pmf(
            goals,
            lambda_away,
        )
    )

    score_matrix = np.outer(
        home_goal_probabilities,
        away_goal_probabilities,
    )

    home_win = np.tril(
        score_matrix,
        k=-1,
    ).sum()

    draw = np.trace(
        score_matrix
    )

    away_win = np.triu(
        score_matrix,
        k=1,
    ).sum()

    return normalize_probabilities(
        {
            "H": float(home_win),
            "D": float(draw),
            "A": float(away_win),
        }
    )


def fit_goal_rates(
    prematch_probabilities,
):
    target = normalize_probabilities(
        prematch_probabilities
    )

    def objective(parameters):
        lambda_home = parameters[0]
        lambda_away = parameters[1]

        model_probabilities = (
            poisson_match_probabilities(
                lambda_home,
                lambda_away,
            )
        )

        error = sum(
            (
                model_probabilities[label]
                - target[label]
            ) ** 2
            for label in (
                "H",
                "D",
                "A",
            )
        )

        return error

    result = minimize(
        objective,
        x0=[
            1.5,
            1.2,
        ],
        bounds=[
            (
                0.05,
                5.0,
            ),
            (
                0.05,
                5.0,
            ),
        ],
        method="L-BFGS-B",
    )

    if not result.success:
        raise RuntimeError(
            "Could not fit Poisson goal rates: "
            f"{result.message}"
        )

    return {
        "lambda_home":
            float(result.x[0]),

        "lambda_away":
            float(result.x[1]),
    }


def calculate_in_play_probabilities(
    prematch_probabilities,
    minute,
    home_goals,
    away_goals,
):
    if minute < 0:
        raise ValueError(
            "Minute cannot be negative."
        )

    if home_goals < 0 or away_goals < 0:
        raise ValueError(
            "Goals cannot be negative."
        )

    minute = min(
        minute,
        MATCH_MINUTES,
    )

    goal_rates = fit_goal_rates(
        prematch_probabilities
    )

    remaining_fraction = (
        MATCH_MINUTES
        - minute
    ) / MATCH_MINUTES

    remaining_lambda_home = (
        goal_rates["lambda_home"]
        * remaining_fraction
    )

    remaining_lambda_away = (
        goal_rates["lambda_away"]
        * remaining_fraction
    )

    goals = np.arange(
        MAX_GOALS + 1
    )

    home_future_probabilities = (
        poisson.pmf(
            goals,
            remaining_lambda_home,
        )
    )

    away_future_probabilities = (
        poisson.pmf(
            goals,
            remaining_lambda_away,
        )
    )

    score_matrix = np.outer(
        home_future_probabilities,
        away_future_probabilities,
    )

    home_win = 0.0
    draw = 0.0
    away_win = 0.0

    for future_home_goals in goals:
        for future_away_goals in goals:
            probability = score_matrix[
                future_home_goals,
                future_away_goals,
            ]

            final_home_goals = (
                home_goals
                + future_home_goals
            )

            final_away_goals = (
                away_goals
                + future_away_goals
            )

            if (
                final_home_goals
                > final_away_goals
            ):
                home_win += probability

            elif (
                final_home_goals
                == final_away_goals
            ):
                draw += probability

            else:
                away_win += probability

    probabilities = (
        normalize_probabilities(
            {
                "H":
                    float(home_win),

                "D":
                    float(draw),

                "A":
                    float(away_win),
            }
        )
    )

    return {
        "probabilities":
            probabilities,

        "lambda_home":
            goal_rates[
                "lambda_home"
            ],

        "lambda_away":
            goal_rates[
                "lambda_away"
            ],

        "remaining_lambda_home":
            remaining_lambda_home,

        "remaining_lambda_away":
            remaining_lambda_away,

        "remaining_fraction":
            remaining_fraction,
    }


if __name__ == "__main__":
    prematch = {
        "H": 0.5404,
        "D": 0.2534,
        "A": 0.2062,
    }

    scenarios = [
        (
            0,
            0,
            0,
        ),
        (
            30,
            0,
            0,
        ),
        (
            30,
            1,
            0,
        ),
        (
            60,
            1,
            0,
        ),
        (
            80,
            1,
            0,
        ),
        (
            80,
            1,
            1,
        ),
        (
            90,
            1,
            0,
        ),
    ]

    print(
        "=== IN-PLAY PROBABILITY ENGINE ==="
    )

    print(
        "\nPre-match probabilities:"
    )

    print(
        prematch
    )

    for (
        minute,
        home_goals,
        away_goals,
    ) in scenarios:

        result = (
            calculate_in_play_probabilities(
                prematch,
                minute,
                home_goals,
                away_goals,
            )
        )

        probabilities = result[
            "probabilities"
        ]

        print(
            "\n--------------------------"
        )

        print(
            f"Minute: {minute}"
        )

        print(
            "Score:",
            f"{home_goals}-"
            f"{away_goals}",
        )

        print(
            "Home:",
            round(
                probabilities["H"],
                4,
            ),
        )

        print(
            "Draw:",
            round(
                probabilities["D"],
                4,
            ),
        )

        print(
            "Away:",
            round(
                probabilities["A"],
                4,
            ),
        )

    fitted = fit_goal_rates(
        prematch
    )

    print(
        "\n=== FITTED GOAL RATES ==="
    )

    print(
        fitted
    )

    reconstructed = (
        poisson_match_probabilities(
            fitted[
                "lambda_home"
            ],
            fitted[
                "lambda_away"
            ],
        )
    )

    print(
        "\nPoisson reconstruction:"
    )

    print(
        reconstructed
    )