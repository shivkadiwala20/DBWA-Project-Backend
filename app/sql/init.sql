-- ============================================================
-- DBW Project V3: Participant Count Schema
-- Each accident row stores HOW MANY of each participant type
-- ============================================================

-- Data sources must come first because accidents references it
CREATE TABLE IF NOT EXISTS data_sources (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    origin_url      TEXT,
    file_name       VARCHAR(255),
    license         VARCHAR(100) DEFAULT 'dl-de/by-2-0',
    retrieved_at    TIMESTAMPTZ  DEFAULT NOW(),
    records_loaded  INT,
    records_skipped INT,
    status          VARCHAR(20)  DEFAULT 'pending'
                    CHECK (status IN ('pending','running','success','error')),
    error_notes     TEXT,
    checksum        VARCHAR(64)
);

-- Regions: German administrative units identified by AGS code
CREATE TABLE IF NOT EXISTS regions (
    id          SERIAL PRIMARY KEY,
    ags         VARCHAR(8)  NOT NULL UNIQUE,
    name        VARCHAR(255) NOT NULL,
    region_type VARCHAR(20) NOT NULL CHECK (region_type IN ('state','district','municipality')),
    state_ags   VARCHAR(2),
    state_name  VARCHAR(100),
    population  BIGINT,
    area_km2    NUMERIC(10,2)
);

CREATE INDEX IF NOT EXISTS idx_regions_state_ags ON regions(state_ags);
CREATE INDEX IF NOT EXISTS idx_regions_type      ON regions(region_type);

-- ============================================================
-- Accidents: one row per accident — participant types as COUNTS
-- cyclists INT   = number of cyclists involved (0 or 1 from source data)
-- pedestrians INT = number of pedestrians involved
-- cars INT       = number of cars involved
-- etc.
-- Different from boolean flags (Version 1) and separate participant rows (Version 2)
-- ============================================================
CREATE TABLE IF NOT EXISTS accidents (
    id          BIGSERIAL PRIMARY KEY,
    source_id   VARCHAR(60),
    year        SMALLINT NOT NULL,
    month       SMALLINT,
    hour        SMALLINT,
    weekday     SMALLINT,
    severity    SMALLINT NOT NULL CHECK (severity IN (1,2,3)),
    accident_type SMALLINT,
    road_type   SMALLINT,
    light_cond  SMALLINT CHECK (light_cond IN (0,1,2)),
    lon         DOUBLE PRECISION,
    lat         DOUBLE PRECISION,
    ags         VARCHAR(8),
    state_ags   VARCHAR(2),
    -- PARTICIPANT COUNTS (0 or 1 per Unfallatlas source, stored as INT for semantics)
    cyclists        INT NOT NULL DEFAULT 0,
    cars            INT NOT NULL DEFAULT 0,
    pedestrians     INT NOT NULL DEFAULT 0,
    motorcycles     INT NOT NULL DEFAULT 0,
    trucks          INT NOT NULL DEFAULT 0,
    others          INT NOT NULL DEFAULT 0,
    total_participants INT GENERATED ALWAYS AS
        (cyclists + cars + pedestrians + motorcycles + trucks + others) STORED,
    data_source_id  INT REFERENCES data_sources(id),
    UNIQUE(source_id, year)
);

CREATE INDEX IF NOT EXISTS idx_accidents_year       ON accidents(year);
CREATE INDEX IF NOT EXISTS idx_accidents_state_ags  ON accidents(state_ags);
CREATE INDEX IF NOT EXISTS idx_accidents_severity   ON accidents(severity);
CREATE INDEX IF NOT EXISTS idx_accidents_year_state ON accidents(year, state_ags);

-- Statistics: cross-source indicator values per region per year
CREATE TABLE IF NOT EXISTS statistics (
    id           SERIAL PRIMARY KEY,
    ags          VARCHAR(8)   NOT NULL,
    indicator    VARCHAR(60)  NOT NULL,
    year         SMALLINT     NOT NULL,
    value        NUMERIC(15,4) NOT NULL,
    source_name  VARCHAR(255),
    UNIQUE(ags, indicator, year)
);

CREATE INDEX IF NOT EXISTS idx_stats_ags       ON statistics(ags);
CREATE INDEX IF NOT EXISTS idx_stats_indicator ON statistics(indicator);
