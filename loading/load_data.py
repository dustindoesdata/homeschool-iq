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
  - Foreign keys enforced via PRAGMA foreign_keys = ON.
  - source_id in the CSV is the string scraper key (e.g. 'nces_003'),
    not the integer DB primary key. This script resolves the mapping.
  - metric_key and subject columns support dashboard comparison queries.
"""

# Last updated: 2026-03-27

import csv
import glob
import logging
import os
import sqlite3

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
    files = sorted(glob.glob(os.path.join(directory, "*_stats.csv")))
    if not files:
        raise FileNotFoundError(
            f"No *_stats.csv found in {directory}. "
            "Run cleaning/clean_data.py first."
        )
    return files[-1]


def load_csv(filepath):
    rows = []
    with open(filepath, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for key in row:
                if row[key] == "" or row[key] == "None":
                    row[key] = None
            rows.append(row)
    log.info(f"Loaded {len(rows)} rows from {filepath}")
    return rows


def init_db(conn, schema_path):
    with open(schema_path, encoding="utf-8") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    conn.commit()
    log.info("Schema applied and categories seeded")


def coerce_numeric(value):
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def coerce_int(value):
    if value is None:
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def build_category_map(conn):
    cursor = conn.execute("SELECT id FROM categories ORDER BY id")
    rows   = cursor.fetchall()
    return {row[0]: row[0] for row in rows}


def upsert_source(conn, row, source_cache):
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

    if cursor.lastrowid == 0:
        cursor = conn.execute("SELECT id FROM sources WHERE url = ?", (url,))
        db_id = cursor.fetchone()[0]
    else:
        db_id = cursor.lastrowid

    source_cache[url] = db_id
    return db_id


def insert_stat(conn, row, source_db_id, category_map):
    stat_text = row.get("stat_text")
    if not stat_text:
        return False

    try:
        category_id = category_map.get(int(float(row.get("category_id", 0))))
    except (ValueError, TypeError):
        category_id = None

    if category_id is None:
        log.warning(f"  Skipping — invalid category_id: {row.get('category_id')!r}")
        return False

    era = row.get("era")
    if not era:
        log.warning(f"  Skipping — missing era: {stat_text[:60]!r}")
        return False

    conn.execute(
        """
        INSERT INTO stats
            (stat_text, numeric_value, unit, value_type, sample_size,
             category_id, sentiment, era, selection_bias_flag,
             semantic_cluster, conflicts_with,
             metric_key, subject,
             source_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            stat_text,
            coerce_numeric(row.get("numeric_value")),
            row.get("unit"),
            row.get("value_type"),
            coerce_int(row.get("sample_size")),
            category_id,
            row.get("sentiment") or "neutral",
            era,
            coerce_int(row.get("selection_bias_flag")) or 0,
            row.get("semantic_cluster"),
            coerce_int(row.get("conflicts_with")),
            row.get("metric_key"),
            row.get("subject"),
            source_db_id,
        )
    )
    return True


# ── Reporting ─────────────────────────────────────────────────────────────────

def print_summary(conn):
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
        SELECT c.name, COUNT(s.id)
        FROM stats s JOIN categories c ON c.id = s.category_id
        GROUP BY c.name ORDER BY COUNT(s.id) DESC
    """).fetchall()
    for name, count in rows:
        log.info(f"    {name:<22} {count:>4}")

    log.info("")
    log.info("  By metric_key (top 15):")
    rows = conn.execute("""
        SELECT metric_key, COUNT(*) as n, COUNT(DISTINCT subject) as subjects
        FROM stats WHERE metric_key IS NOT NULL
        GROUP BY metric_key ORDER BY n DESC LIMIT 15
    """).fetchall()
    for metric, count, subjects in rows:
        log.info(f"    {metric:<35} {count:>4} rows  {subjects} subjects")

    log.info("")
    log.info("  By subject:")
    rows = conn.execute("""
        SELECT subject, COUNT(*) as n FROM stats
        WHERE subject IS NOT NULL
        GROUP BY subject ORDER BY n DESC
    """).fetchall()
    for subject, count in rows:
        log.info(f"    {subject:<25} {count:>4}")

    log.info("")
    log.info("  Comparison-ready (metric_key + both subjects):")
    rows = conn.execute("""
        SELECT metric_key,
               GROUP_CONCAT(DISTINCT subject) as subjects,
               COUNT(*) as n
        FROM stats
        WHERE metric_key IS NOT NULL AND subject IS NOT NULL
        GROUP BY metric_key
        HAVING COUNT(DISTINCT subject) >= 2
        ORDER BY n DESC
    """).fetchall()
    if rows:
        for metric, subjects, count in rows:
            log.info(f"    {metric:<35} [{subjects}]  {count} rows")
    else:
        log.info("    None yet — run cleaner against full source set")

    log.info("")
    log.info("  By credibility tier:")
    rows = conn.execute("""
        SELECT src.credibility_tier, COUNT(s.id)
        FROM stats s JOIN sources src ON src.id = s.source_id
        GROUP BY src.credibility_tier ORDER BY COUNT(s.id) DESC
    """).fetchall()
    for tier, count in rows:
        log.info(f"    {tier:<22} {count:>4}")

    log.info("")
    log.info("  Selection bias breakdown:")
    rows = conn.execute("""
        SELECT selection_bias_flag, COUNT(*) FROM stats GROUP BY selection_bias_flag
    """).fetchall()
    for flag, count in rows:
        label = "flagged" if flag else "clean"
        log.info(f"    flag={flag}  {count:>4}  {label}")

    log.info("=" * 60)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("HomeschoolIQ Loader — run started")
    log.info("=" * 60)

    csv_path = find_latest_csv(CLEANED_DIR)
    rows     = load_csv(csv_path)

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        log.info(f"Removed existing database: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    init_db(conn, SCHEMA_PATH)

    category_map = build_category_map(conn)
    source_cache = {}

    inserted = 0
    skipped  = 0

    for row in rows:
        source_db_id = upsert_source(conn, row, source_cache)
        if source_db_id is None:
            skipped += 1
            continue
        if insert_stat(conn, row, source_db_id, category_map):
            inserted += 1
        else:
            skipped += 1

    conn.commit()

    log.info(f"\nCSV rows processed : {len(rows)}")
    log.info(f"Stats inserted     : {inserted}")
    log.info(f"Rows skipped       : {skipped}")
    log.info(f"Sources loaded     : {len(source_cache)}")
    log.info(f"Database written   : {DB_PATH}")

    print_summary(conn)
    conn.close()

    return DB_PATH


if __name__ == "__main__":
    main()