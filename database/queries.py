def insert_team(connection, team_id, team_name):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO teams (team_id, team_name)
            VALUES (%s, %s)
            ON CONFLICT (team_id) DO NOTHING;
            """,
            (team_id, team_name)
        )

    connection.commit()

def insert_teams(connection, teams):
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO teams (team_id, team_name)
            VALUES (%s, %s)
            ON CONFLICT (team_id) DO NOTHING;
            """,
            teams.items()
        )

    connection.commit()

def insert_fixtures(connection, matches):
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO fixtures (
                fixture_id,
                date,
                league_id,
                season,
                status,
                minute,
                home_team_id,
                away_team_id,
                home_goals,
                away_goals
            )
            VALUES (
                %(fixture_id)s,
                %(date)s,
                %(league_id)s,
                %(season)s,
                %(status)s,
                %(minute)s,
                %(home_team_id)s,
                %(away_team_id)s,
                %(home_goals)s,
                %(away_goals)s
            )
            ON CONFLICT (fixture_id)
            DO UPDATE SET
                date = EXCLUDED.date,
                status = EXCLUDED.status,
                minute = EXCLUDED.minute,
                home_goals = EXCLUDED.home_goals,
                away_goals = EXCLUDED.away_goals;
            """,
            matches
        )

    connection.commit()