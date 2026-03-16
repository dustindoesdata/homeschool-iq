# Data Dictionary
### HomeschoolIQ — Field-Level Documentation

> *Every field in this schema earns its place. This document explains what each field stores, why it exists, and how it behaves.*

**Schema file:** `sql/schema.sql`
**Schema version:** 1.0.0
**Database:** `sql/homeschool.db`
**Last Updated:** *(updated when schema changes are made)*

---

## Table Index

| Table | Purpose | Row Definition |
|---|---|---|
| `categories` | Controlled vocabulary for stat classification | One row per category label |
| `sources` | Every article, study, or report scraped | One row per unique source URL |
| `stats` | Individual data points extracted from sources | One row per claim or finding |

---

## Table: `categories`

Seeded once at setup via `schema.sql`. Never scraped. Provides the controlled vocabulary for `stats.category_id`.

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | INTEGER | Yes | Auto-incrementing primary key |
| `name` | TEXT | Yes | Category label — see allowed values below |

**Allowed values for `name`:**

| Value | What it covers |
|---|---|
| `Academic` | Test scores, graduation rates, college acceptance and completion |
| `Social-Emotional` | Socialization, peer dynamics, mental health, clique formation, adult social functioning |
| `Cost` | Family cost of homeschooling, public per-pupil expenditure, hidden costs |
| `Outcomes` | Career outcomes, income, civic engagement, adult life functioning |
| `Critique` | Documented risks, regulatory gaps, abuse cases, negative findings |

---

## Table: `sources`

One row per unique source URL. Every stat in the `stats` table references a row here. Trust signals are assigned manually via `scraper/sources.json` — not inferred by the scraper.

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | INTEGER | Yes | Auto-incrementing primary key |
| `title` | TEXT | Yes | Full title of the article, study, or report |
| `url` | TEXT | Yes | Source URL — enforced unique across the table |
| `publisher` | TEXT | No | Publishing organization (e.g. `NCES`, `Education Week`) |
| `published_date` | TEXT | No | Date the article or report was published — format `YYYY-MM-DD` |
| `data_collection_year` | INTEGER | No | Year the underlying data was actually collected — often different from `published_date`. Used to derive `stats.era`. See fallback rule in Derivation Rules below. |
| `credibility_tier` | TEXT | Yes | Classification of source type — see allowed values below |
| `methodology_grade` | TEXT | Yes | Quality of the study methodology — see allowed values below |
| `scraped_at` | TIMESTAMP | Auto | Timestamp of when the scraper collected this source — set automatically |

**Allowed values for `credibility_tier`:**

| Value | Definition |
|---|---|
| `government` | Federal or state agency data (NCES, Census Bureau) |
| `peer_reviewed` | Published research with documented methodology (NHERI, PLOS ONE) |
| `advocacy` | Organization with an institutional position on the outcome (HSLDA) |
| `news` | Journalism and editorial coverage (Education Week) |

**Allowed values for `methodology_grade`:**

| Grade | Definition |
|---|---|
| `A` | Randomized or controlled study with a documented control group |
| `B` | Large sample with some controls documented |
| `C` | Self-selected sample, no controls, or advocacy-funded without disclosure |
| `D` | Anecdotal, opinion piece, or undisclosed methodology |

**Key rule — `published_date` vs. `data_collection_year`:**
These are not the same field and should never be treated as interchangeable. A 2022 article citing a 2009 study has `published_date = 2022` and `data_collection_year = 2009`. The `era` field on every stat is derived from `data_collection_year`, not `published_date`. Getting this wrong means pre-2012 and post-2020 data silently mix — which invalidates era-based analysis.

---

## Table: `stats`

One row per individual data point extracted from a source. The core analytical table. Every dashboard chart and every finding in `docs/findings.md` is built from rows here.

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | INTEGER | Yes | Auto-incrementing primary key |
| `stat_text` | TEXT | Yes | Full plain-language description of the stat as extracted or paraphrased from the source |
| `numeric_value` | REAL | No | The numeric value of the stat if one exists — NULL if the stat is qualitative |
| `unit` | TEXT | No | Unit of measurement for `numeric_value` — see allowed values below |
| `value_type` | TEXT | No | Statistical type of `numeric_value` — see allowed values below |
| `sample_size` | INTEGER | No | Number of subjects in the underlying study. NULL means not reported — treat as low confidence |
| `category_id` | INTEGER | Yes | Foreign key → `categories.id` |
| `sentiment` | TEXT | Yes | Direction of the finding — see allowed values below |
| `era` | TEXT | Yes | Demographic era of the data — derived from `sources.data_collection_year` — see Derivation Rules |
| `selection_bias_flag` | INTEGER (0 or 1) | Auto | `1` = no documented control group. Defaults to `0`. Auto-set to `1` for any source with `methodology_grade` of C or D unless explicitly overridden in `clean_data.py` with a comment |
| `semantic_cluster` | TEXT | No | Sub-label for Social-Emotional stats only — NULL for all other categories. Cross-field rule enforced in `validate_raw.py` |
| `conflicts_with` | INTEGER | No | Foreign key → `stats.id` of a contradictory stat. NULL if no known conflict. Populated manually during EDA — see Derivation Rules |
| `source_id` | INTEGER | Yes | Foreign key → `sources.id` |
| `created_at` | TIMESTAMP | Auto | Timestamp of record creation — set automatically |

