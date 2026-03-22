"""
HomeschoolIQ — Raw Data Validator
File: validation/validate_raw.py

Reads the most recent scrape output from data/raw/, validates every
record against quality rules, and writes:
  - data/logs/<timestamp>_validation.json  — full validation report
  - data/quarantine/<timestamp>_<id>.json  — one file per failed record

Records that pass all checks are written to data/cleaned/ for the
cleaning pipeline. Records that fail are quarantined, not deleted.

Usage:
    python validation/validate_raw.py
    — or —
    make validate
"""

# Last updated: 2026-03-21

import json
import os
import glob
import logging
from datetime import datetime, timezone

# ── Configuration ─────────────────────────────────────────────────────────────

RAW_DIR        = "data/raw"
LOG_DIR        = "data/logs"
QUARANTINE_DIR = "data/quarantine"
SOURCES_FILE   = "scraper/sources.json"
CLEANED_DIR    = "data/cleaned"

# Minimum characters for a scraped page to be considered non-empty
MIN_CHAR_COUNT = 500

# If more than this fraction of records from one source fail validation,
# the pipeline halts rather than proceeding with partial data.
# Enforced in check_quarantine_threshold().
QUARANTINE_THRESHOLD = 0.20

# ── Logging setup ─────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def find_latest_file(directory, pattern):
    """
    Return the path of the most recent file matching pattern in directory.
    Sort is alphabetical — works correctly because filenames use
    zero-padded UTC timestamps (YYYY_MM_DD_HHMMSS).
    Raises FileNotFoundError if no matching file exists.
    """
    files = sorted(glob.glob(os.path.join(directory, pattern)))
    if not files:
        raise FileNotFoundError(
            f"No file matching '{pattern}' found in {directory}."
        )
    return files[-1]


def load_latest_scrape():
    """
    Find and load the most recent JSON file in data/raw/.
    Returns (scrape_filepath, records).
    """
    scrape_filepath = find_latest_file(RAW_DIR, "????_??_??_??????.json")
    log.info(f"Loading scrape output: {scrape_filepath}")
    with open(scrape_filepath) as f:
        records = json.load(f)
    log.info(f"Loaded {len(records)} records")
    return scrape_filepath, records


def load_source_registry():
    """
    Load sources.json and return a dict keyed by source_id.
    Named 'registry' to distinguish from the scrape records loaded
    elsewhere — both are called 'sources' in common usage but refer
    to different data shapes.
    Note: load_source_registry() is duplicated in clean_data.py.
    Both should be moved to a shared utils module in a future refactor.
    """
    with open(SOURCES_FILE) as f:
        data = json.load(f)
    return {s["id"]: s for s in data["sources"]}


# ── Validation rules ──────────────────────────────────────────────────────────

def validate_record(record, source_registry):
    """
    Run all validation checks on a single scraped record.
    Returns a list of failure reasons. Empty list = passed.
    Only successful scrapes are validated — failed/skipped are ignored.
    """
    failures  = []
    source_id = record.get("source_id", "unknown")

    if record.get("status") != "success":
        return []

    # Rule 1 — required fields must be present and non-empty
    required_fields = [
        "source_id", "title", "url", "publisher",
        "credibility_tier", "methodology_grade",
        "expected_sentiment_skew", "raw_text", "scraped_at"
    ]
    for field in required_fields:
        if not record.get(field):
            failures.append(f"missing required field: {field}")

    # Rule 2 — credibility_tier must be a known value
    valid_tiers = {"government", "peer_reviewed", "advocacy", "news"}
    tier = record.get("credibility_tier", "")
    if tier and tier not in valid_tiers:
        failures.append(f"invalid credibility_tier: '{tier}'")

    # Rule 3 — methodology_grade must be A, B, C, or D
    valid_grades = {"A", "B", "C", "D"}
    grade = record.get("methodology_grade", "")
    if grade and grade not in valid_grades:
        failures.append(f"invalid methodology_grade: '{grade}'")

    # Rule 4 — raw_text must meet minimum length
    char_count = record.get("char_count", 0)
    if char_count < MIN_CHAR_COUNT:
        failures.append(
            f"raw_text too short: {char_count} chars "
            f"(minimum {MIN_CHAR_COUNT})"
        )

    # Rule 5 — source_id must exist in sources.json
    if source_id not in source_registry:
        failures.append(
            f"source_id '{source_id}' not found in sources.json"
        )

    return failures


