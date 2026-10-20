-- Run once:  CREATE DATABASE tennis_db;  then connect to it and run this file.

-- ===================== Competitions =====================
CREATE TABLE IF NOT EXISTS categories (
    category_id   VARCHAR(50)  PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS competitions (
    competition_id   VARCHAR(50)  PRIMARY KEY,
    competition_name VARCHAR(100) NOT NULL,
    parent_id        VARCHAR(50),
    type             VARCHAR(20)  NOT NULL,
    gender           VARCHAR(10)  NOT NULL,
    category_id      VARCHAR(50)  REFERENCES categories(category_id),
    level            VARCHAR(30)  -- extra: grand_slam, atp_1000, wta_500 ... (PDF asks for a 'level' filter)
);

-- ===================== Complexes & venues =====================
CREATE TABLE IF NOT EXISTS complexes (
    complex_id   VARCHAR(50)  PRIMARY KEY,
    complex_name VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS venues (
    venue_id     VARCHAR(50)  PRIMARY KEY,
    venue_name   VARCHAR(100) NOT NULL,
    city_name    VARCHAR(100) NOT NULL,
    country_name VARCHAR(100) NOT NULL,
    country_code CHAR(3)      NOT NULL,
    timezone     VARCHAR(100) NOT NULL,
    complex_id   VARCHAR(50)  REFERENCES complexes(complex_id)
);

-- ===================== Doubles rankings =====================
CREATE TABLE IF NOT EXISTS competitors (
    competitor_id VARCHAR(50)  PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    country       VARCHAR(100) NOT NULL,
    country_code  CHAR(3)      NOT NULL,
    abbreviation  VARCHAR(10)  NOT NULL
);

-- ranking_year / ranking_week / gender are extra columns (not in the PDF) so
-- several weeks can be stored and the app can filter by Year/Week/Gender.
CREATE TABLE IF NOT EXISTS competitor_rankings (
    rank_id             SERIAL PRIMARY KEY,
    "rank"              INT NOT NULL,
    movement            INT NOT NULL,
    points              INT NOT NULL,
    competitions_played INT NOT NULL,
    competitor_id       VARCHAR(50) REFERENCES competitors(competitor_id),
    ranking_year        INT,
    ranking_week        INT,
    gender              VARCHAR(10),
    UNIQUE (competitor_id, ranking_year, ranking_week, gender)
);

-- ===================== Indexes =====================
CREATE INDEX IF NOT EXISTS idx_comp_category ON competitions(category_id);
CREATE INDEX IF NOT EXISTS idx_comp_parent   ON competitions(parent_id);
CREATE INDEX IF NOT EXISTS idx_comp_type     ON competitions(type);
CREATE INDEX IF NOT EXISTS idx_comp_level    ON competitions(level);
CREATE INDEX IF NOT EXISTS idx_venue_complex ON venues(complex_id);
CREATE INDEX IF NOT EXISTS idx_venue_country ON venues(country_name);
CREATE INDEX IF NOT EXISTS idx_rank_comp     ON competitor_rankings(competitor_id);
CREATE INDEX IF NOT EXISTS idx_rank_rank     ON competitor_rankings("rank");
CREATE INDEX IF NOT EXISTS idx_competitor_country ON competitors(country);

-- ===================== View: latest week per gender =====================
CREATE OR REPLACE VIEW v_latest_rankings AS
SELECT r.rank_id, r."rank", r.movement, r.points, r.competitions_played,
       r.ranking_year, r.ranking_week, r.gender,
       c.competitor_id, c.name, c.country, c.country_code, c.abbreviation
FROM competitor_rankings r
JOIN competitors c ON c.competitor_id = r.competitor_id
WHERE (r.gender, r.ranking_year, r.ranking_week) IN (
    SELECT gender, ranking_year, ranking_week FROM (
        SELECT gender, ranking_year, ranking_week,
               ROW_NUMBER() OVER (PARTITION BY gender
                                  ORDER BY ranking_year DESC, ranking_week DESC) AS rn
        FROM (SELECT DISTINCT gender, ranking_year, ranking_week
              FROM competitor_rankings) d
    ) x WHERE rn = 1
);
