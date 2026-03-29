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

# ── Metric key detection ──────────────────────────────────────────────────────
# Maps metric_key → list of keyword signals.
# First match wins. Order matters — more specific patterns first.
# metric_key values must match the CHECK constraint in schema.sql.

METRIC_PATTERNS = {
    "per_pupil_cost": [
        "per pupil", "per student", "per-pupil", "per-student",
        "cost per", "spend per", "expenditure per"
    ],
    "standardized_test_score": [
        "percentile point", "standardized", "achievement test",
        "test score", "sat score", "act score", "clt score",
        "score above", "scoring above", "score below",
        "50th percentile", "public school average is",
    ],
    "academic_achievement_studies": [
        "peer-reviewed studies on academic", "studies show homeschool",
        "studies on academic achievement"
    ],
    "social_emotional_studies": [
        "peer-reviewed studies on social", "studies on social",
        "social, emotional", "emotional, and psychological"
    ],
    "adult_outcomes_studies": [
        "peer-reviewed studies on success", "studies on success into adulthood",
        "success into adulthood"
    ],
    # bachelor_degree_rate and household_income MUST come before enrollment_rate —
    # "percent" in Cardus sentences would otherwise fire enrollment_rate
    "bachelor_degree_rate": [
        "bachelor", "bachelor's degree", "college degree",
        "four-year degree", "completed a degree",
        "completed a bachelor",
    ],
    "household_income": [
        "household income", "income above", "income below",
        "earning", "annual income", "median income",
        "incomes above the median", "household incomes",
    ],
    "employment_rate": [
        "employed", "not working", "employment", "workforce"
    ],
    "extracurricular_participation": [
        "sports team", "sport class", "extracurricular",
        "participated in sports", "afterschool club",
        "school-based activit",
    ],
    "civic_engagement": [
        "volunteer", "volunteering", "civic", "voting", "town hall",
        "community service", "community engagement"
    ],
    "dropout_rate": [
        "dropout", "drop out", "drop-out"
    ],
    "annual_family_cost": [
        "families spend", "family spend", "homeschool families spend",
        "parents spend", "annual cost of homeschool"
    ],
    "taxpayer_cost": [
        "taxpayer", "tax dollar", "public fund", "billion for taxpayer",
        "saved.*taxpayer", "taxpayer.*saved"
    ],
    "enrollment_rate": [
        # Narrowed — "% of", "percent of", "enrolled" removed (too broad,
        # fired on internet access rows and unrelated percentage sentences)
        "households with school-age", "were homeschooled",
        "homeschooling rate", "homeschool rate",
        "school-age children.*homeschool",
        "students.*homeschooled",
        "k-12.*homeschool",
    ],
    "enrollment_count": [
        "million homeschool", "million home", "homeschool students in",
        "home-educated children", "homeschooled children",
        "number of homeschool"
    ],
    "college_gpa": [
        "college gpa", "gpa", "grade point average"
    ],
}

# ── Subject detection ─────────────────────────────────────────────────────────
# Maps subject → keyword signals in priority order.
# Checked in order — first match wins.
# Subjects must match the CHECK constraint in schema.sql.

SUBJECT_PATTERNS = {
    "black_homeschool": [
        "black homeschool", "african american homeschool",
        "black home-educated", "black home educated"
    ],
    "black_public": [
        "black public school", "african american public school",
        "black student", "african american student"
    ],
    "hispanic_homeschool": [
        "hispanic homeschool", "hispanic home-educated",
        "latino homeschool"
    ],
    "hispanic_public": [
        "hispanic public school", "hispanic student",
        "latino student"
    ],
    "homeschool": [
        "homeschool", "home-educated", "home educated",
        "home school", "homeschooled", "homeschooler"
    ],
    "public_school": [
        "public school", "public-school", "institutional school",
        "traditionally schooled", "conventionally schooled",
        "non-homeschool", "those in institutional",
        "publicly schooled", "publicly-schooled",
        "elementary and secondary",
        "non-homeschooler", "non-home-schooled",
        "those who attended institutional",
    ],
    "general_population": [
        "general population", "national average", "all americans",
        "u.s. average", "us average"
    ],
    "all_students": [
        "all students", "all school-age", "k-12 students",
        "school-age children"
    ],
}



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


def detect_metric_key(sentence):
    """
    Assign a metric_key from METRIC_PATTERNS.
    Returns the first matching key, or None if no pattern matches.
    First match wins — patterns are ordered most-specific to least-specific.
    """
    s = sentence.lower()
    for metric_key, signals in METRIC_PATTERNS.items():
        if any(sig in s for sig in signals):
            return metric_key
    return None


def detect_subject(sentence):
    """
    Detect the subject (who the number describes) from SUBJECT_PATTERNS.
    Returns the first matching subject, or None.
    Checks more-specific patterns (black_homeschool) before general ones
    (homeschool) to prevent over-broad matches.
    """
    s = sentence.lower()
    for subject, signals in SUBJECT_PATTERNS.items():
        if any(sig in s for sig in signals):
            return subject
    return None


