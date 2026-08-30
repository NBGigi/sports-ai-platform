CREATE TABLE leagues (
    league_id INTEGER PRIMARY KEY,
    league_name VARCHAR(100) NOT NULL,
    tier INTEGER NOT NULL
);


CREATE TABLE teams (
    team_id INTEGER PRIMARY KEY,
    team_name VARCHAR(100) NOT NULL
);


CREATE TABLE fixtures (
    fixture_id INTEGER PRIMARY KEY,
    date TIMESTAMPTZ NOT NULL,

    league_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    round VARCHAR(100),

    status VARCHAR(50) NOT NULL,
    minute INTEGER,

    home_team_id INTEGER NOT NULL,
    away_team_id INTEGER NOT NULL,

    home_goals INTEGER,
    away_goals INTEGER,

    FOREIGN KEY (league_id)
        REFERENCES leagues(league_id),

    FOREIGN KEY (home_team_id)
        REFERENCES teams(team_id),

    FOREIGN KEY (away_team_id)
        REFERENCES teams(team_id)
);


CREATE TABLE fixture_statistics (
    fixture_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,

    shots_on_goal INTEGER,
    shots_off_goal INTEGER,
    total_shots INTEGER,
    blocked_shots INTEGER,
    shots_inside_box INTEGER,
    shots_outside_box INTEGER,
    corners INTEGER,
    possession INTEGER,
    yellow_cards INTEGER,
    red_cards INTEGER,
    xg DOUBLE PRECISION,

    PRIMARY KEY (fixture_id, team_id),

    FOREIGN KEY (fixture_id)
        REFERENCES fixtures(fixture_id),

    FOREIGN KEY (team_id)
        REFERENCES teams(team_id)
);

CREATE TABLE team_external_ids (
    team_id INTEGER NOT NULL,
    provider VARCHAR(50) NOT NULL,
    external_id INTEGER NOT NULL,

    PRIMARY KEY (team_id, provider),

    FOREIGN KEY (team_id)
        REFERENCES teams(team_id)
);