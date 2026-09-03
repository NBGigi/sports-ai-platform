from database.connection import get_connection


DEFAULT_ELO = 1500
K_FACTOR = 20
HOME_ADVANTAGE = 40
LEAGUE_GAP = 250


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


def get_transition_map(matches):

    leagues_by_team_season = {}

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

            key = (
                team_id,
                season,
            )

            leagues_by_team_season[
                key
            ] = league_id

    transitions = {}

    for (
        team_id,
        season
    ), current_league in (
        leagues_by_team_season.items()
    ):

        next_key = (
            team_id,
            season + 1,
        )

        if (
            next_key
            not in leagues_by_team_season
        ):
            continue

        next_league = (
            leagues_by_team_season[
                next_key
            ]
        )

        if (
            current_league == 40
            and next_league == 39
        ):
            transition_type = "promotion"

        elif (
            current_league == 39
            and next_league == 40
        ):
            transition_type = "relegation"

        else:
            continue

        transitions[
            (
                team_id,
                season + 1,
            )
        ] = transition_type

    return transitions


def apply_league_transition(
    rating,
    transition_type,
):

    if transition_type == "promotion":
        return rating - LEAGUE_GAP

    if transition_type == "relegation":
        return rating + LEAGUE_GAP

    return rating


def calculate_elo_history():

    matches = get_finished_matches()

    transition_map = get_transition_map(
        matches
    )

    ratings = {}
    history = []

    applied_transitions = set()

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

                "elo_difference_before":
                    (
                        home_elo_before
                        - away_elo_before
                    ),

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

def get_current_league_teams(
    matches,
    season,
    league_id,
):
    teams = set()

    for match in matches:

        (
            fixture_id,
            date,
            match_league_id,
            match_season,
            home_team_id,
            away_team_id,
            home_goals,
            away_goals,
        ) = match

        if (
            match_season == season
            and match_league_id == league_id
        ):
            teams.add(home_team_id)
            teams.add(away_team_id)

    return teams


if __name__ == "__main__":

    history, ratings = (
        calculate_elo_history()
    )

    matches = get_finished_matches()

    CURRENT_SEASON = 2026

    print(
        "MATCHES PROCESSED:",
        len(history)
    )

    print(
        "TEAMS RATED:",
        len(ratings)
    )

    premier_league_teams = (
        get_current_league_teams(
            matches,
            CURRENT_SEASON,
            39,
        )
    )

    championship_teams = (
        get_current_league_teams(
            matches,
            CURRENT_SEASON,
            40,
        )
    )

    premier_league_ratings = [
        (
            team_id,
            ratings[team_id]
        )
        for team_id
        in premier_league_teams
        if team_id in ratings
    ]

    championship_ratings = [
        (
            team_id,
            ratings[team_id]
        )
        for team_id
        in championship_teams
        if team_id in ratings
    ]

    premier_league_ratings.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    championship_ratings.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    print(
        "\nPREMIER LEAGUE CURRENT ELO:"
    )

    for team_id, elo in (
        premier_league_ratings
    ):
        print(
            team_id,
            round(elo, 2)
        )

    print(
        "\nCHAMPIONSHIP CURRENT ELO:"
    )

    for team_id, elo in (
        championship_ratings
    ):
        print(
            team_id,
            round(elo, 2)
        )