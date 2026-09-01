from database.connection import get_connection


DEFAULT_ELO = 1500
K_FACTOR = 20
HOME_ADVANTAGE = 65


def expected_score(
    team_elo,
    opponent_elo,
    home_advantage=0,
):
    adjusted_team_elo = (
        team_elo
        + home_advantage
    )

    return 1 / (
        1
        + 10 ** (
            (
                opponent_elo
                - adjusted_team_elo
            )
            / 400
        )
    )


def actual_score(
    goals_for,
    goals_against,
):
    if goals_for > goals_against:
        return 1.0

    if goals_for == goals_against:
        return 0.5

    return 0.0


def update_elo(
    current_elo,
    expected,
    actual,
    k_factor=K_FACTOR,
):
    return (
        current_elo
        + k_factor
        * (
            actual
            - expected
        )
    )


def get_finished_matches():

    connection = get_connection()

    with connection.cursor() as cursor:

        cursor.execute(
            """
            SELECT
                fixture_id,
                date,
                league_id,
                season,
                home_team_id,
                away_team_id,
                home_goals,
                away_goals

            FROM fixtures

            WHERE status = 'Match Finished'
              AND home_goals IS NOT NULL
              AND away_goals IS NOT NULL
              AND league_id IN (39, 40)

            ORDER BY
                date,
                fixture_id;
            """
        )

        rows = cursor.fetchall()

    connection.close()

    return rows


def calculate_elo_history():

    matches = get_finished_matches()

    ratings = {}
    history = []

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

        home_elo_before = ratings.get(
            home_team_id,
            DEFAULT_ELO
        )

        away_elo_before = ratings.get(
            away_team_id,
            DEFAULT_ELO
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

        home_elo_after = update_elo(
            home_elo_before,
            home_expected,
            home_actual,
        )

        away_elo_after = update_elo(
            away_elo_before,
            away_expected,
            away_actual,
        )

        ratings[
            home_team_id
        ] = home_elo_after

        ratings[
            away_team_id
        ] = away_elo_after

        history.append(
            {
                "fixture_id":
                    fixture_id,

                "date":
                    date,

                "league_id":
                    league_id,

                "season":
                    season,

                "home_team_id":
                    home_team_id,

                "away_team_id":
                    away_team_id,

                "home_elo_before":
                    home_elo_before,

                "away_elo_before":
                    away_elo_before,

                "home_expected":
                    home_expected,

                "away_expected":
                    away_expected,

                "home_actual":
                    home_actual,

                "away_actual":
                    away_actual,

                "home_elo_after":
                    home_elo_after,

                "away_elo_after":
                    away_elo_after,
            }
        )

    return history, ratings


if __name__ == "__main__":

    history, ratings = calculate_elo_history()

    print(
        "MATCHES PROCESSED:",
        len(history)
    )

    print(
        "TEAMS RATED:",
        len(ratings)
    )

    print(
        "\nTOP 10 CURRENT ELO:"
    )

    top_teams = sorted(
        ratings.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:10]

    for team_id, elo in top_teams:

        print(
            team_id,
            round(elo, 2)
        )