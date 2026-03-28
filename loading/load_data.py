"""
HomeschoolIQ — Database Loader
File: loading/load_data.py

Reads the most recent *_stats.csv from data/cleaned/, initialises
the SQLite database from sql/schema.sql, and loads all stats into
the sources and stats tables.

Run order:
  1. scraper/scrape_sources.py
  2. validation/validate_raw.py
  3. cleaning/clean_data.py
  4. loading/load_data.py   ← this file

Output:
  data/homeschooliq.db   — SQLite database consumed by the dashboard

Usage:
    python loading/load_data.py

Notes:
  - Idempotent: re-running overwrites the database cleanly.
    The database is rebuilt from scratch on every run, not appended to.
    This keeps the DB in sync with the CSV without collision handling.
  - Foreign keys are enforced via PRAGMA foreign_keys = ON.
  - source_id in the CSV is the string scraper key (e.g. 'nces_003'),
    not the integer DB primary key. This script resolves the mapping.
  - category_id in the CSV is an integer (1-5) mapping to the
    categories table seeded by schema.sql.
"""

# Last updated: 2026-03-27

import csv
import glob
import json
import logging
import os
import re
import sqlite3
from datetime import datetime, timezone

# ── Configuration ─────────────────────────────────────────────────────────────

CLEANED_DIR = "data/cleaned"
DB_PATH     = "data/homeschooliq.db"
SCHEMA_PATH = "sql/schema.sql"

# ── Logging setup ─────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def find_latest_csv(directory):
    """
    Return the path of the most recent *_stats.csv in directory.
    Alphabetical sort works because filenames use zero-padded UTC timestamps.
    Raises FileNotFoundError if none exist.
    """
    files = sorted(glob.glob(os.path.join(directory, "*_stats.csv")))
    if not files:
        raise FileNotFoundError(
            f"No *_stats.csv found in {directory}. "
            "Run cleaning/clean_data.py first."
        )
    return files[-1]


def load_csv(filepath):
    """
    Load stats CSV and return list of row dicts.
    Handles empty string → None coercion for nullable fields.
    """
    rows = []
    with open(filepath, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Coerce empty strings to None for nullable DB fields
            for key in row:
                if row[key] == "":
                    row[key] = None
            rows.append(row)
    log.info(f"Loaded {len(rows)} rows from {filepath}")
    return rows


def init_db(conn, schema_path):
    """
    Apply schema.sql to a fresh database connection.
    Uses CREATE TABLE IF NOT EXISTS so re-runs are safe.
    Categories are seeded via INSERT OR IGNORE in the schema.
    """
    with open(schema_path, encoding="utf-8") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    conn.commit()
    log.info("Schema applied and categories seeded")


def coerce_numeric(value):
    """
    Coerce a string numeric value to float, or None if missing/invalid.
    The CSV QUOTE_ALL format sometimes writes 'None' as a string.
    """
    if value is None or value in ("", "None"):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def coerce_int(value):
    """Coerce to int, or None if missing/invalid."""
    if value is None or value in ("", "None"):
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def resolve_category_id(raw_id, category_map):
    """
    The CSV stores category_id as an integer string (1–5).
    Map it to the DB integer PK from the seeded categories table.
    category_map is {1: 1, 2: 2, ...} built from the categories table.
    Returns None if the value is invalid — row will be skipped.
    """
    try:
        return category_map.get(int(float(raw_id)))
    except (ValueError, TypeError):
        return None


# ── Core load logic ───────────────────────────────────────────────────────────

def build_category_map(conn):
    """
    Return a dict mapping category integer position → DB id.
    The schema seeds categories in a fixed order:
      1→Academic, 2→Social-Emotional, 3→Cost, 4→Outcomes, 5→Critique
    This map lets the loader translate CSV category_id (1-5) to DB PKs.
    """
    cursor = conn.execute("SELECT id, name FROM categories ORDER BY id")
    rows   = cursor.fetchall()

    # Map by insertion order (id 1 = Academic, etc.)
    position_map = {}
    for db_id, name in rows:
        position_map[db_id] = db_id  # categories are seeded 1-5, so identity map
    return position_map


def upsert_source(conn, row, source_cache):
    """
    Insert source if not already seen (by URL), return its integer PK.
    source_cache: dict mapping source_url → db_id to avoid duplicate inserts.
    """
    url = row.get("source_url")
    if not url:
        return None

    if url in source_cache:
        return source_cache[url]

    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO sources
            (title, url, publisher, published_date, data_collection_year,
             credibility_tier, methodology_grade)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row.get("source_title"),
            url,
            row.get("source_publisher"),
            row.get("published_date"),
            coerce_int(row.get("data_collection_year")),
            row.get("credibility_tier"),
            row.get("methodology_grade"),
        )
    )

    # If INSERT OR IGNORE was a no-op (URL already existed), fetch existing id
    if cursor.lastrowid == 0:
        cursor = conn.execute("SELECT id FROM sources WHERE url = ?", (url,))
        db_id = cursor.fetchone()[0]
    else:
        db_id = cursor.lastrowid

    source_cache[url] = db_id
    return db_id