def check_source_balance(records, source_registry):
    """
    Log credibility tier distribution across successful sources.
    Warns if any single tier exceeds 40% of the successful corpus.
    Does not halt — balance is a sources.json concern, not a per-record one.
    """
    successful_ids = {
        r["source_id"] for r in records
        if r.get("status") == "success"
    }
    tier_counts = {}
    for sid in successful_ids:
        if sid in source_registry:
            tier = source_registry[sid]["credibility_tier"]
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

    total = len(successful_ids)
    if total == 0:
        return

    log.info("Source balance in this run:")
    for tier, count in sorted(tier_counts.items()):
        pct  = count / total
        flag = "  ⚠️  EXCEEDS 40%" if pct > 0.40 else ""
        log.info(f"  {tier:<15} {count}/{total} ({pct:.0%}){flag}")


def check_quarantine_threshold(quarantined, total_successful):
    """
    Halt the pipeline if the quarantine rate exceeds QUARANTINE_THRESHOLD.
    Implements Cleaning Rule 8 from docs/cleaning_rules.md.
    """
    if total_successful == 0:
        return
    quarantine_rate = len(quarantined) / total_successful
    if quarantine_rate > QUARANTINE_THRESHOLD:
        raise RuntimeError(
            f"Quarantine rate {quarantine_rate:.0%} exceeds threshold "
            f"{QUARANTINE_THRESHOLD:.0%}. "
            f"{len(quarantined)} of {total_successful} records failed. "
            "Investigate before rerunning."
        )


# ── Output writers ─────────────────────────────────────────────────────────────

def write_quarantine_record(record, failure_reasons, timestamp):
    """Write a failed record to data/quarantine/ for manual review."""
    os.makedirs(QUARANTINE_DIR, exist_ok=True)
    source_id = record.get("source_id", "unknown")
    filepath  = os.path.join(
        QUARANTINE_DIR, f"{timestamp}_{source_id}.json"
    )
    output = {
        "quarantined_at":  datetime.now(timezone.utc).isoformat(),
        "failure_reasons": failure_reasons,
        "record":          record
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    log.warning(f"  Quarantined → {filepath}")


def write_validation_report(report, timestamp):
    """Write the full validation report to data/logs/."""
    os.makedirs(LOG_DIR, exist_ok=True)
    filepath = os.path.join(LOG_DIR, f"{timestamp}_validation.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    log.info(f"Validation report written to {filepath}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    timestamp = datetime.now(timezone.utc).strftime("%Y_%m_%d_%H%M%S")

    log.info("=" * 60)
    log.info("HomeschoolIQ Validator — run started")
    log.info("=" * 60)

    scrape_filepath, records = load_latest_scrape()
    source_registry          = load_source_registry()

    total     = len(records)
    succeeded = sum(1 for r in records if r.get("status") == "success")
    failed    = sum(1 for r in records if r.get("status") == "failed")
    skipped   = sum(1 for r in records if r.get("status") == "skipped")

    log.info(
        f"\nScrape summary: {succeeded} succeeded, "
        f"{failed} failed, {skipped} skipped"
    )

    check_source_balance(records, source_registry)

    log.info("\nValidating records...")
    passed      = []
    quarantined = []

    for record in records:
        source_id = record.get("source_id", "unknown")

        if record.get("status") != "success":
            log.info(
                f"  [{source_id}] Skipping — "
                f"status={record.get('status')}"
            )
            continue

        failure_reasons = validate_record(record, source_registry)

        if failure_reasons:
            log.warning(
                f"  [{source_id}] FAILED — "
                f"{', '.join(failure_reasons)}"
            )
            write_quarantine_record(record, failure_reasons, timestamp)
            quarantined.append({
                "source_id":       source_id,
                "failure_reasons": failure_reasons
            })
        else:
            log.info(f"  [{source_id}] ✓ passed")
            passed.append(record)

    # Enforce quarantine threshold — halts if failure rate is too high
    check_quarantine_threshold(quarantined, succeeded)

    report = {
        "validated_at":       datetime.now(timezone.utc).isoformat(),
        "scrape_filepath":    scrape_filepath,
        "total_records":      total,
        "scrape_succeeded":   succeeded,
        "scrape_failed":      failed,
        "scrape_skipped":     skipped,
        "validation_passed":  len(passed),
        "validation_failed":  len(quarantined),
        "quarantine_detail":  quarantined
    }
    write_validation_report(report, timestamp)

    os.makedirs(CLEANED_DIR, exist_ok=True)
    validated_output_path = os.path.join(
        CLEANED_DIR, f"{timestamp}_validated.json"
    )
    with open(validated_output_path, "w", encoding="utf-8") as f:
        json.dump(passed, f, indent=2, ensure_ascii=False)
    log.info(f"Validated records written to {validated_output_path}")

    log.info("\n" + "=" * 60)
    log.info("Validation complete")
    log.info(f"  Passed     : {len(passed)}")
    log.info(f"  Quarantined: {len(quarantined)}")
    log.info("=" * 60)

    if quarantined:
        log.warning(
            f"{len(quarantined)} record(s) quarantined. "
            "Check data/quarantine/ for details."
        )

    return len(passed)


if __name__ == "__main__":
    main()