def extract_all_numbers(sentence):
    """
    Extract ALL numeric values from a sentence, not just the first.
    Returns a list of (numeric_value, unit) tuples.

    Used for comparison sentences that contain two values —
    e.g. "$600 [homeschool] vs $16,446 [public school]"
    extracts [(600.0, 'USD'), (16446.0, 'USD')].

    Each value is extracted with the same unit logic as extract_numeric_value():
    percentages first, then dollars, then millions, then plain numbers.
    Year numbers and URLs are stripped before extraction.
    """
    # Strip URLs
    s = re.sub(r'https?://\S+', '', sentence)
    s = re.sub(r'\b\w+\.(?:org|com|gov|edu|net)\S*', '', s)
    # Strip year ranges
    s = YEAR_REGEX.sub('', s)

    results = []

    # Percentages
    for m in re.finditer(r'(\d+\.?\d*)\s*%', s):
        results.append((float(m.group(1)), '%'))

    # Dollar amounts
    for m in re.finditer(r'\$(\d[\d,]*(?:\.\d+)?)', s):
        results.append((float(m.group(1).replace(',', '')), 'USD'))

    # Millions
    for m in re.finditer(r'(\d+\.?\d*)\s*million', s, re.IGNORECASE):
        results.append((float(m.group(1)) * 1_000_000, 'count'))

    # Percentile written out (only if no % already found for this number)
    if not results:
        for m in re.finditer(r'(\d+\.?\d*)\s*percent', s, re.IGNORECASE):
            results.append((float(m.group(1)), '%'))

    # Deduplicate — same value/unit pair
    seen = set()
    deduped = []
    for val, unit in results:
        key = (round(val, 4), unit)
        if key not in seen:
            seen.add(key)
            deduped.append((val, unit))

    return deduped


def is_comparison_sentence(sentence):
    """
    Return True if the sentence contains explicit comparison language
    between homeschool and another group.
    Used to decide whether to run multi-number extraction.
    """
    s = sentence.lower()
    comparison_signals = [
        "compared to", " vs ", "versus", "above", "below",
        "higher than", "lower than", "points above", "points below",
        "percent above", "percent below", "while.*public", "public.*while",
        "homeschool.*public", "public.*homeschool",
        "home-educated.*public", "public.*home-educated",
    ]
    has_homeschool = any(w in s for w in [
        "homeschool", "home-educated", "home educated"
    ])
    has_comparison = any(sig in s for sig in comparison_signals)
    return has_homeschool and has_comparison



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

def _split_subjects(sentence, values):
    """
    For a comparison sentence containing multiple numeric values,
    attempt to assign a subject to each value based on sentence structure.

    Strategy: split the sentence at comparison keywords, then detect
    the subject in each fragment and assign it to the nearest number.

    Returns a list of subjects parallel to the values list.
    Falls back to detect_subject() on the full sentence if splitting fails.
    """
    s_lower = sentence.lower()

    # Split points — common comparison structures
    split_patterns = [
        r'\bcompared to\b', r'\bversus\b', r'\bvs\.?\b',
        r'\bwhile\b', r'\bwhereas\b', r'\bwhereas\b',
        r'\b(?:public school|public-school)\b.*\b(?:homeschool|home-educated)\b',
    ]

    fragments = [sentence]
    for pattern in split_patterns:
        parts = re.split(pattern, sentence, flags=re.IGNORECASE)
        if len(parts) >= 2:
            fragments = parts
            break

    # Try to match each value to the fragment it appears in
    subjects = []
    for val, unit in values:
        # Build a pattern that finds this number in text
        val_str = str(int(val)) if val == int(val) else str(val)
        matched_subject = None
        for fragment in fragments:
            if val_str in fragment or f"{val:.0f}" in fragment:
                matched_subject = detect_subject(fragment)
                if matched_subject:
                    break
        # Fall back to full sentence if no fragment match
        subjects.append(matched_subject or detect_subject(sentence))

    return subjects



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

            category_id      = assign_category(sentence)
            sentiment        = assign_sentiment(sentence, source.get("expected_sentiment_skew", "neutral"))
            semantic_cluster = assign_semantic_cluster(category_id, sentence)
            metric_key       = detect_metric_key(sentence)

            stat_text = sentence
            if is_proxy:
                stat_text += " [era derived from published_date]"

            base_row = {
                "stat_text":            stat_text,
                "value_type":           None,
                "sample_size":          None,
                "category_id":          category_id,
                "sentiment":            sentiment,
                "era":                  era,
                "selection_bias_flag":  selection_bias_flag,
                "semantic_cluster":     semantic_cluster,
                "conflicts_with":       None,
                "metric_key":           metric_key,
                "source_id":            source_id,
                "source_title":         title,
                "source_url":           url,
                "source_publisher":     publisher,
                "credibility_tier":     credibility_tier,
                "methodology_grade":    methodology_grade,
                "data_collection_year": data_collection_year,
                "published_date":       published_date,
            }

            if is_comparison_sentence(sentence) and metric_key:
                # Comparison sentence — extract all numbers and write
                # one row per (value, subject) pair so the dashboard
                # can query both sides of a comparison by metric_key.
                all_values = extract_all_numbers(sentence)

                if len(all_values) >= 2:
                    # Attempt subject assignment per number by splitting
                    # the sentence at natural comparison boundaries.
                    subjects = _split_subjects(sentence, all_values)
                    for (val, unit), subject in zip(all_values, subjects):
                        row = dict(base_row)
                        row["numeric_value"] = val
                        row["unit"]          = unit
                        row["subject"]       = subject
                        all_stats.append(row)
                    total_extracted += len(all_values) - 1  # extra rows from split
                    continue  # skip the single-value fallback below

            # Single-value path — standard extraction
            numeric_value, unit = extract_numeric_value(sentence)
            subject             = detect_subject(sentence)
            base_row["numeric_value"] = numeric_value
            base_row["unit"]          = unit
            base_row["subject"]       = subject
            all_stats.append(base_row)

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
        "metric_key", "subject",
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