-- ============================================================
-- HomeschoolIQ — Database Schema
-- File: sql/schema.sql
-- Version: 1.0.0
-- Description: Core relational schema for the HomeschoolIQ
--              data pipeline. Three tables, every field earns
--              its place. Rebuild anytime via: make rebuild
-- ============================================================

-- ⚠️  CRITICAL — FOREIGN KEY ENFORCEMENT
-- SQLite does NOT enforce foreign key constraints by default.
-- Every database connection in load_data.py must execute:
--     PRAGMA foreign_keys = ON;
-- before any INSERT or UPDATE statement. Without this, FK
-- violations will be silently accepted.
-- ============================================================


-- ------------------------------------------------------------
-- TABLE: categories
-- Purpose: Controlled vocabulary for stat classification.
--          Inserted once at setup, not scraped.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS categories (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL UNIQUE
    -- Allowed values:
    --   'Academic'         — test scores, graduation, college outcomes
    --   'Social-Emotional' — socialization, mental health, peer dynamics
    --   'Cost'             — financial cost to family, public cost per pupil
    --   'Outcomes'         — career, civic engagement, adult functioning
    --   'Critique'         — documented concerns, negative findings, risks
);


-- ------------------------------------------------------------
-- TABLE: sources
-- Purpose: Tracks every article, study, or report scraped.
--          One row per source URL. Stats reference this table.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sources (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Identity
    title                 TEXT NOT NULL,          -- Title of the article or study
    url                   TEXT NOT NULL UNIQUE,   -- Source URL — must be unique
    publisher             TEXT,                   -- e.g. 'NCES', 'Education Week'

    -- Dates — both matter, they are often different
    published_date        TEXT,                   -- Date the article was published (YYYY-MM-DD)
    data_collection_year  INTEGER,                -- Year the underlying data was actually collected
    --   NOTE: If data_collection_year is NULL, clean_data.py falls back to
    --   the year extracted from published_date as a proxy for era derivation.
    --   If both are NULL, the record is quarantined — see docs/cleaning_rules.md.

    -- Trust signals — assigned manually via sources.json
    credibility_tier      TEXT NOT NULL CHECK(credibility_tier IN ('government', 'peer_reviewed', 'advocacy', 'news')),
    methodology_grade     TEXT NOT NULL CHECK(methodology_grade IN ('A', 'B', 'C', 'D')),
    --   A — randomized or controlled study
    --   B — large sample, some controls documented
    --   C — self-selected sample, no controls
    --   D — anecdotal, opinion, or undisclosed methodology

    -- Audit
    scraped_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ------------------------------------------------------------
-- TABLE: stats
-- Purpose: Individual data points extracted from sources.
--          Each row is one claim, one number, one finding.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stats (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,

    -- The data point
    stat_text             TEXT NOT NULL,          -- Full plain-language description of the stat
    numeric_value         REAL,                   -- The number itself, if extractable
    unit                  TEXT CHECK(unit IS NULL OR unit IN ('%', 'score', 'USD', 'count')),
    value_type            TEXT CHECK(value_type IS NULL OR value_type IN (
                              'percentile', 'mean', 'median', 'rate', 'count', 'dollar', 'ratio'
                          )),
    sample_size           INTEGER,                -- Number of subjects in the study. NULL = not reported = treat as low confidence

    -- Classification
    category_id           INTEGER NOT NULL REFERENCES categories(id),
    sentiment             TEXT NOT NULL CHECK(sentiment IN ('pro_homeschool', 'pro_public', 'neutral')),
    era                   TEXT NOT NULL CHECK(era IN ('pre_2012', '2012_2019', '2020_present')),
    --   Derived from data_collection_year on the source, not published_date.
    --   These are demographically distinct populations — never aggregate across eras.
    --   See derivation fallback rules in docs/cleaning_rules.md.

    -- Bias and validity flags
    selection_bias_flag   INTEGER NOT NULL DEFAULT 0 CHECK(selection_bias_flag IN (0, 1)),
    --   0 = control group documented or not applicable
    --   1 = no documented control group
    --   Rule: auto-set to 1 for any source with methodology_grade C or D
    --         unless explicitly overridden in clean_data.py with a comment.

    semantic_cluster      TEXT CHECK(
                              semantic_cluster IS NULL OR
                              semantic_cluster IN (
                                  'peer_interaction', 'clique_formation', 'adult_outcomes',
                                  'anxiety_rates', 'conflict_resolution'
                              )
                          ),
    --   Social-Emotional sub-label only. NULL for all other categories.
    --   Cross-field rule: if category != 'Social-Emotional', semantic_cluster must be NULL.
    --   Enforced in validate_raw.py — see docs/cleaning_rules.md.

    -- Conflict tracking — links contradictory stats across sources
    -- ⚠️  INSERTION ORDER: when loading two conflicting stats, insert stat A first,
    --   retrieve its id, then insert stat B with conflicts_with = stat_A.id.
    --   Dashboard queries must use WHERE stats.id < conflicts_with to avoid
    --   returning duplicate pairs. See docs/cleaning_rules.md.
    conflicts_with        INTEGER REFERENCES stats(id),

    -- Comparison fields
    -- metric_key groups rows measuring the same thing across subjects.
    -- subject identifies who the number describes.
    -- Together they enable side-by-side dashboard comparisons:
    --   SELECT metric_key, subject, AVG(numeric_value)
    --   FROM stats WHERE metric_key = 'per_pupil_cost'
    --   GROUP BY subject
    metric_key            TEXT,
    --   Controlled vocabulary — see METRIC_KEYS in clean_data.py.
    --   NULL = metric not identified (sentence-level stat only).

    subject               TEXT CHECK(
                              subject IS NULL OR subject IN (
                                  'homeschool', 'public_school',
                                  'black_homeschool', 'black_public',
                                  'hispanic_homeschool', 'hispanic_public',
                                  'all_students', 'general_population'
                              )
                          ),
    --   Who the numeric_value describes.
    --   NULL = subject not identified from sentence context.

    -- Provenance
    source_id             INTEGER NOT NULL REFERENCES sources(id),

    -- Audit
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ------------------------------------------------------------
-- INDEXES
-- Purpose: Support dashboard filter queries on the most
--          frequently queried stats columns.
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_stats_sentiment   ON stats(sentiment);
CREATE INDEX IF NOT EXISTS idx_stats_era         ON stats(era);
CREATE INDEX IF NOT EXISTS idx_stats_category    ON stats(category_id);
CREATE INDEX IF NOT EXISTS idx_stats_source      ON stats(source_id);
CREATE INDEX IF NOT EXISTS idx_stats_metric      ON stats(metric_key);
CREATE INDEX IF NOT EXISTS idx_stats_subject     ON stats(subject);


-- ============================================================
-- SEED: categories
-- Insert the controlled vocabulary once at setup.
-- ============================================================
INSERT OR IGNORE INTO categories (name) VALUES
    ('Academic'),
    ('Social-Emotional'),
    ('Cost'),
    ('Outcomes'),
    ('Critique');