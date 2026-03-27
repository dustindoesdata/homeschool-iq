# 🏠 HomeschoolIQ

### Research-backed answers to the questions every homeschooling parent gets asked.

> *"What about socialization?"*
> *"Will they fall behind academically?"*
> *"How much does it actually cost?"*

HomeschoolIQ collects published research from government agencies,
peer-reviewed studies, and education journalism — then puts it all
in one honest, filterable dashboard so you can see what the data
actually says, not what advocates on either side want you to hear.

[![Status](https://img.shields.io/badge/Status-In%20Progress-yellow?style=flat-square)]()
[![Sources](https://img.shields.io/badge/Sources-64%20Verified-blue?style=flat-square)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

---

## 🔗 View the Dashboard

> *Coming soon — deploying to Streamlit Community Cloud*

No account required. No setup. Just open the link and explore.

---

## What the Research Covers

### 📚 Academic Outcomes
How do homeschooled students perform on standardized tests? What
happens when they go to college? What does the research say when
you control for income and parent education — not just the
self-selected success stories?

### 👥 Socialization
The most common critique of homeschooling — examined honestly.
The research literature actually measures five distinct things
under the word "socialization," and they don't all point in the
same direction. This section breaks them apart.

### 💰 Cost
What does homeschooling actually cost a family per year? How does
that compare to what the public school system spends per student?
What are the hidden costs nobody talks about?

### 🎓 Long-Term Outcomes
College acceptance. Career outcomes. Civic engagement. How do
homeschool graduates fare in adult life?

### ⚠️ The Hard Truths
The risks, the regulatory gaps, and the documented downsides.
This section exists because a project that only shows the
positive findings is not a research project — it's a sales pitch.

---

## How the Data Is Sourced

Every stat in the dashboard comes from a verified source across
four credibility tiers. All 64 sources confirmed live in the first full scrape run (March 2026). Each passed a 20-pass
analytical review for live URL, HTML scrapability, tier accuracy,
paywall-free access, and homeschool relevance.

| Tier | Count | Examples |
|---|---|---|
| 🏛️ Government | 9 | NCES, U.S. Census, HHS, ACF |
| 🔬 Peer-Reviewed | 25 | PLOS ONE, NHERI research, Nature/Scientific Reports, ERIC, Pew Research |
| 📢 Advocacy | 15 | HSLDA (pro), CRHE (critical), EdChoice, NSCAF |
| 📰 News | 15 | NPR, Education Week, Education Next, The 74, CNA |

Every data point is labeled with its source and a credibility grade
so you always know how much weight to give it. Advocacy sources are
included deliberately — but they are graded and flagged, and both
pro-homeschool (HSLDA) and critical (CRHE) voices are represented
so neither side can run unopposed.

---

## Why I Built This

I am a homeschooling father. When I decided to homeschool my
children, I wanted a data-driven foundation — not blog posts, not
Facebook groups, not the loudest voices on either side.

I wanted to know what peer-reviewed research actually says about
academic outcomes. I wanted to understand the socialization
question with real numbers, not anecdotes. I wanted to engage
honestly with the hard parts, including the documented risks that
homeschool advocates prefer not to discuss.

I could not find that resource. So I built it.

Every finding in this project is written alongside the data as
it was collected — not after — to prevent the natural human
tendency to find evidence for what we already believe.

The conclusions may surprise you. Some of them surprised me.

---

## Suggest a Source

If you know of a credible research study or government report
this project should include, open a
[GitHub Issue](https://github.com/dustindoesdata/homeschool-iq/issues/new)
with the link and a brief description.

No technical knowledge required. Every submitted source is
reviewed, graded for credibility, and added if it meets the
quality bar.

---

## Project Status

| Phase | Status | Description |
|---|---|---|
| Phase 0 — Contracts | ✅ Complete | Schema, sources, data dictionary, cleaning rules, findings framework |
| Phase 1 — Scaffold | ✅ Complete | Scraper, validator, cleaner built and committed |
| Phase 2 — Scrape & Validate | ✅ Complete | Pipeline proven end-to-end; first full run complete |
| Source Expansion | ✅ Complete | 100 sources verified across 4 tiers; 20-pass analytical review |
| Phase 2b — Full Scrape | 🔄 Next | Re-scrape all 100 sources; validate and clean output |
| Phase 3 — Analysis | ⬜ Upcoming | EDA, findings written alongside the data |
| Phase 4 — Dashboard | ⬜ Upcoming | Interactive charts, filters, source transparency |
| Launch | ⬜ Upcoming | Live on Streamlit Community Cloud |

---

## For Developers

### Running the Pipeline

Run each step in order from the repo root:

```bash
# Step 1 — Collect data from all active sources
python3 scraper/scrape_sources.py

# Step 2 — Validate scraped data quality
python3 validation/validate_raw.py

# Step 3 — Extract and structure stats
python3 cleaning/clean_data.py
```

Each step feeds the next. Output lands in `data/` at each stage:

| Step | Output location | What it contains |
|---|---|---|
| Scrape | `data/raw/` | Raw page text from each source, timestamped JSON |
| Validate | `data/cleaned/` | Validated records ready for cleaning |
| Clean | `data/cleaned/` | Structured stats CSV ready for the database |
| Logs | `data/logs/` | Run manifests and validation reports |
| Quarantine | `data/quarantine/` | Records that failed validation |

### Project Structure

```
homeschool-iq/
├── scraper/
│   ├── scrape_sources.py   # Fetches pages from all active sources
│   └── sources.json        # 100-source registry with credibility grades
├── validation/
│   └── validate_raw.py     # Quality checks on scraped output
├── cleaning/
│   └── clean_data.py       # Extracts and structures stat sentences
├── sql/
│   └── schema.sql          # Database schema
├── data/
│   ├── raw/                # Timestamped scrape output
│   ├── cleaned/            # Validated records and structured stats
│   ├── logs/               # Run manifests and validation reports
│   └── quarantine/         # Records that failed validation
├── docs/
│   ├── data_dictionary.md  # Every field defined
│   ├── cleaning_rules.md   # Pipeline transformation rules
│   └── findings.md         # The analytical framework
├── requirements.txt
├── CONTRIBUTING.md
└── README.md
```

### Install Dependencies

```bash
pip3 install -r requirements.txt
```

### Source Registry

[`scraper/sources.json`](https://github.com/dustindoesdata/homeschool-iq/blob/main/scraper/sources.json) contains all 100 verified sources. For a human-readable table of every source, see [`docs/SOURCES.md`](https://github.com/dustindoesdata/homeschool-iq/blob/main/docs/SOURCES.md).

Each JSON entry includes:

- `id` — unique source identifier
- `publisher` — organization that produced the content
- `title` — full source title
- `url` — direct URL to the scrapable HTML page
- `credibility_tier` — `government` | `peer_reviewed` | `advocacy` | `news`
- `methodology_grade` — `A` (controlled study) → `D` (anecdotal)
- `expected_sentiment_skew` — `positive` | `critical` | `neutral`
- `scrape_mode` — `html` (all 100 current sources are HTML)
- `active` — boolean; deactivated sources are kept for history

All 100 active sources passed a 20-pass analytical review covering:
URL liveness, HTML scrapability, no paywalls, correct credibility tier,
accurate methodology grade, no duplicates, stat-sentence yield, and
homeschool research relevance.

### Technical Documentation

- [`docs/data_dictionary.md`](docs/data_dictionary.md) — every database field defined
- [`docs/cleaning_rules.md`](docs/cleaning_rules.md) — all pipeline transformation rules
- [`docs/findings.md`](docs/findings.md) — the analytical framework

The pipeline runs on Python, SQLite, pandas, and Streamlit.
Everything is free and open source. See [`CONTRIBUTING.md`](CONTRIBUTING.md)
to get involved.

---

## License

MIT — use it, fork it, build on it. If this helps another
homeschooling family make a more informed decision, that is
the whole point.

---

**Dustin** · Data Scientist · Army Veteran · Homeschooling Father

*"Business drives Technology, not the other way around."*