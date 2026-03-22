"""
HomeschoolIQ — Data Cleaner
File: cleaning/clean_data.py

Reads the most recent validated JSON from data/cleaned/, extracts
stat sentences from each source's raw text, applies all cleaning
rules from docs/cleaning_rules.md, and writes a structured CSV
ready for load_data.py.

Rules applied:
  - Era derived from sources.json data_collection_year (Rule 1)
  - selection_bias_flag auto-set from methodology_grade (Rule 2)
  - semantic_cluster only assigned to Social-Emotional stats (Rule 3)
  - Duplicate sentences across sources are collapsed
  - Sentences with no statistical content are skipped

Note for load_data.py:
  The CSV carries source_id as a string (e.g. 'nces_001') matching
  sources.json. load_data.py must insert each source into the sources
  table first, retrieve the integer primary key, and use that integer
  when inserting stats. The string source_id is a scraper reference
  key, not a database FK.

Sentiment note:
  Sentiment is assigned via keyword matching and should be treated as
  a first-pass estimate. Review data/cleaned/*_stats.csv before the
  dashboard goes live — sentences flagged as pro_homeschool or
  pro_public should be spot-checked for context accuracy.

Usage:
    python cleaning/clean_data.py
    — or —
    make transform
"""

# Last updated: 2026-03-21

import json
import os
import re
import glob
import csv
import logging
from datetime import datetime, timezone

# ── Configuration ─────────────────────────────────────────────────────────────

CLEANED_DIR  = "data/cleaned"
SOURCES_FILE = "scraper/sources.json"

# ── Keyword lists — edit here, not inside functions ───────────────────────────
# Each list drives one category or sentiment check in assign_category()
# and assign_sentiment(). Priority order for categories is documented
# in assign_category().

COST_KEYWORDS = [
    "cost", "spend", "expenditure", "dollar", "afford",
    "tuition", "curriculum", "budget", "$"
]

SOCIAL_KEYWORDS = [
    "social", "peer", "friend", "anxiety", "emotion",
    "clique", "interact", "isolat",

    # Note: "civic" intentionally excluded — civic engagement stats
    # route to Outcomes, not Social-Emotional.
]

CRITIQUE_KEYWORDS = [
    "abuse", "neglect", "regulat", "oversight", "concern",
    "risk", "problem", "gap", "lack", "fail"
]

OUTCOMES_KEYWORDS = [
    "college", "university", "career", "graduate", "adult",
    "employment", "income", "workforce", "civic"
]

NEGATIVE_SENTIMENT_WORDS = [
    "concern", "abuse", "neglect", "lack", "fail",
    "problem", "risk", "gap", "regulat"
]

POSITIVE_SENTIMENT_WORDS = [
    "outperform", "exceed", "above average",
    "superior", "stronger", "more likely",

    # Note: "higher", "better", "greater" intentionally excluded —
    # these words are unreliable without category context.
    # "higher cost" is not pro-homeschool. "fewer problems" is not pro-public.
    # Category-aware sentiment expansion is a future improvement.
]

PRO_PUBLIC_WORDS = [
    "below", "decline", "worse", "behind", "lag",

    # Note: "lower" and "fewer" intentionally excluded —
    # "lower cost" and "fewer behavioral problems" are pro-homeschool.
    # Context-free matching produces too many false pro_public tags.
]

