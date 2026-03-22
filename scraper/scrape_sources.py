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

# Last updated: 2026-03-21

import json
import os
import time
import logging
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

# ── Configuration ─────────────────────────────────────────────────────────────

SOURCES_FILE    = "scraper/sources.json"
OUTPUT_DIR      = "data/raw"
LOG_DIR         = "data/logs"
DELAY_SECONDS   = 2       # pause between requests — be polite
MAX_RETRIES     = 3       # retry a failed request this many times
RETRY_DELAY     = 5       # seconds to wait before retrying
REQUEST_TIMEOUT = 15      # seconds before giving up on a request

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


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_active_sources(filepath):
    """
    Load and return active sources from sources.json.
    Raises RuntimeError if no active sources are found.
    """
    with open(filepath, "r") as f:
        data = json.load(f)

    all_sources = data["sources"]
    active = [s for s in all_sources if s.get("active", False)]

    if not active:
        raise RuntimeError(
            f"No active sources found in {filepath}. "
            "Set at least one source to 'active': true."
        )

    log.info(f"Loaded {len(active)} active sources from {filepath}")
    return active


# ── Core functions ─────────────────────────────────────────────────────────────

def fetch_page(url, retries=MAX_RETRIES):
    """
    Fetch a URL with retry logic.
    Returns the response object on success, None on failure.
    """
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(
                url, headers=HEADERS, timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            log.warning(f"  HTTP error on attempt {attempt}/{retries}: {e}")
        except requests.exceptions.ConnectionError as e:
            log.warning(
                f"  Connection error on attempt {attempt}/{retries}: {e}"
            )
        except requests.exceptions.Timeout:
            log.warning(f"  Timeout on attempt {attempt}/{retries}")
        except requests.exceptions.RequestException as e:
            log.warning(
                f"  Request failed on attempt {attempt}/{retries}: {e}"
            )

        if attempt < retries:
            log.info(f"  Retrying in {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)

    log.error(f"  All {retries} attempts failed for {url}")
    return None


def extract_visible_text(html):
    """
    Parse HTML and return clean visible text.
    Strips scripts, styles, nav, footer, and header elements.
    """
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(
        ["script", "style", "nav", "footer", "header", "noscript"]
    ):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    text = " ".join(text.split())
    return text


def scrape_source(source):
    """
    Scrape a single source. Returns a result dict.
    status is 'success', 'failed', or 'skipped'.
    """
    source_id   = source.get("id", "unknown")
    url         = source.get("url", "")
    scrape_mode = source.get("scrape_mode", "html")

    if not url:
        return {
            "source_id": source_id,
            "status":    "failed",
            "reason":    "missing url field in sources.json",
            "url":       ""
        }

    if scrape_mode != "html":
        log.info(f"  [{source_id}] Skipping — scrape_mode is '{scrape_mode}'")
        return {
            "source_id": source_id,
            "status":    "skipped",
            "reason":    f"scrape_mode={scrape_mode}",
            "url":       url
        }

    log.info(f"  [{source_id}] Fetching {url}")
    response = fetch_page(url)

    if response is None:
        return {
            "source_id": source_id,
            "status":    "failed",
            "reason":    "all retries exhausted",
            "url":       url
        }

    text = extract_visible_text(response.text)

    return {
        "source_id":               source_id,
        "title":                   source.get("title", ""),
        "publisher":               source.get("publisher", ""),
        "url":                     url,
        "credibility_tier":        source.get("credibility_tier", ""),
        "methodology_grade":       source.get("methodology_grade", ""),
        "expected_sentiment_skew": source.get("expected_sentiment_skew", "neutral"),
        "status":                  "success",
        "status_code":             response.status_code,
        "raw_text":                text,
        "char_count":              len(text),
        "scraped_at":              datetime.now(timezone.utc).isoformat()
    }


def write_scrape_output(scrape_results, run_timestamp):
    """
    Write scrape results to data/raw/YYYY_MM_DD_HHMMSS.json.
    Creates the directory if it does not exist.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, f"{run_timestamp}.json")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(scrape_results, f, indent=2, ensure_ascii=False)

    log.info(f"Raw output written to {filepath}")
    return filepath


def write_run_manifest(manifest, run_timestamp):
    """
    Write a run manifest to data/logs/YYYY_MM_DD_HHMMSS_manifest.json.
    Records what happened on this run for auditability.
    """
    os.makedirs(LOG_DIR, exist_ok=True)
    filepath = os.path.join(LOG_DIR, f"{run_timestamp}_manifest.json")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    log.info(f"Run manifest written to {filepath}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    run_start     = datetime.now(timezone.utc)
    run_timestamp = run_start.strftime("%Y_%m_%d_%H%M%S")

    log.info("=" * 60)
    log.info("HomeschoolIQ Scraper — run started")
    log.info(f"Timestamp: {run_timestamp}")
    log.info("=" * 60)

    sources = load_active_sources(SOURCES_FILE)

    scrape_results = []
    succeeded      = 0
    failed         = 0
    skipped        = 0

    for i, source in enumerate(sources, start=1):
        log.info(f"\n[{i}/{len(sources)}] {source['title']}")

        result = scrape_source(source)
        scrape_results.append(result)

        if result["status"] == "success":
            succeeded += 1
            log.info(f"  ✓ {result['char_count']:,} characters extracted")
        elif result["status"] == "failed":
            failed += 1
            log.warning(f"  ✗ Failed: {result['reason']}")
        else:
            skipped += 1
            log.info(f"  — Skipped: {result['reason']}")

        if i < len(sources):
            log.info(f"  Waiting {DELAY_SECONDS}s before next request...")
            time.sleep(DELAY_SECONDS)

    output_path = write_scrape_output(scrape_results, run_timestamp)

    run_end  = datetime.now(timezone.utc)
    manifest = {
        "run_timestamp":     run_timestamp,
        "run_start":         run_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "run_end":           run_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "duration_seconds":  round(
            (run_end - run_start).total_seconds(), 1
        ),
        "sources_attempted": len(sources),
        "sources_succeeded": succeeded,
        "sources_failed":    failed,
        "sources_skipped":   skipped,
        "output_file":       output_path,
        "failed_sources":    [
            {
                "source_id": r["source_id"],
                "url":       r["url"],
                "reason":    r["reason"]
            }
            for r in scrape_results if r["status"] == "failed"
        ]
    }
    write_run_manifest(manifest, run_timestamp)

    log.info("\n" + "=" * 60)
    log.info("Run complete")
    log.info(f"  Succeeded : {succeeded}")
    log.info(f"  Failed    : {failed}")
    log.info(f"  Skipped   : {skipped}")
    log.info(f"  Duration  : {manifest['duration_seconds']}s")
    log.info("=" * 60)

    if failed > 0:
        log.warning(
            f"{failed} source(s) failed. Check the manifest for details."
        )


if __name__ == "__main__":
    main()