**Allowed values for `unit`:**

| Value | When to use |
|---|---|
| `%` | Percentage values (e.g. graduation rate, survey response rate) |
| `score` | Test scores or scale scores (e.g. SAT, ACT, standardized assessment) |
| `USD` | Dollar amounts (e.g. annual curriculum cost, per-pupil expenditure) |
| `count` | Raw counts (e.g. number of homeschool families, enrollment figures) |
| NULL | Qualitative stats with no extractable numeric value |

**Allowed values for `value_type`:**

| Value | Definition |
|---|---|
| `percentile` | Position within a distribution (e.g. 87th percentile nationally) |
| `mean` | Arithmetic average across a sample |
| `median` | Middle value in a distribution — more robust than mean for skewed data |
| `rate` | Frequency per unit (e.g. per 100,000 students) |
| `count` | Raw total count |
| `dollar` | Monetary value |
| `ratio` | Ratio or proportion between two quantities |
| NULL | Not applicable or not determinable from the source |

**Allowed values for `sentiment`:**

| Value | Definition |
|---|---|
| `pro_homeschool` | Finding favors homeschooling outcomes |
| `pro_public` | Finding favors public school outcomes |
| `neutral` | Finding is descriptive, mixed, or does not favor either environment |

**Allowed values for `era`:**

| Value | Definition |
|---|---|
| `pre_2012` | Data collected before 2012 — reflects a predominantly religious, upper-middle-class homeschool population |
| `2012_2019` | Data collected 2012–2019 — transitional period, growing demographic diversity |
| `2020_present` | Data collected 2020 or later — post-COVID surge, significantly more diverse population |

**Critical rule — never aggregate across eras without disclosure.** These three eras describe demographically different populations. An aggregate statistic spanning all three eras describes no specific population accurately. Every dashboard chart defaults to showing era filters, and every finding in `docs/findings.md` identifies which era(s) its supporting data comes from.

**Allowed values for `semantic_cluster`:**

Used only when `category_id` maps to `Social-Emotional`. NULL for all other categories.

| Value | What it measures |
|---|---|
| `peer_interaction` | Frequency and breadth of peer social contact |
| `clique_formation` | In-group/out-group dynamics in age-segregated environments |
| `conflict_resolution` | Ability to navigate interpersonal conflict constructively |
| `anxiety_rates` | Prevalence of social anxiety in the population studied |
| `adult_outcomes` | Self-reported social functioning and satisfaction in adulthood |

**`sample_size` confidence guide:**

| Sample Size | Confidence Level | Dashboard Treatment |
|---|---|---|
| NULL | Low — not reported | Flagged with a visible disclaimer |
| < 100 | Low — small sample | Flagged with a visible disclaimer |
| 100–999 | Moderate | Displayed normally |
| 1,000+ | High | Displayed normally, noted as large sample |

---

## sources.json Contract

The scraper reads `scraper/sources.json` to populate the `sources` table. The following fields in `sources.json` map directly to schema fields or drive scraper behavior:

| JSON Field | Maps To | Required |
|---|---|---|
| `id` | Scraper reference key — not stored in `sources` table. Used to identify the source in `notes` and pipeline logs. | Yes |
| `title` | `sources.title` | Yes |
| `url` | `sources.url` | Yes |
| `publisher` | `sources.publisher` | Yes |
| `credibility_tier` | `sources.credibility_tier` | Yes |
| `methodology_grade` | `sources.methodology_grade` | Yes |
| `expected_sentiment_skew` | Cleaning script signal — `positive`, `critical`, `neutral` | Yes |
| `scrape_mode` | Scraper branch condition (`html`) | Yes |
| `active` | Whether scraper processes this source | Yes |
| `notes` | Human-readable context for analysts | No |

---

## Derivation Rules

These fields are either auto-generated by SQLite or derived by the cleaning pipeline. They are never entered manually.

| Field | Table | Derivation Rule |
|---|---|---|
| `era` | `stats` | Derived from `sources.data_collection_year`: < 2012 → `pre_2012`, 2012–2019 → `2012_2019`, ≥ 2020 → `2020_present`. **Fallback:** if `data_collection_year` is NULL, extract year from `published_date` as a proxy and flag the record. If both are NULL, quarantine the record — do not insert. |
| `selection_bias_flag` | `stats` | Auto-set to `1` if parent source has `methodology_grade` of C or D. Can be manually overridden to `0` with a comment in `clean_data.py` |
| `conflicts_with` | `stats` | Populated manually by the analyst during the EDA phase in `notebooks/eda.ipynb`. Not automated. Requires human judgment to identify contradictory stats. **Insertion order:** always insert stat A first, retrieve its id, then insert stat B with `conflicts_with = stat_A.id`. Dashboard queries must use `WHERE stats.id < conflicts_with` to avoid returning duplicate pairs. |
| `scraped_at` | `sources` | Set automatically by SQLite `DEFAULT CURRENT_TIMESTAMP` on insert |
| `created_at` | `stats` | Set automatically by SQLite `DEFAULT CURRENT_TIMESTAMP` on insert |