NEUTRAL_GROWTH_WORDS = [
    "increased", "doubled", "grew", "rise", "surge"
]

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
    Note: duplicated in validate_raw.py only.
    Candidate for extraction to a shared utils module.
    """
    files = sorted(glob.glob(os.path.join(directory, pattern)))
    if not files:
        raise FileNotFoundError(
            f"No file matching '{pattern}' found in {directory}."
        )
    return files[-1]


def load_latest_validated():
    """Load the most recent validated JSON from data/cleaned/."""
    filepath = find_latest_file(CLEANED_DIR, "*_validated.json")
    log.info(f"Loading validated records: {filepath}")
    with open(filepath) as f:
        records = json.load(f)
    log.info(f"Loaded {len(records)} validated records")
    return records


def load_source_registry():
    """
    Load sources.json and return a dict keyed by source_id.
    Named 'registry' to distinguish from scrape records — both are called
    'sources' colloquially but refer to different data shapes.
    Note: duplicated in validate_raw.py. Both should be moved to a
    shared utils module in a future refactor.
    """
    with open(SOURCES_FILE) as f:
        data = json.load(f)
    return {s["id"]: s for s in data["sources"]}


# ── Era derivation (Cleaning Rule 1) ─────────────────────────────────────────

def derive_era(data_collection_year, published_date):
    """
    Derive era from data_collection_year (from sources.json).
    Falls back to published_date year if data_collection_year is missing.
    Returns (era, is_proxy) — is_proxy=True means the fallback was used.
    Returns (None, False) if both values are missing or unparseable.
    """
    year     = None
    is_proxy = False

    if data_collection_year:
        try:
            year = int(data_collection_year)
        except (ValueError, TypeError):
            pass

    if year is None and published_date:
        try:
            year     = int(str(published_date)[:4])
            is_proxy = True
        except (ValueError, TypeError):
            pass

    if year is None:
        return None, False

    if year < 2012:
        return "pre_2012", is_proxy
    elif year <= 2019:
        return "2012_2019", is_proxy
    else:
        return "2020_present", is_proxy


# ── Selection bias flag (Cleaning Rule 2) ─────────────────────────────────────

def derive_selection_bias_flag(methodology_grade):
    """
    Auto-set selection_bias_flag from methodology grade.
    Grade C or D → flag = 1 (no documented control group)
    Grade A or B → flag = 0
    """
    return 1 if methodology_grade in ("C", "D") else 0


# ── Stat extraction ───────────────────────────────────────────────────────────

# Stat signal patterns — sentences matching any of these are kept.
# Plain numbers are intentionally excluded from this list and handled
# separately in extract_numeric_value() with year-exclusion logic.
# Update STAT_PATTERN_STRINGS to add new patterns; STAT_REGEX is
# compiled from it and must not be edited directly.
STAT_PATTERN_STRINGS = [
    r'\d+\.?\d*\s*%',                    # percentages: 87%, 3.3%
    r'\$[\d,]+',                         # dollar amounts: $13,764
    r'\d+\.?\d*\s*percent',              # "percent" written out
    r'\d[\d,]*\s*million',               # millions: 3.3 million
    r'\d[\d,]*\s*billion',               # billions
    r'percentile',                       # percentile references
    r'\d+(?:st|nd|rd|th)\s+percentile',  # 87th percentile
    r'increased?\s+(?:by\s+)?\d',        # increased by X
    r'decreased?\s+(?:by\s+)?\d',        # decreased by X
    r'doubled|tripled|quadrupled',       # relative change
    r'average(?:d|s)?\s+[\$\d]',         # averaged $X
    r'approximately\s+\d',              # approximately X
    r'nearly\s+\d',                     # nearly X
    r'more than\s+\d',                  # more than X
    r'fewer than\s+\d',                 # fewer than X
]

# Compiled from STAT_PATTERN_STRINGS above
STAT_REGEX = re.compile(
    "|".join(STAT_PATTERN_STRINGS),
    re.IGNORECASE
)

# Compiled pattern to exclude year numbers from numeric extraction
YEAR_REGEX = re.compile(r'\b(?:19|20)\d{2}\b')

# Boilerplate patterns — matches navigation, legal, and non-content text
SKIP_REGEX = re.compile(
    r'(cookie|privacy policy|terms of use|subscribe|newsletter|'
    r'follow us|share this|related article|back to top|'
    r'javascript|please enable|loading\.\.\.|sign in|log in|'
    r'copyright ©|all rights reserved)',
    re.IGNORECASE
)


def extract_stat_sentences(raw_text):
    """
    Split raw text into sentences and return those containing statistics.
    Normalises whitespace and newlines before splitting.
    Filters out boilerplate and out-of-range sentences.
    """
    raw_text = raw_text.replace("\n", " ").replace("\r", " ")
    raw_text = " ".join(raw_text.split())

    sentences     = re.split(r'(?<=[.!?])\s+', raw_text)
    stat_sentences = []

    for sentence in sentences:
        sentence = sentence.strip()

        if len(sentence) < 30 or len(sentence) > 500:
            continue
        if SKIP_REGEX.search(sentence):
            continue
        if STAT_REGEX.search(sentence):
            stat_sentences.append(sentence)

    return stat_sentences


def extract_numeric_value(sentence):
    """
    Extract the first numeric value and unit from a sentence.
    Excludes 4-digit year numbers (1900–2099) to prevent years
    being stored as stat values.
    Returns (numeric_value, unit) or (None, None).
    """
    # Percentage
    pct_match = re.search(r'(\d+\.?\d*)\s*%', sentence)
    if pct_match:
        return float(pct_match.group(1)), "%"

    # Dollar amount
    dollar_match = re.search(r'\$(\d[\d,]*)', sentence)
    if dollar_match:
        return float(dollar_match.group(1).replace(",", "")), "USD"

    # Millions
    million_match = re.search(
        r'(\d+\.?\d*)\s*million', sentence, re.IGNORECASE
    )
    if million_match:
        return float(million_match.group(1)) * 1_000_000, "count"

    # Plain number — only if sentence has a stat signal, and
    # after removing year numbers to avoid extracting e.g. 2019
    if STAT_REGEX.search(sentence):
        sentence_no_years = YEAR_REGEX.sub("", sentence)
        num_match = re.search(r'\b(\d[\d,]*)\b', sentence_no_years)
        if num_match:
            return float(num_match.group(1).replace(",", "")), "count"

    return None, None


def assign_category(sentence):
    """
    Assign a category_id based on sentence content.
    category_id: 1=Academic  2=Social-Emotional  3=Cost
                 4=Outcomes  5=Critique

    Priority order (first match wins):
      Cost → Social-Emotional → Critique → Outcomes → Academic

    Cost is checked before Outcomes intentionally — a sentence about
    college tuition costs belongs in Cost, not Outcomes.
    """
    s = sentence.lower()

    if any(w in s for w in COST_KEYWORDS):
        return 3
    if any(w in s for w in SOCIAL_KEYWORDS):
        return 2
    if any(w in s for w in CRITIQUE_KEYWORDS):
        return 5
    if any(w in s for w in OUTCOMES_KEYWORDS):
        return 4
    return 1


def assign_sentiment(sentence, _expected_skew):
    """
    Assign sentiment based primarily on sentence content.
    _expected_skew is accepted for interface compatibility — reserved for
    future category-aware sentiment expansion. Currently unused; keyword
    matching drives all decisions. Prefixed with _ per Python convention.

    Returns: 'pro_homeschool', 'pro_public', or 'neutral'

    IMPORTANT: This is a first-pass keyword estimate. Output should be
    reviewed before the dashboard goes live. See docstring at top of file.
    Words like "higher" and "fewer" are intentionally excluded from
    positive/negative lists — they require category context to be reliable.
    """
    s = sentence.lower()

    if any(w in s for w in NEGATIVE_SENTIMENT_WORDS):
        return "neutral"
    if any(w in s for w in POSITIVE_SENTIMENT_WORDS):
        return "pro_homeschool"
    if any(w in s for w in PRO_PUBLIC_WORDS):
        return "pro_public"
    if any(w in s for w in NEUTRAL_GROWTH_WORDS):
        return "neutral"

    return "neutral"


def assign_semantic_cluster(category_id, sentence):
    """
    Assign a semantic cluster for Social-Emotional stats (category_id=2).
    Returns None for all other categories — enforces Cleaning Rule 3.
    """
    if category_id != 2:
        return None

    s = sentence.lower()

    if any(w in s for w in [
        "clique", "exclusion", "bully", "in-group", "group dynamic"
    ]):
        return "clique_formation"
    if any(w in s for w in [
        "anxiety", "stress", "depress", "mental health"
    ]):
        return "anxiety_rates"
    if any(w in s for w in [
        "conflict", "resolv", "disagree", "mediat"
    ]):
        return "conflict_resolution"
    if any(w in s for w in [
        "adult", "grown", "later life", "long-term social"
    ]):
        return "adult_outcomes"

    return "peer_interaction"


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    timestamp = datetime.now(timezone.utc).strftime("%Y_%m_%d_%H%M%S")

    log.info("=" * 60)
    log.info("HomeschoolIQ Cleaner — run started")
    log.info("=" * 60)

    records         = load_latest_validated()
    source_registry = load_source_registry()

    all_stats        = []
    seen_sentences   = set()   # deduplication — normalized sentence text
    total_extracted  = 0       # count before deduplication

    for record in records:
        source_id = record["source_id"]
        source    = source_registry.get(source_id, {})

        title             = record.get("title", "")
        url               = record.get("url", "")
        publisher         = record.get("publisher", "")
        credibility_tier  = record.get("credibility_tier", "")
        methodology_grade = record.get("methodology_grade", "")
        raw_text = record.get("raw_text", "")

        # Era comes from sources.json metadata — not the scraped record.
        # Note: if sources.json is updated between scrape and clean runs,
        # era assignment may differ from the original scrape context.
        data_collection_year = source.get("data_collection_year")
        published_date       = source.get("published_date")
        era, is_proxy        = derive_era(
            data_collection_year, published_date
        )

        if era is None:
            log.warning(
                f"  [{source_id}] Cannot derive era — "
                "add data_collection_year to sources.json"
            )
            continue

        selection_bias_flag = derive_selection_bias_flag(methodology_grade)
        sentences           = extract_stat_sentences(raw_text)
        total_extracted    += len(sentences)

        log.info(
            f"  [{source_id}] {len(sentences)} stat sentences extracted"
        )

        for sentence in sentences:

            # Deduplication — collapse identical sentences across sources
            normalized = " ".join(sentence.lower().split())
            if normalized in seen_sentences:
                continue
            seen_sentences.add(normalized)

            numeric_value, unit = extract_numeric_value(sentence)
            category_id         = assign_category(sentence)
            sentiment           = assign_sentiment(sentence, source.get("expected_sentiment_skew", "neutral"))
            semantic_cluster    = assign_semantic_cluster(
                category_id, sentence
            )

            stat_text = sentence
            if is_proxy:
                stat_text += " [era derived from published_date]"

            all_stats.append({
                # id omitted — SQLite AUTOINCREMENT assigns the real ID
                "stat_text":            stat_text,
                "numeric_value":        numeric_value,  # None → SQL NULL
                "unit":                 unit,           # None → SQL NULL
                "value_type":           None,           # analyst assigns
                "sample_size":          None,           # analyst assigns
                "category_id":          category_id,
                "sentiment":            sentiment,
                "era":                  era,
                "selection_bias_flag":  selection_bias_flag,
                "semantic_cluster":     semantic_cluster,
                "conflicts_with":       None,           # analyst assigns
                # Source fields — used by load_data.py to populate
                # the sources table before inserting stats
                "source_id":            source_id,
                "source_title":         title,
                "source_url":           url,
                "source_publisher":     publisher,
                "credibility_tier":     credibility_tier,
                "methodology_grade":    methodology_grade,
                "data_collection_year": data_collection_year,
                "published_date":       published_date,
            })

    if not all_stats:
        raise RuntimeError(
            "No stats were extracted. "
            "Check that sources.json has data_collection_year fields "
            "and that data/cleaned/ contains a validated JSON file."
        )

    # Write CSV — QUOTE_ALL prevents newline corruption in text fields
    output_path = os.path.join(CLEANED_DIR, f"{timestamp}_stats.csv")
    fieldnames  = [
        "stat_text", "numeric_value", "unit", "value_type",
        "sample_size", "category_id", "sentiment", "era",
        "selection_bias_flag", "semantic_cluster", "conflicts_with",
        "source_id", "source_title", "source_url", "source_publisher",
        "credibility_tier", "methodology_grade",
        "data_collection_year", "published_date"
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            quoting=csv.QUOTE_ALL,
            extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(all_stats)

    duplicates_removed = total_extracted - len(all_stats)

    log.info(f"\nCleaned stats written to {output_path}")
    log.info("\n" + "=" * 60)
    log.info("Cleaning complete")
    log.info(f"  Sources processed  : {len(records)}")
    log.info(f"  Sentences extracted: {total_extracted}")
    log.info(f"  Duplicates removed : {duplicates_removed}")
    log.info(f"  Stats written      : {len(all_stats)}")
    log.info("=" * 60)

    return output_path


if __name__ == "__main__":
    main()