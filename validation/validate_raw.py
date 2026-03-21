"""
HomeschoolIQ — Raw Data Validator
File: validation/validate_raw.py

Reads the most recent scrape output from data/raw/, validates every
record against quality rules, and writes:
  - data/logs/<timestamp>_validation.json  — full validation report
  - data/quarantine/<timestamp>_<id>.json  — one file per failed record

Only records that pass all checks proceed to the cleaning pipeline.

Usage:
    python validation/validate_raw.py
    — or —
    make validate
"""

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

# Minimum characters for a record to be considered non-empty
MIN_CHAR_COUNT = 500

# If more than this fraction of records from one source fail, halt
QUARANTINE_THRESHOLD = 0.20

# ── Logging setup ─────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_latest_scrape():
    """
    Find and load the most recent JSON file in data/raw/.
    Returns (filepath, records) or raises if none found.
    """
    files = sorted(glob.glob(os.path.join(RAW_DIR, "*.json")))
    if not files:
        raise FileNotFoundError(
            f"No scrape output found in {RAW_DIR}. "
            "Run 'make scrape' first."
        )
    filepath = files[-1]
    log.info(f"Loading scrape output: {filepath}")
    with open(filepath) as f:
        records = json.load(f)
    log.info(f"Loaded {len(records)} records")
    return filepath, records


def load_sources():
    """Load sources.json and return a dict keyed by source_id."""
    with open(SOURCES_FILE) as f:
        data = json.load(f)
    return {s["id"]: s for s in data["sources"]}


# ── Validation rules ──────────────────────────────────────────────────────────

def validate_record(record, sources):
    """
    Run all validation checks on a single record.
    Returns a list of failure reasons. Empty list = passed.
    """
    failures = []
    source_id = record.get("source_id", "unknown")

    # Rule: only validate successful scrapes
    if record.get("status") != "success":
        return []

    # Rule 1 — required fields must be present and non-empty
    required = [
        "source_id", "title", "url", "publisher",
        "credibility_tier", "methodology_grade",
        "raw_text", "scraped_at"
    ]
    for field in required:
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
    if source_id not in sources:
        failures.append(
            f"source_id '{source_id}' not found in sources.json"
        )

    return failures


def check_balance(records, sources):
    """
    Assert no single credibility tier exceeds 40% of successful sources.
    Logs a warning but does not halt — balance is a sources.json concern.
    """
    successful_ids = {
        r["source_id"] for r in records
        if r.get("status") == "success"
    }
    tier_counts = {}
    for sid in successful_ids:
        if sid in sources:
            tier = sources[sid]["credibility_tier"]
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

    total = len(successful_ids)
    if total == 0:
        return

    log.info("Source balance in this run:")
    for tier, count in sorted(tier_counts.items()):
        pct = count / total
        flag = "  ⚠️  EXCEEDS 40%" if pct > 0.40 else ""
        log.info(f"  {tier:<15} {count}/{total} ({pct:.0%}){flag}")


# ── Output writers ─────────────────────────────────────────────────────────────

def quarantine_record(record, reasons, timestamp):
    """Write a failed record to data/quarantine/."""
    os.makedirs(QUARANTINE_DIR, exist_ok=True)
    source_id = record.get("source_id", "unknown")
    filename = f"{timestamp}_{source_id}.json"
    filepath = os.path.join(QUARANTINE_DIR, filename)
    output = {
        "quarantined_at": datetime.now(timezone.utc).isoformat(),
        "reasons": reasons,
        "record": record
    }
    with open(filepath, "w") as f:
        json.dump(output, f, indent=2)
    log.warning(f"  Quarantined → {filepath}")


def write_validation_report(report, timestamp):
    """Write the full validation report to data/logs/."""
    os.makedirs(LOG_DIR, exist_ok=True)
    filename = f"{timestamp}_validation.json"
    filepath = os.path.join(LOG_DIR, filename)
    with open(filepath, "w") as f:
        json.dump(report, f, indent=2)
    log.info(f"Validation report written to {filepath}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    timestamp = datetime.now(timezone.utc).strftime("%Y_%m_%d_%H%M%S")

    log.info("=" * 60)
    log.info("HomeschoolIQ Validator — run started")
    log.info("=" * 60)

    # Load data
    scrape_file, records = load_latest_scrape()
    sources = load_sources()

    # Summarise what came in from the scraper
    total     = len(records)
    succeeded = sum(1 for r in records if r.get("status") == "success")
    failed    = sum(1 for r in records if r.get("status") == "failed")
    skipped   = sum(1 for r in records if r.get("status") == "skipped")

    log.info(
        f"\nScrape summary: {succeeded} succeeded, "
        f"{failed} failed, {skipped} skipped"
    )

    # Check source balance
    check_balance(records, sources)

    # Validate each successful record
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

        failures = validate_record(record, sources)

        if failures:
            log.warning(
                f"  [{source_id}] FAILED — {', '.join(failures)}"
            )
            quarantine_record(record, failures, timestamp)
            quarantined.append({
                "source_id": source_id,
                "reasons": failures
            })
        else:
            log.info(f"  [{source_id}] ✓ passed")
            passed.append(record)

    # Build and write report
    report = {
        "validated_at":      datetime.now(timezone.utc).isoformat(),
        "scrape_file":       scrape_file,
        "total_records":     total,
        "succeeded":         succeeded,
        "failed_scrapes":    failed,
        "skipped_scrapes":   skipped,
        "passed":            len(passed),
        "quarantined":       len(quarantined),
        "quarantine_detail": quarantined
    }
    write_validation_report(report, timestamp)

    # Write validated records for the cleaning pipeline
    os.makedirs("data/cleaned", exist_ok=True)
    clean_path = os.path.join(
        "data/cleaned",
        f"{timestamp}_validated.json"
    )
    with open(clean_path, "w") as f:
        json.dump(passed, f, indent=2)
    log.info(f"Validated records written to {clean_path}")

    # Summary
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