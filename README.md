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
| Research Design | ✅ Complete | Questions defined, sources identified, data model built |
| Data Collection | 🔄 In Progress | Scraping research from all 10 sources |
| Analysis | ⬜ Upcoming | EDA, findings written alongside the data |
| Dashboard | ⬜ Upcoming | Interactive charts, filters, source transparency |
| Launch | ⬜ Upcoming | Live on Streamlit Community Cloud |

---

## For Developers

The technical documentation lives in the `docs/` folder:

- [`docs/data_dictionary.md`](docs/data_dictionary.md) — every field defined
- [`docs/cleaning_rules.md`](docs/cleaning_rules.md) — pipeline transformation rules
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
