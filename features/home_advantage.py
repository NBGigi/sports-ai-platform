from database.connection import get_connection


def get_home_advantage_stats():

    connection = get_connection()

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                league_id,

                COUNT(*) AS matches,

                SUM(
                    CASE
                        WHEN home_goals > away_goals THEN 1
                        ELSE 0
                    END
                ) AS home_wins,

                SUM(
                    CASE
                        WHEN home_goals = away_goals THEN 1
                        ELSE 0
                    END
                ) AS draws,

                SUM(
                    CASE
                        WHEN home_goals < away_goals THEN 1
                        ELSE 0
                    END
                ) AS away_wins,

                AVG(home_goals) AS avg_home_goals,

                AVG(away_goals) AS avg_away_goals,

                AVG(
                    home_goals - away_goals
                ) AS avg_home_goal_difference

            FROM fixtures

            WHERE status = 'Match Finished'
              AND home_goals IS NOT NULL
              AND away_goals IS NOT NULL
              AND league_id IN (39, 40)
              AND season <= 2025

            GROUP BY league_id

            ORDER BY league_id;
            """
        )

        rows = cursor.fetchall()

    connection.close()

    results = []

    for row in rows:

        (
            league_id,
            matches,
            home_wins,
            draws,
            away_wins,
            avg_home_goals,
            avg_away_goals,
            avg_home_goal_difference,
        ) = row

        home_win_rate = (
            home_wins / matches
        )

        draw_rate = (
            draws / matches
        )

        away_win_rate = (
            away_wins / matches
        )

        home_expected_score = (
            home_win_rate
            + 0.5 * draw_rate
        )

        results.append(
            {
                "league_id":
                    league_id,

                "matches":
                    matches,

                "home_win_rate":
                    home_win_rate,

                "draw_rate":
                    draw_rate,

                "away_win_rate":
                    away_win_rate,

                "home_expected_score":
                    home_expected_score,

                "avg_home_goals":
                    avg_home_goals,

                "avg_away_goals":
                    avg_away_goals,

                "avg_home_goal_difference":
                    avg_home_goal_difference,
            }
        )

    return results


if __name__ == "__main__":

    stats = get_home_advantage_stats()

    for league in stats:

        print(
            "\nLEAGUE:",
            league["league_id"]
        )

        print(
            "Matches:",
            league["matches"]
        )

        print(
            "Home win rate:",
            round(
                league["home_win_rate"],
                3
            )
        )

        print(
            "Draw rate:",
            round(
                league["draw_rate"],
                3
            )
        )

        print(
            "Away win rate:",
            round(
                league["away_win_rate"],
                3
            )
        )

        print(
            "Home expected score:",
            round(
                league["home_expected_score"],
                3
            )
        )

        print(
            "Avg home goals:",
            round(
                float(
                    league["avg_home_goals"]
                ),
                3
            )
        )

        print(
            "Avg away goals:",
            round(
                float(
                    league["avg_away_goals"]
                ),
                3
            )
        )

        print(
            "Avg home goal difference:",
            round(
                float(
                    league[
                        "avg_home_goal_difference"
                    ]
                ),
                3
            )
        )