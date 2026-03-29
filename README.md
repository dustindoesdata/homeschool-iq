# 🏠 HomeschoolIQ

### Research-backed answers to the questions every homeschooling parent gets asked.

> *"What about socialization?"*
> *"Will they fall behind academically?"*
> *"How much does it actually cost?"*

HomeschoolIQ collects published research from government agencies,
peer-reviewed studies, and education journalism — then puts it all
in one honest, filterable dashboard so you can see what the data
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

Every stat in the dashboard comes from one of these sources:

| Source | Type |
|---|---|
| National Center for Education Statistics (NCES) | U.S. Government |
| U.S. Census Bureau | U.S. Government |
| National Home Education Research Institute (NHERI) | Research Organization |
| PLOS ONE | Peer-Reviewed Journal |
| Home School Legal Defense Association (HSLDA) | Advocacy Organization |
| Education Week | Education Journalism |

Every data point is labeled with its source and a credibility grade
so you always know how much weight to give it. Advocacy sources are
included deliberately — but they are graded and flagged so they
cannot mislead.

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
| Data Cleaning | ✅ Complete | metric_key + subject fields enable comparison charts |
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
```

Each step feeds the next. Output lands in `data/` at each stage:

| Step | Output location | What it contains |
|---|---|---|
| Scrape | `data/raw/` | Raw page text from each source |
| Validate | `data/cleaned/` | Validated records ready for cleaning |
| Clean | `data/cleaned/` | Structured stats CSV ready for the database |
| Logs | `data/logs/` | Run manifests and validation reports |

### Project Structure

```
homeschool-iq/
├── scraper/
│   ├── scrape_sources.py   # Fetches pages from all active sources
│   └── sources.json        # Source list with credibility grades
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