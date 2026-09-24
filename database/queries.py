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
                round,
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
                %(round)s,
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
                league_id = EXCLUDED.league_id,
                season = EXCLUDED.season,
                round = EXCLUDED.round,
                status = EXCLUDED.status,
                minute = EXCLUDED.minute,
                home_team_id = EXCLUDED.home_team_id,
                away_team_id = EXCLUDED.away_team_id,
                home_goals = EXCLUDED.home_goals,
                away_goals = EXCLUDED.away_goals;
            """,
            matches
        )

    connection.commit()


def insert_fixture_statistics(connection, fixture_id, team_statistics):
    rows = []

    for stats in team_statistics:
        row = {
            "fixture_id": fixture_id,
            **stats
        }

        rows.append(row)

    with connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO fixture_statistics (
                fixture_id,
                team_id,
                shots_on_goal,
                shots_off_goal,
                total_shots,
                blocked_shots,
                shots_inside_box,
                shots_outside_box,
                corners,
                possession,
                yellow_cards,
                red_cards,
                xg
            )
            VALUES (
                %(fixture_id)s,
                %(team_id)s,
                %(shots_on_goal)s,
                %(shots_off_goal)s,
                %(total_shots)s,
                %(blocked_shots)s,
                %(shots_inside_box)s,
                %(shots_outside_box)s,
                %(corners)s,
                %(possession)s,
                %(yellow_cards)s,
                %(red_cards)s,
                %(xg)s
            )
            ON CONFLICT (fixture_id, team_id)
            DO UPDATE SET
                shots_on_goal = COALESCE(
                    EXCLUDED.shots_on_goal,
                    fixture_statistics.shots_on_goal
                ),
                shots_off_goal = COALESCE(
                    EXCLUDED.shots_off_goal,
                    fixture_statistics.shots_off_goal
                ),
                total_shots = COALESCE(
                    EXCLUDED.total_shots,
                    fixture_statistics.total_shots
                ),
                blocked_shots = COALESCE(
                    EXCLUDED.blocked_shots,
                    fixture_statistics.blocked_shots
                ),
                shots_inside_box = COALESCE(
                    EXCLUDED.shots_inside_box,
                    fixture_statistics.shots_inside_box
                ),
                shots_outside_box = COALESCE(
                    EXCLUDED.shots_outside_box,
                    fixture_statistics.shots_outside_box
                ),
                corners = COALESCE(
                    EXCLUDED.corners,
                    fixture_statistics.corners
                ),
                possession = COALESCE(
                    EXCLUDED.possession,
                    fixture_statistics.possession
                ),
                yellow_cards = COALESCE(
                    EXCLUDED.yellow_cards,
                    fixture_statistics.yellow_cards
                ),
                red_cards = COALESCE(
                    EXCLUDED.red_cards,
                    fixture_statistics.red_cards
                ),
                xg = COALESCE(
                    EXCLUDED.xg,
                    fixture_statistics.xg
                );
            """,
            rows
        )

    connection.commit()

def get_existing_statistics_fixture_ids(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT fixture_id
            FROM fixture_statistics
            GROUP BY fixture_id
            HAVING COUNT(DISTINCT team_id) = 2;
            """
        )

        rows = cursor.fetchall()

    return {
        row[0]
        for row in rows
    }

def insert_team_external_ids(connection, mappings):
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO team_external_ids (
                team_id,
                provider,
                external_id
            )
            VALUES (
                %(team_id)s,
                %(provider)s,
                %(external_id)s
            )
            ON CONFLICT (team_id, provider)
            DO UPDATE SET
                external_id = EXCLUDED.external_id;
            """,
            mappings
        )

    connection.commit()

def get_external_team_id(connection, team_id, provider):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT external_id
            FROM team_external_ids
            WHERE team_id = %s
              AND provider = %s;
            """,
            (team_id, provider)
        )

        row = cursor.fetchone()

    if row is None:
        return None

    return row[0]

def get_fixture(connection, fixture_id):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                fixture_id,
                date,
                home_team_id,
                away_team_id
            FROM fixtures
            WHERE fixture_id = %s;
            """,
            (fixture_id,)
        )

        row = cursor.fetchone()

    if row is None:
        return None

    return {
        "fixture_id": row[0],
        "date": row[1],
        "home_team_id": row[2],
        "away_team_id": row[3],
    }


