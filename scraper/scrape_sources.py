"""
HomeschoolIQ — Web Scraper
File: scraper/scrape_sources.py

Reads active sources from scraper/sources.json, fetches each page,
extracts the visible text, and writes timestamped output to data/raw/.
A run manifest is written to data/logs/ on every run.

Usage:
    python scraper/scrape_sources.py
    — or —
    make scrape
"""

import json
import os
import time
import logging
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# ── Configuration ─────────────────────────────────────────────────────────────

SOURCES_FILE   = "scraper/sources.json"
OUTPUT_DIR     = "data/raw"
LOG_DIR        = "data/logs"
DELAY_SECONDS  = 2       # pause between requests — be polite
MAX_RETRIES    = 3       # retry a failed request this many times
RETRY_DELAY    = 5       # seconds to wait before retrying
REQUEST_TIMEOUT = 15     # seconds before giving up on a request

HEADERS = {
    "User-Agent": (
        "HomeschoolIQ-Research-Bot/1.0 "
        "(https://github.com/dustindoesdata/homeschool-iq; "
        "educational research project)"
    )
}

# ── Logging setup ─────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)


# ── Core functions ─────────────────────────────────────────────────────────────

def load_sources(filepath):
    """Load and return active sources from sources.json."""
    with open(filepath, "r") as f:
        data = json.load(f)

    all_sources = data["sources"]
    active = [s for s in all_sources if s.get("active", False)]
    log.info(f"Loaded {len(active)} active sources from {filepath}")
    return active


def fetch_page(url, retries=MAX_RETRIES):
    """
    Fetch a URL with retry logic.
    Returns the response object on success, None on failure.
    """
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            log.warning(f"  HTTP error on attempt {attempt}/{retries}: {e}")
        except requests.exceptions.ConnectionError as e:
            log.warning(f"  Connection error on attempt {attempt}/{retries}: {e}")
        except requests.exceptions.Timeout:
            log.warning(f"  Timeout on attempt {attempt}/{retries}")
        except requests.exceptions.RequestException as e:
            log.warning(f"  Request failed on attempt {attempt}/{retries}: {e}")

        if attempt < retries:
            log.info(f"  Retrying in {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)

    log.error(f"  All {retries} attempts failed for {url}")
    return None


def extract_text(html):
    """
    Parse HTML and return clean visible text.
    Strips scripts, styles, and nav elements.
    """
    soup = BeautifulSoup(html, "lxml")

    # Remove elements that are never useful
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()

    # Get visible text, collapse whitespace
    text = soup.get_text(separator=" ", strip=True)
    text = " ".join(text.split())
    return text


def scrape_source(source):
    """
    Scrape a single source. Returns a result dict.
    status is 'success', 'failed', or 'skipped'.
    """
    source_id = source["id"]
    url = source["url"]
    scrape_mode = source.get("scrape_mode", "html")

    if scrape_mode != "html":
        log.info(f"  [{source_id}] Skipping — scrape_mode is '{scrape_mode}'")
        return {
            "source_id": source_id,
            "status": "skipped",
            "reason": f"scrape_mode={scrape_mode}",
            "url": url
        }

    log.info(f"  [{source_id}] Fetching {url}")
    response = fetch_page(url)

    if response is None:
        return {
            "source_id": source_id,
            "status": "failed",
            "reason": "all retries exhausted",
            "url": url
        }

    text = extract_text(response.text)

    return {
        "source_id":           source_id,
        "title":               source["title"],
        "publisher":           source["publisher"],
        "url":                 url,
        "credibility_tier":    source["credibility_tier"],
        "methodology_grade":   source["methodology_grade"],
        "expected_sentiment_skew": source["expected_sentiment_skew"],
        "status":              "success",
        "status_code":         response.status_code,
        "raw_text":            text,
        "char_count":          len(text),
        "scraped_at":          datetime.utcnow().isoformat() + "Z"
    }


def write_output(results, run_timestamp):
    """
    Write scraped results to data/raw/YYYY_MM_DD_HHMMSS.json.
    Creates the directory if it does not exist.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = f"{run_timestamp}.json"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w") as f:
        json.dump(results, f, indent=2)

    log.info(f"Raw output written to {filepath}")
    return filepath


def write_manifest(manifest, run_timestamp):
    """
    Write a run manifest to data/logs/YYYY_MM_DD_HHMMSS_manifest.json.
    The manifest records what happened on this run for auditability.
    """
    os.makedirs(LOG_DIR, exist_ok=True)
    filename = f"{run_timestamp}_manifest.json"
    filepath = os.path.join(LOG_DIR, filename)

    with open(filepath, "w") as f:
        json.dump(manifest, f, indent=2)

    log.info(f"Run manifest written to {filepath}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    run_start    = datetime.utcnow()
    run_timestamp = run_start.strftime("%Y_%m_%d_%H%M%S")

    log.info("=" * 60)
    log.info("HomeschoolIQ Scraper — run started")
    log.info(f"Timestamp: {run_timestamp}")
    log.info("=" * 60)

    # Load sources
    sources = load_sources(SOURCES_FILE)

    # Scrape each source
    results  = []
    succeeded = 0
    failed    = 0
    skipped   = 0

    for i, source in enumerate(sources, start=1):
        log.info(f"\n[{i}/{len(sources)}] {source['title']}")

        result = scrape_source(source)
        results.append(result)

        if result["status"] == "success":
            succeeded += 1
            log.info(f"  ✓ {result['char_count']:,} characters extracted")
        elif result["status"] == "failed":
            failed += 1
            log.warning(f"  ✗ Failed: {result['reason']}")
        else:
            skipped += 1
            log.info(f"  — Skipped: {result['reason']}")

        # Rate limit — pause between requests
        if i < len(sources):
            log.info(f"  Waiting {DELAY_SECONDS}s before next request...")
            time.sleep(DELAY_SECONDS)

    # Write output
    output_path = write_output(results, run_timestamp)

    # Build and write manifest
    run_end = datetime.utcnow()
    manifest = {
        "run_timestamp":      run_timestamp,
        "run_start":          run_start.isoformat() + "Z",
        "run_end":            run_end.isoformat() + "Z",
        "duration_seconds":   round((run_end - run_start).total_seconds(), 1),
        "sources_attempted":  len(sources),
        "sources_succeeded":  succeeded,
        "sources_failed":     failed,
        "sources_skipped":    skipped,
        "output_file":        output_path,
        "failed_sources":     [
            {"source_id": r["source_id"], "url": r["url"], "reason": r["reason"]}
            for r in results if r["status"] == "failed"
        ]
    }
    write_manifest(manifest, run_timestamp)

    # Summary
    log.info("\n" + "=" * 60)
    log.info("Run complete")
    log.info(f"  Succeeded : {succeeded}")
    log.info(f"  Failed    : {failed}")
    log.info(f"  Skipped   : {skipped}")
    log.info(f"  Duration  : {manifest['duration_seconds']}s")
    log.info("=" * 60)

    if failed > 0:
        log.warning(f"{failed} source(s) failed. Check the manifest for details.")


if __name__ == "__main__":
    main()