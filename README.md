# 🏠 HomeschoolIQ

### A full data engineering pipeline exploring homeschool vs. public school outcomes.


[![Python](https://img.shields.io/badge/Python_3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)](https://plotly.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)](https://github.com/features/actions)

[![Status](https://img.shields.io/badge/Status-In%20Progress-yellow?style=flat-square)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Last Updated](https://img.shields.io/badge/Last%20Updated-Coming%20Soon-lightgrey?style=flat-square)]()

> *Built by a homeschooling community who wanted the truth.*

---

## What This Is

HomeschoolIQ is an **end-to-end data pipeline** that collects, stores, cleans, and visualizes research-backed statistics on homeschool and public school outcomes.

It covers academic performance, social development, cost, and long-term outcomes - drawing from government data, peer-reviewed research, advocacy organizations, and critical news coverage. Every data point is sourced, graded for credibility, and tagged for bias so the final dashboard shows the full picture honestly.

This project exists for two reasons:

- **As a homeschooling father** - I wanted a data-driven foundation built from evidence, not advocacy. That means engaging the hard questions head-on, not avoiding them.
- **As a data engineer** - I wanted a portfolio project that exercises the complete pipeline: ingestion → validation → storage → cleaning → analysis → visualization → deployment.

---

## Pipeline Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                              │
│   Government (NCES, Census)  ·  Research (NHERI)  ·  News        │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                      INGESTION LAYER                             │
│          scraper/scrape_sources.py  ·  requests + BS4            │
│          Rate limited  ·  Retry logic  ·  Timestamped output     │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
                    data/raw/YYYY_MM_DD/
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                     VALIDATION GATE                              │
│                  validation/validate_raw.py                      │
│    Required fields  ·  Value range checks  ·  Quarantine log     │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                      CLEANING LAYER                              │
│                   cleaning/clean_data.py                         │
│    Deduplication  ·  Unit standardization  ·  Sentiment tagging  │
│    Credibility grading  ·  Era tagging  ·  Bias flagging         │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
                    data/cleaned/
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                       STORAGE LAYER                              │
│         sql/schema.sql  →  sql/load_data.py  →  homeschool.db    │
│              sources  ·  stats  ·  categories                    │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                      ANALYSIS LAYER                              │
│                    notebooks/eda.ipynb                           │
│    Sentiment distribution  ·  Source credibility map             │
│    Time period breakdown  ·  Social-emotional clustering         │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                   PRESENTATION LAYER                             │
│                   dashboard/app.py  (Streamlit)                  │
│    The Good  ·  The Hard Truths  ·  The Nuance  ·  The Data      │
└──────────────────────────────────────────────────────────────────┘
```

---

## Repository Structure

```
homeschool-iq/
│
├── README.md                   # You are here
├── requirements.txt            # Pinned dependencies
├── Makefile                    # scrape · validate · transform · load · dashboard · rebuild · backup
├── .gitignore
├── LICENSE
├── CONTRIBUTING.md
├── metadata.json               # Pipeline run metadata (powers the last updated badge)
│
├── scraper/
│   ├── scrape_sources.py       # HTML scraping — requests + BeautifulSoup4
│   └── sources.json            # Seed list: URLs, credibility tiers, methodology grades
│
├── data/
│   ├── raw/                    # Timestamped scraped output — never overwritten
│   ├── cleaned/                # Validated, standardized, tagged records
│   ├── sample/                 # 20–30 seed records — repo runs immediately on clone
│   ├── logs/                   # Per-run manifests: records written, failures, duration
│   └── quarantine/             # Records that failed validation — held for manual review
│
├── validation/
│   └── validate_raw.py         # Assertion gate between raw and cleaned
│
├── cleaning/
│   └── clean_data.py           # Full transformation pipeline
│
├── sql/
│   ├── schema.sql              # CREATE TABLE definitions
│   ├── load_data.py            # CSV → SQLite loader
│   ├── seed_data.sql           # INSERT dump — DB always rebuildable from text
│   └── homeschool.db           # SQLite database (committed to repo)
│
├── notebooks/
│   └── eda.ipynb               # Exploratory analysis — where findings begin
│
├── dashboard/
│   └── app.py                  # Streamlit app — the public deliverable
│
└── docs/
    ├── cleaning_rules.md       # 9 transformation and validation rules for clean_data.py
    ├── data_dictionary.md      # Every field defined
    └── findings.md             # Plain-language conclusions — a father's interpretation
```

---

## Data Model

Three tables. Every field earns its place.

```sql
sources       -- Where the data came from and how much to trust it
              -- credibility_tier   : government · peer_reviewed · advocacy · news
              -- methodology_grade  : A (controlled study) → D (anecdotal)
              -- data_collection_year: year the underlying data was collected
              --                      (distinct from the article's published date)

categories    -- Academic · Social-Emotional · Cost · Outcomes · Critique

stats         -- Individual data points extracted from sources
              -- sentiment         : pro_homeschool · pro_public · neutral
              -- era               : pre_2012 · 2012_2019 · 2020_present
              -- selection_bias_flag: no documented control group
              -- semantic_cluster  : peer_interaction · clique_formation ·
              --                     adult_outcomes · anxiety_rates · conflict_resolution
              -- value_type        : percentile · mean · median · rate · count · dollar · ratio
              -- sample_size       : NULL = not reported = low confidence
              -- conflicts_with    : references a contradictory stat.id
```

The `era` field is intentional. Pre-2012 homeschooling and post-2020 homeschooling are demographically different populations. Aggregating across that divide produces noise. Every chart in the dashboard respects the distinction.

---

## Data Sources

| Source | Type | Skew | Grade |
|---|---|---|---|
| [NCES — Homeschooling in the United States](https://nces.ed.gov/programs/digest/d22/tables/dt22_206.10.asp) | Government | Neutral | A |
| [NCES — Parent and Family Involvement Survey](https://nces.ed.gov/nhes/homeschooling.asp) | Government | Neutral | A |
| [NCES — Per Pupil Expenditure](https://nces.ed.gov/fastfacts/display.asp?id=66) | Government | Neutral | A |
| [U.S. Census Bureau — Household Pulse Survey](https://census.gov) | Government | Neutral | A |
| [NHERI — Academic Achievement Research](https://nheri.org/research-facts-on-homeschooling/) | Peer-Reviewed | Positive | B |
| [NHERI — Social-Emotional Development](https://nheri.org/homeschool-researchers/) | Peer-Reviewed | Positive | B |
| [PLOS ONE — Social Development Study](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0177391) | Peer-Reviewed | Neutral | A |
| [HSLDA — Homeschool Academic Stats](https://hslda.org/post/study-shows-homeschoolers-perform-better-academically) | Advocacy | Positive | C |
| [Education Week — Homeschooling Coverage](https://edweek.org/teaching-learning/homeschooling) | News | Critical | C |
| [Education Week — Oversight and Abuse](https://edweek.org/policy-politics/homeschooling-regulations) | News | Critical | C |

10 sources across 4 credibility tiers. No single tier exceeds 40% of the corpus. Sources are balanced deliberately: positive, critical, and neutral voices in proportion. Balance is a data engineering decision, to remove confirmation bias.

---

## On the Socialization Question

The conventional critique of homeschooling *"what about socialization?"*  deserves a data-driven answer, not a defensive one.

The research literature uses "socialization" to describe at least five distinct constructs: peer interaction frequency, conflict resolution skill, clique formation and exclusion dynamics, social anxiety rates, and adult social functioning. These are not the same thing and they do not all point in the same direction.

This dashboard examines the socialization question as what it actually is: a **label definition problem**. Age-segregated school environments produce peer interaction. They also produce clique formation, in-group dynamics, and social anxiety at documented rates. Homeschooled children who engage co-ops, community programs, and mixed-age environments develop a different social profile — not an absent one.

The evidence on this is examined honestly in `docs/findings.md`, including the parts that challenge assumptions on both sides.

---

## Tech Stack

| Layer | Tool | Why |
|---|---|---|
| Scraping | `requests` + `BeautifulSoup4` | Simple, proven, zero cost |
| Cleaning | `pandas` | Readable, maintainable, powerful enough |
| Validation | `pandas` assertions | No framework needed at this scale |
| Storage | `SQLite` | Portable, free, commits directly to the repo |
| Analysis | `Jupyter` | Explore freely, export what matters |
| Visualization | `Plotly` | Interactive charts, Streamlit-native |
| Dashboard | `Streamlit` | Python-native, free hosting |
| Deployment | Streamlit Community Cloud | Free tier, connects directly to GitHub |
| CI/CD | GitHub Actions | Lint on every push — keeps the repo clean |
| Automation | `Makefile` | One command per pipeline phase |

Every tool is free. Every tool is purposeful. Nothing here is impressive for its own sake.

---

## Getting Started

```bash
# Clone the repo
git clone https://github.com/dustindoesdata/homeschool-iq.git
cd homeschool-iq

# Install dependencies
pip install -r requirements.txt

# Run the full pipeline
make scrape       # Collect raw data from sources
make validate     # Assert data quality before cleaning
make transform    # Standardize, tag, and grade records
make load         # Load cleaned data into SQLite
make dashboard    # Launch Streamlit locally

# Backup the database before any destructive operation
make backup

# Rebuild the database from scratch at any time
make rebuild
```

The `data/sample/` folder contains seed records so the dashboard runs immediately on clone, no scraping required to see the project working.

---

## Build Progress

### Phase 0 — Lock the Contracts
- [x] Schema finalized — v1.0.0
- [x] `sources.json` seed list built and balanced — 10 sources across 4 credibility tiers
- [x] Dashboard sections agreed — Good · Hard Truths · Nuance · Data
- [x] `docs/data_dictionary.md` complete
- [x] `docs/cleaning_rules.md` complete — 9 transformation and validation rules
- [x] `docs/findings.md` skeleton complete — 5 sections, claims to test defined

### Phase 1 — Scaffold
- [ ] Repo initialized and pushed to GitHub
- [ ] Folder structure in place
- [ ] `requirements.txt` with pinned versions
- [ ] `Makefile` with all seven targets (scrape · validate · transform · load · dashboard · rebuild · backup)
- [ ] `LICENSE` and `CONTRIBUTING.md` committed
- [ ] GitHub Actions lint workflow active
- [ ] `data/sample/` seed records committed

### Phase 2 — Collect
- [ ] `scraper/sources.json` — balanced seed list
- [ ] `scraper/scrape_sources.py` — rate limited, retry logic, timestamped output
- [ ] Per-run manifest written to `data/logs/`

### Phase 3 — Validate
- [ ] `validation/validate_raw.py` — assertions, quarantine on failure
- [ ] Validation report written alongside run manifest

### Phase 4 — Store
- [ ] `sql/schema.sql` verified executable — runs cleanly against SQLite
- [ ] `sql/load_data.py` written — loads cleaned CSVs into `homeschool.db`
- [ ] `homeschool.db` committed
- [ ] `sql/seed_data.sql` INSERT dump committed

### Phase 5 — Clean
- [ ] `cleaning/clean_data.py` — deduplication, standardization, tagging, grading
- [ ] Era field derived from `data_collection_year`
- [ ] `selection_bias_flag` assigned per source methodology
- [ ] `semantic_cluster` assigned for social-emotional stats

### Phase 6 — Ship
- [ ] `notebooks/eda.ipynb` — full exploratory analysis
- [ ] `docs/findings.md` — written alongside the data, not after
- [ ] `dashboard/app.py` — four sections: Good · Hard Truths · Nuance · Data
- [ ] `metadata.json` — created and committed with `last_run` field
- [ ] Last Updated badge swapped from static placeholder to live dynamic badge
- [ ] Deployed to Streamlit Community Cloud
- [ ] Live URL added to README
- [ ] Badge added to `dustindoesdata` profile README

---

## Live Dashboard

> 🔗 *Deploying soon — Streamlit Community Cloud*

---

## Contributing

Non-technical contributions are just as valuable as code. If you know a credible source this project should include, open a GitHub Issue with the URL and a brief description. See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## License

MIT - use it, fork it, build on it. If this helps another homeschooling family make a more informed decision, that's the whole point.

---

**Dustin** · Data Scientist · Army Veteran · Homeschooling Father

[![GitHub](https://img.shields.io/badge/GitHub-dustindoesdata-181717?style=for-the-badge&logo=github)](https://github.com/dustindoesdata)

*"Business drives Technology, not the other way around."*
