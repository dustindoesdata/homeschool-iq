# 🏠 HomeschoolIQ

### Research-backed answers to the questions every homeschooling parent gets asked.

> *"What about socialization?"*
> *"Will they fall behind academically?"*
> *"How much does it actually cost?"*

HomeschoolIQ collects published research from government agencies,
peer-reviewed studies, and education journalism — then puts it all
in one honest, interactive dashboard so you can see what the data
actually says, not what advocates on either side want you to hear.

[![Status](https://img.shields.io/badge/Status-Live-brightgreen?style=flat-square)]()
[![Sources](https://img.shields.io/badge/Sources-64%20Verified-blue?style=flat-square)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

---

## 🔗 View the Dashboard

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://homeschool-iq-4jzmxbcnpmnlz89skb6kgy.streamlit.app/)

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
Participation in sports, clubs, and community service compared
side by side between homeschool and public school students.

### 💰 Cost
What does homeschooling actually cost a family per year? How does
that compare to what the public school system spends per student?

### 🎓 Long-Term Outcomes
Bachelor's degree attainment. Household income. How do adults
who were homeschooled long-term compare to non-homeschoolers?

### 📈 Who Is Homeschooling and Why?
Enrollment trends over time, the pandemic surge, demographic
breakdowns, and the reasons parents actually cite for choosing it.

### ⚠️ The Hard Truths
The risks, the regulatory gaps, and the documented downsides.
This section exists because a project that only shows the
positive findings is not a research project — it's a sales pitch.

---

## How the Data Is Sourced

Every stat in the dashboard comes from one of 64 verified sources across
four credibility tiers. The full source list is in
[`docs/SOURCES.md`](https://github.com/dustindoesdata/homeschool-iq/blob/main/docs/SOURCES.md).

| Tier | Count | Includes |
|---|---|---|
| 🏛️ Government | 9 | NCES, U.S. Census Bureau, HHS/ACF |
| 🔬 Peer-Reviewed | 25 | NHERI, PLOS ONE, Pew Research, Cardus, Nature, ERIC |
| 📢 Advocacy | 15 | HSLDA (pro-homeschool), CRHE (critical), EdChoice, NEA |
| 📰 News | 15 | NPR, PBS NewsHour, Education Week, Education Next, The 74 |

Every data point is labeled with its source and a credibility grade
so you always know how much weight to give it. Advocacy sources are
included deliberately — both pro-homeschool (HSLDA) and critical (CRHE)
voices are represented so neither side runs unopposed.

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
| Research Design | ✅ Complete | Questions defined, 64 verified sources, data model built |
| Data Collection | ✅ Complete | 64 sources scraped, 334 stats extracted |
| Data Validation | ✅ Complete | Full pipeline validated end-to-end |
| Data Cleaning | ✅ Complete | Stats extracted with comparison fields for charting |
| Analysis | ✅ Complete | 6 questions answered with verified data across 5 chart types |
| Dashboard | ✅ Complete | Live on Streamlit Community Cloud |
| Launch | ✅ **Live** | [View the dashboard →](https://homeschool-iq-4jzmxbcnpmnlz89skb6kgy.streamlit.app/) |

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

# Step 4 — Load stats into SQLite database
python3 loading/load_data.py

# Step 5 — Launch the dashboard
python3 -m streamlit run dashboard/app.py
```

Each step feeds the next. Output lands in `data/` at each stage:

| Step | Output location | What it contains |
|---|---|---|
| Scrape | `data/raw/` | Raw page text from each source, timestamped JSON |
| Validate | `data/cleaned/` | Validated records ready for cleaning |
| Clean | `data/cleaned/` | Structured stats CSV with metric_key and subject fields |
| Load | `data/homeschooliq.db` | SQLite database consumed by the dashboard |
| Logs | `data/logs/` | Run manifests and validation reports |

### Project Structure

```
homeschool-iq/
├── scraper/
│   ├── scrape_sources.py   # Fetches pages from all active sources
│   └── sources.json        # 64-source registry with credibility grades
├── validation/
│   └── validate_raw.py     # Quality checks on scraped output
├── cleaning/
│   └── clean_data.py       # Extracts stats, assigns metric_key and subject
├── loading/
│   └── load_data.py        # Loads CSV into SQLite, prints summary report
├── dashboard/
│   └── app.py              # Streamlit dashboard — 6 questions, 5 chart types
├── sql/
│   └── schema.sql          # Database schema
├── data/
│   ├── raw/                # Timestamped scrape output
│   ├── cleaned/            # Validated records and structured stats
│   ├── logs/               # Run manifests and validation reports
│   ├── quarantine/         # Records that failed validation
│   └── homeschooliq.db     # SQLite database
├── docs/
│   ├── data_dictionary.md  # Every field defined
│   ├── cleaning_rules.md   # Pipeline transformation rules
│   ├── findings.md         # The analytical framework
│   └── SOURCES.md          # Full table of all 64 verified sources
├── requirements.txt
├── CONTRIBUTING.md
└── README.md
```

### Install Dependencies

The dashboard requires three packages:

```bash
pip3 install streamlit pandas plotly
```

The scraper additionally requires `requests`, `beautifulsoup4`, and `lxml`:

```bash
pip3 install requests beautifulsoup4 lxml
```

Note: `requirements.txt` in the repo root contains only the dashboard
dependencies and is used by Streamlit Community Cloud for deployment.

### Technical Documentation

- [`docs/data_dictionary.md`](docs/data_dictionary.md) — every database field defined
- [`docs/cleaning_rules.md`](docs/cleaning_rules.md) — all pipeline transformation rules
- [`docs/findings.md`](docs/findings.md) — the analytical framework

The pipeline runs on Python, SQLite, pandas, Streamlit, requests,
and BeautifulSoup. Everything is free and open source.
See [`CONTRIBUTING.md`](CONTRIBUTING.md) to get involved.

---

## License

MIT — use it, fork it, build on it. If this helps another
homeschooling family make a more informed decision, that is
the whole point.

---

**Dustin** · Data Scientist · Army Veteran · Homeschooling Father

*"Business drives Technology, not the other way around."*