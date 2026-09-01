from database.connection import get_connection


def get_team_season_strength_stats(
    league_id=None,
    season=None,
):
    connection = get_connection()

    with connection.cursor() as cursor:
        cursor.execute(
            """
            WITH team_matches AS (

                SELECT
                    home_team_id AS team_id,
                    league_id,
                    season,

                    1 AS games_played,

                    CASE
                        WHEN home_goals > away_goals THEN 3
                        WHEN home_goals = away_goals THEN 1
                        ELSE 0
                    END AS points,

                    home_goals AS goals_for,
                    away_goals AS goals_against

                FROM fixtures

                WHERE status = 'Match Finished'
                  AND home_goals IS NOT NULL
                  AND away_goals IS NOT NULL

                UNION ALL

                SELECT
                    away_team_id AS team_id,
                    league_id,
                    season,

                    1 AS games_played,

                    CASE
                        WHEN away_goals > home_goals THEN 3
                        WHEN away_goals = home_goals THEN 1
                        ELSE 0
                    END AS points,

                    away_goals AS goals_for,
                    home_goals AS goals_against

                FROM fixtures

                WHERE status = 'Match Finished'
                  AND home_goals IS NOT NULL
                  AND away_goals IS NOT NULL
            )

            SELECT
                tm.team_id,
                t.team_name,
                tm.league_id,
                l.league_name,
                tm.season,

                SUM(tm.games_played) AS games_played,
                SUM(tm.points) AS points,
                SUM(tm.goals_for) AS goals_for,
                SUM(tm.goals_against) AS goals_against,

                SUM(
                    tm.goals_for
                    - tm.goals_against
                ) AS goal_difference,

                ROUND(
                    SUM(tm.points)::numeric
                    / NULLIF(
                        SUM(tm.games_played),
                        0
                    ),
                    3
                ) AS points_per_game,

                ROUND(
                    SUM(
                        tm.goals_for
                        - tm.goals_against
                    )::numeric
                    / NULLIF(
                        SUM(tm.games_played),
                        0
                    ),
                    3
                ) AS goal_difference_per_game,

                ROUND(
                    SUM(tm.goals_for)::numeric
                    / NULLIF(
                        SUM(tm.games_played),
                        0
                    ),
                    3
                ) AS goals_for_per_game,

                ROUND(
                    SUM(tm.goals_against)::numeric
                    / NULLIF(
                        SUM(tm.games_played),
                        0
                    ),
                    3
                ) AS goals_against_per_game

            FROM team_matches tm

            JOIN teams t
                ON t.team_id = tm.team_id

            JOIN leagues l
                ON l.league_id = tm.league_id
                
            WHERE
                (%s::INTEGER IS NULL OR tm.league_id = %s)
            AND
                (%s::INTEGER IS NULL OR tm.season = %s)

            GROUP BY
                tm.team_id,
                t.team_name,
                tm.league_id,
                l.league_name,
                tm.season

            ORDER BY
                tm.season,
                tm.league_id,
                points_per_game DESC;
            """,
            (
                league_id,
                league_id,
                season,
                season,
            )
        )

        rows = cursor.fetchall()

        columns = [
            "team_id",
            "team_name",
            "league_id",
            "league_name",
            "season",
            "games_played",
            "points",
            "goals_for",
            "goals_against",
            "goal_difference",
            "points_per_game",
            "goal_difference_per_game",
            "goals_for_per_game",
            "goals_against_per_game",
        ]

    connection.close()

    return [
        dict(zip(columns, row))
        for row in rows
    ]

def get_league_transitions():

    stats = get_team_season_strength_stats()

    stats_by_team_season = {
        (
            row["team_id"],
            row["season"]
        ): row
        for row in stats
    }

    transitions = []

    for row in stats:

        team_id = row["team_id"]
        season = row["season"]

        next_season_key = (
            team_id,
            season + 1
        )

        next_season = (
            stats_by_team_season.get(
                next_season_key
            )
        )

        if next_season is None:
            continue

        current_league = row["league_id"]
        next_league = next_season["league_id"]

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

        transitions.append(
            {
                "team_id":
                    team_id,

                "team_name":
                    row["team_name"],

                "transition_type":
                    transition_type,

                "from_season":
                    season,

                "to_season":
                    season + 1,

                "from_league":
                    current_league,

                "to_league":
                    next_league,

                "from_ppg":
                    row["points_per_game"],

                "to_ppg":
                    next_season[
                        "points_per_game"
                    ],

                "ppg_change":
                    next_season[
                        "points_per_game"
                    ]
                    - row[
                        "points_per_game"
                    ],

                "from_gd_per_game":
                    row[
                        "goal_difference_per_game"
                    ],

                "to_gd_per_game":
                    next_season[
                        "goal_difference_per_game"
                    ],

                "gd_per_game_change":
                    next_season[
                        "goal_difference_per_game"
                    ]
                    - row[
                        "goal_difference_per_game"
                    ],

                "from_gf_per_game":
                    row[
                        "goals_for_per_game"
                    ],

                "to_gf_per_game":
                    next_season[
                        "goals_for_per_game"
                    ],

                "from_ga_per_game":
                    row[
                        "goals_against_per_game"
                    ],

                "to_ga_per_game":
                    next_season[
                        "goals_against_per_game"
                    ],
            }
        )

    return transitions

def summarize_league_transitions():

    transitions = get_league_transitions()

    complete_transitions = [
        transition
        for transition in transitions
        if transition["to_season"] <= 2025
    ]

    promotions = [
        transition
        for transition in complete_transitions
        if transition["transition_type"] == "promotion"
    ]

    relegations = [
        transition
        for transition in complete_transitions
        if transition["transition_type"] == "relegation"
    ]

    def average(rows, key):

        if not rows:
            return None

        return sum(
            row[key]
            for row in rows
        ) / len(rows)

    promotion_avg_ppg_change = average(
        promotions,
        "ppg_change"
    )

    relegation_avg_ppg_change = average(
        relegations,
        "ppg_change"
    )

    promotion_avg_gd_change = average(
        promotions,
        "gd_per_game_change"
    )

    relegation_avg_gd_change = average(
        relegations,
        "gd_per_game_change"
    )

    symmetric_ppg_gap = (
                                abs(promotion_avg_ppg_change)
                                +
                                abs(relegation_avg_ppg_change)
                        ) / 2

    symmetric_gd_gap = (
                               abs(promotion_avg_gd_change)
                               +
                               abs(relegation_avg_gd_change)
                       ) / 2

    return {
        "promotion_count":
            len(promotions),

        "relegation_count":
            len(relegations),

        "promotion_avg_ppg_change":
            promotion_avg_ppg_change,

        "relegation_avg_ppg_change":
            relegation_avg_ppg_change,

        "symmetric_ppg_gap":
            symmetric_ppg_gap,

        "promotion_avg_gd_change":
            promotion_avg_gd_change,

        "relegation_avg_gd_change":
            relegation_avg_gd_change,

        "symmetric_gd_gap":
            symmetric_gd_gap,
    }


if __name__ == "__main__":

    summary = summarize_league_transitions()

    print("\nLEAGUE TRANSITION SUMMARY")

    for key, value in summary.items():
        print(
            key,
            "=",
            value
        )