def insert_stat(conn, row, source_db_id, category_map):
    """
    Insert one stat row. Returns True on success, False if skipped.
    Skips rows with missing required fields or invalid category_id.
    """
    stat_text = row.get("stat_text")
    if not stat_text:
        return False

    category_id = resolve_category_id(row.get("category_id"), category_map)
    if category_id is None:
        log.warning(f"  Skipping row — invalid category_id: {row.get('category_id')!r}")
        return False

    sentiment = row.get("sentiment") or "neutral"
    era       = row.get("era")
    if not era:
        log.warning(f"  Skipping row — missing era: {stat_text[:60]!r}")
        return False

    conn.execute(
        """
        INSERT INTO stats
            (stat_text, numeric_value, unit, value_type, sample_size,
             category_id, sentiment, era, selection_bias_flag,
             semantic_cluster, conflicts_with, source_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            stat_text,
            coerce_numeric(row.get("numeric_value")),
            row.get("unit"),
            row.get("value_type"),
            coerce_int(row.get("sample_size")),
            category_id,
            sentiment,
            era,
            coerce_int(row.get("selection_bias_flag")) or 0,
            row.get("semantic_cluster"),
            coerce_int(row.get("conflicts_with")),
            source_db_id,
        )
    )
    return True


# ── Reporting ─────────────────────────────────────────────────────────────────

def print_summary(conn):
    """
    Print a post-load summary: row counts by category, tier, era, sentiment.
    This is the first real look at what the dashboard will have to work with.
    """
    log.info("")
    log.info("=" * 60)
    log.info("DATABASE SUMMARY")
    log.info("=" * 60)

    total_stats   = conn.execute("SELECT COUNT(*) FROM stats").fetchone()[0]
    total_sources = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    log.info(f"  Total stats   : {total_stats}")
    log.info(f"  Total sources : {total_sources}")

    log.info("")
    log.info("  By category:")
    rows = conn.execute("""
        SELECT c.name, COUNT(s.id) as n
        FROM stats s
        JOIN categories c ON c.id = s.category_id
        GROUP BY c.name
        ORDER BY n DESC
    """).fetchall()
    for name, count in rows:
        bar = "█" * (count // 5)
        log.info(f"    {name:<20} {count:>4}  {bar}")

    log.info("")
    log.info("  By credibility tier:")
    rows = conn.execute("""
        SELECT src.credibility_tier, COUNT(s.id) as n
        FROM stats s
        JOIN sources src ON src.id = s.source_id
        GROUP BY src.credibility_tier
        ORDER BY n DESC
    """).fetchall()
    for tier, count in rows:
        log.info(f"    {tier:<20} {count:>4}")

    log.info("")
    log.info("  By era:")
    rows = conn.execute("""
        SELECT era, COUNT(*) as n FROM stats GROUP BY era ORDER BY era
    """).fetchall()
    for era, count in rows:
        log.info(f"    {era:<20} {count:>4}")

    log.info("")
    log.info("  By sentiment:")
    rows = conn.execute("""
        SELECT sentiment, COUNT(*) as n FROM stats GROUP BY sentiment ORDER BY n DESC
    """).fetchall()
    for sentiment, count in rows:
        log.info(f"    {sentiment:<20} {count:>4}")

    log.info("")
    log.info("  Selection bias breakdown:")
    rows = conn.execute("""
        SELECT selection_bias_flag, COUNT(*) as n FROM stats GROUP BY selection_bias_flag
    """).fetchall()
    for flag, count in rows:
        label = "flagged (no controls)" if flag else "clean (controls documented)"
        log.info(f"    flag={flag}  {count:>4}  {label}")

    log.info("")
    log.info("  Category × Era (row counts):")
    rows = conn.execute("""
        SELECT c.name, s.era, COUNT(*) as n
        FROM stats s
        JOIN categories c ON c.id = s.category_id
        GROUP BY c.name, s.era
        ORDER BY c.name, s.era
    """).fetchall()
    for name, era, count in rows:
        log.info(f"    {name:<20} {era:<16} {count:>4}")

    log.info("=" * 60)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("HomeschoolIQ Loader — run started")
    log.info("=" * 60)

    csv_path = find_latest_csv(CLEANED_DIR)
    rows     = load_csv(csv_path)

    # Build fresh DB — wipe and rebuild for idempotency
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        log.info(f"Removed existing database: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    init_db(conn, SCHEMA_PATH)

    category_map = build_category_map(conn)
    source_cache = {}  # url → db integer PK

    inserted  = 0
    skipped   = 0

    for row in rows:
        source_db_id = upsert_source(conn, row, source_cache)
        if source_db_id is None:
            log.warning(f"  Skipping row — no source URL: {row.get('stat_text', '')[:50]!r}")
            skipped += 1
            continue

        ok = insert_stat(conn, row, source_db_id, category_map)
        if ok:
            inserted += 1
        else:
            skipped += 1

    conn.commit()

    log.info("")
    log.info(f"CSV rows processed : {len(rows)}")
    log.info(f"Stats inserted     : {inserted}")
    log.info(f"Rows skipped       : {skipped}")
    log.info(f"Sources loaded     : {len(source_cache)}")
    log.info(f"Database written   : {DB_PATH}")

    print_summary(conn)
    conn.close()

    return DB_PATH


if __name__ == "__main__":
    main()