def insert_live_snapshot(connection, snapshot):

    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO live_fixture_snapshots (
                fixture_id,
                team_id,
                captured_at,
                minute,
                home_goals,
                away_goals,
                shots_on_goal,
                shots_off_goal,
                total_shots,
                blocked_shots,
                shots_inside_box,
                shots_outside_box,
                corners,
                possession,
                yellow_cards,
                red_cards,
                xg
            )
            VALUES (
                %(fixture_id)s,
                %(team_id)s,
                %(captured_at)s,
                %(minute)s,
                %(home_goals)s,
                %(away_goals)s,
                %(shots_on_goal)s,
                %(shots_off_goal)s,
                %(total_shots)s,
                %(blocked_shots)s,
                %(shots_inside_box)s,
                %(shots_outside_box)s,
                %(corners)s,
                %(possession)s,
                %(yellow_cards)s,
                %(red_cards)s,
                %(xg)s
            )
            ON CONFLICT (
                fixture_id,
                team_id,
                captured_at
            )
            DO NOTHING;
            """,
            snapshot
        )

    connection.commit()

def persist_live_fixture_event(
    connection,
    event,
):
    snapshots = []

    for team_id in (
        event["home_team_id"],
        event["away_team_id"],
    ):
        snapshots.append(
            {
                "fixture_id":
                    event["fixture_id"],

                "team_id":
                    team_id,

                "captured_at":
                    event["captured_at"],

                "minute":
                    event["minute"],

                "home_goals":
                    event["home_goals"],

                "away_goals":
                    event["away_goals"],

                "shots_on_goal": None,
                "shots_off_goal": None,
                "total_shots": None,
                "blocked_shots": None,
                "shots_inside_box": None,
                "shots_outside_box": None,
                "corners": None,
                "possession": None,
                "yellow_cards": None,
                "red_cards": None,
                "xg": None,
            }
        )

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE fixtures
                SET
                    status = %(status)s,
                    minute = %(minute)s,
                    home_goals = %(home_goals)s,
                    away_goals = %(away_goals)s
                WHERE fixture_id = %(fixture_id)s
                RETURNING fixture_id;
                """,
                event,
            )

            updated_fixture = (
                cursor.fetchone()
            )

            if updated_fixture is None:
                raise ValueError(
                    "Fixture not found in database: "
                    f"{event['fixture_id']}"
                )

            cursor.executemany(
                """
                INSERT INTO live_fixture_snapshots (
                    fixture_id,
                    team_id,
                    captured_at,
                    minute,
                    home_goals,
                    away_goals,
                    shots_on_goal,
                    shots_off_goal,
                    total_shots,
                    blocked_shots,
                    shots_inside_box,
                    shots_outside_box,
                    corners,
                    possession,
                    yellow_cards,
                    red_cards,
                    xg
                )
                VALUES (
                    %(fixture_id)s,
                    %(team_id)s,
                    %(captured_at)s,
                    %(minute)s,
                    %(home_goals)s,
                    %(away_goals)s,
                    %(shots_on_goal)s,
                    %(shots_off_goal)s,
                    %(total_shots)s,
                    %(blocked_shots)s,
                    %(shots_inside_box)s,
                    %(shots_outside_box)s,
                    %(corners)s,
                    %(possession)s,
                    %(yellow_cards)s,
                    %(red_cards)s,
                    %(xg)s
                )
                ON CONFLICT (
                    fixture_id,
                    team_id,
                    captured_at
                )
                DO NOTHING;
                """,
                snapshots,
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise


def insert_fixture_prediction(
    connection,
    prediction,
):
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO fixture_predictions (
                    fixture_id,
                    model_version,
                    home_elo,
                    away_elo,
                    elo_diff,
                    prob_home,
                    prob_draw,
                    prob_away
                )
                VALUES (
                    %(fixture_id)s,
                    %(model_version)s,
                    %(home_elo)s,
                    %(away_elo)s,
                    %(elo_diff)s,
                    %(prob_home)s,
                    %(prob_draw)s,
                    %(prob_away)s
                )
                ON CONFLICT (
                    fixture_id,
                    model_version
                )
                DO NOTHING
                RETURNING fixture_id;
                """,
                prediction,
            )

            inserted = (
                cursor.fetchone()
                is not None
            )

        connection.commit()

        return inserted

    except Exception:
        connection.rollback()
        raise

def get_fixture_prediction(
    connection,
    fixture_id,
    model_version="v1",
):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                fixture_id,
                model_version,
                home_elo,
                away_elo,
                elo_diff,
                prob_home,
                prob_draw,
                prob_away
            FROM fixture_predictions
            WHERE fixture_id = %s
              AND model_version = %s;
            """,
            (
                fixture_id,
                model_version,
            ),
        )

        row = cursor.fetchone()

    if row is None:
        return None

    return {
        "fixture_id": row[0],
        "model_version": row[1],
        "home_elo": row[2],
        "away_elo": row[3],
        "elo_diff": row[4],
        "prob_home": row[5],
        "prob_draw": row[6],
        "prob_away": row[7],
    }


def get_current_fixture_state(
    connection,
    fixture_id,
):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                f.fixture_id,
                f.status,
                f.minute,
                f.home_goals,
                f.away_goals,
                f.home_team_id,
                home_team.team_name,
                f.away_team_id,
                away_team.team_name
            FROM fixtures f

            JOIN teams home_team
                ON home_team.team_id
                = f.home_team_id

            JOIN teams away_team
                ON away_team.team_id
                = f.away_team_id

            WHERE f.fixture_id = %s;
            """,
            (
                fixture_id,
            ),
        )

        row = cursor.fetchone()

    if row is None:
        return None

    return {
        "fixture_id": row[0],
        "status": row[1],
        "minute": row[2],
        "home_goals": row[3],
        "away_goals": row[4],
        "home_team_id": row[5],
        "home_team_name": row[6],
        "away_team_id": row[7],
        "away_team_name": row[8],
    }