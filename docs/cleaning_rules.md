# Cleaning Rules
### HomeschoolIQ — Transformation, Validation, and Population Rules

> *This document is the single source of truth for every decision made in the cleaning pipeline. A developer building `clean_data.py` or `validate_raw.py` should need no other document.*

**Implements:** `cleaning/clean_data.py` and `validation/validate_raw.py`
**Schema version:** 1.0.0
**Last Updated:** *(updated when rules change)*

---

## Rule 1 — Era Derivation

**Field:** `stats.era`
**Derived from:** `sources.data_collection_year`

| `data_collection_year` | Assigned `era` |
|---|---|
| < 2012 | `pre_2012` |
| 2012–2019 | `2012_2019` |
| ≥ 2020 | `2020_present` |

**Fallback — NULL `data_collection_year`:**
If `data_collection_year` is NULL, extract the year from `published_date` as a proxy. When a proxy is used, append `[era derived from published_date]` to the stat's `stat_text` so downstream analysis can identify proxy-era records.

If both `data_collection_year` and `published_date` are NULL, do not insert the record. Write it to `data/quarantine/` with reason `missing_year` for manual review.

**Why this matters:** Pre-2012 and post-2020 homeschool populations are demographically different. Mixing eras without disclosure produces noise. This rule is non-negotiable.

---

## Rule 2 — Selection Bias Flag

**Field:** `stats.selection_bias_flag`
**Type:** INTEGER — 0 or 1

**Automatic assignment:**
```
If source.methodology_grade IN ('C', 'D') → selection_bias_flag = 1
If source.methodology_grade IN ('A', 'B') → selection_bias_flag = 0
```

**Manual override:**
A Tier B source with a well-documented control group may have `selection_bias_flag` overridden to `0`. Any override must include an inline comment in `clean_data.py`:

```python
# Override: NHERI 2015 study explicitly documents matched control group
# See source notes: nheri_001
stat['selection_bias_flag'] = 0
```

No silent overrides. Every override is traceable.

---

## Rule 3 — Semantic Cluster Assignment

**Field:** `stats.semantic_cluster`
**Applies to:** Social-Emotional category stats only

**Cross-field rule:**
If `category != 'Social-Emotional'` → `semantic_cluster` must be `NULL`.
If `category == 'Social-Emotional'` → assign one of the five allowed values.

This cross-field constraint cannot be enforced by a SQL CHECK constraint alone. It must be asserted in `validate_raw.py`:

```python
# validate_raw.py assertion
social_emotional_id = get_category_id('Social-Emotional')
invalid = df[
    (df['category_id'] != social_emotional_id) &
    (df['semantic_cluster'].notna())
]
assert len(invalid) == 0, f"{len(invalid)} non-Social-Emotional stats have semantic_cluster set"
```

**Assignment guide:**

| Cluster | Assign when the stat measures... |
|---|---|
| `peer_interaction` | Frequency or breadth of peer contact |
| `clique_formation` | In-group/out-group dynamics, exclusion behavior |
| `conflict_resolution` | Ability to handle interpersonal conflict |
| `anxiety_rates` | Social anxiety prevalence or severity |
| `adult_outcomes` | Social functioning or satisfaction reported in adulthood |

---

## Rule 4 — Conflicts With Population

**Field:** `stats.conflicts_with`
**Populated by:** Analyst manually during `notebooks/eda.ipynb`
**Not automated.**

`conflicts_with` requires human judgment — it cannot be assigned by a script. Two stats conflict when they address the same claim and reach contradictory conclusions. Identifying that requires reading and interpreting both stats in context.

**Process:**
1. During EDA, when two stats contradict each other, note both `stat.id` values
2. After both stats are committed to the database, update the later-inserted stat:
   ```sql
   UPDATE stats SET conflicts_with = <earlier_stat_id> WHERE id = <later_stat_id>;
   ```
3. Only one direction of the link is needed — the dashboard deduplicates using:
   ```sql
   WHERE stats.id < stats.conflicts_with
   ```

**Insertion order rule:**
When loading two conflicting stats in the same pipeline run, always insert stat A first, retrieve its auto-generated `id`, then insert stat B with `conflicts_with = stat_A.id`. SQLite foreign key enforcement (`PRAGMA foreign_keys = ON`) will reject a `conflicts_with` value that references a non-existent `stats.id`.

---

## Rule 5 — Source Balance Assertion

**Checked by:** `validate_raw.py`
**Rule:** No single credibility tier exceeds 40% of active sources.

```python
# validate_raw.py assertion
from collections import Counter

active_sources = [s for s in sources if s['active']]
tier_counts = Counter(s['credibility_tier'] for s in active_sources)
total = len(active_sources)

for tier, count in tier_counts.items():
    pct = count / total
    assert pct <= 0.40, (
        f"Tier '{tier}' is {pct:.0%} of active sources — exceeds 40% balance rule. "
        f"Add critical or neutral sources before adding more '{tier}' sources."
    )
```

**Current counts:** government=4, peer_reviewed=3, advocacy=1, news=2 (total=10).
Government is at the ceiling. Do not add government sources without deactivating another.

---

## Rule 6 — Foreign Key Enforcement

**Applies to:** Every database connection in `load_data.py`

SQLite does not enforce foreign key constraints by default. The very first line after opening a connection must be:

```python
conn = sqlite3.connect('sql/homeschool.db')
conn.execute("PRAGMA foreign_keys = ON")
```

Without this, a stat can reference a non-existent `source_id` or `category_id` and SQLite will silently accept it. This PRAGMA must appear before any INSERT or UPDATE statement on every connection.

---

## Rule 7 — make rebuild Is Destructive

**Command:** `make rebuild`

`make rebuild` drops and recreates `homeschool.db` from scratch using `sql/schema.sql` and `sql/seed_data.sql`. Any manually annotated data — including `conflicts_with` links added during EDA — will be permanently lost.

**Before running `make rebuild`:**
```bash
make backup   # copies homeschool.db to homeschool_backup_YYYYMMDD.db
```

The `make backup` target is defined in the Makefile. Use it. Rebuilding without a backup is irreversible.

---

## Rule 8 — Quarantine Threshold

**Checked by:** `validate_raw.py`

If more than 20% of records from a single source fail validation, halt the pipeline and write a failure report to `data/logs/`. Do not attempt to clean partial data from a heavily failing source — investigate the source first.

```python
# Per-source failure threshold
QUARANTINE_THRESHOLD = 0.20

for source_id, group in df.groupby('source_id'):
    failure_rate = group['validation_failed'].mean()
    if failure_rate > QUARANTINE_THRESHOLD:
        raise PipelineHaltError(
            f"Source {source_id} has {failure_rate:.0%} failure rate. "
            f"Halting. Investigate before rerunning."
        )
```

---

## Rule 9 — Grade D Definition

Methodology grade D means: *anecdotal, opinion piece, or undisclosed methodology.*

This is the standard definition across all four Phase 0 documents. Do not use "undisclosed funding" as the D definition — funding disclosure and methodology disclosure are distinct concepts. A study can have fully disclosed funding and still have an invalid or undisclosed methodology.

---

## Summary Checklist for clean_data.py

Before marking Phase 5 complete, verify every rule is implemented:

- [ ] Rule 1 — Era derived from `data_collection_year`, fallback to `published_date`, quarantine if both NULL
- [ ] Rule 2 — `selection_bias_flag` auto-set from `methodology_grade`, overrides commented
- [ ] Rule 3 — `semantic_cluster` NULL for non-Social-Emotional stats
- [ ] Rule 4 — `conflicts_with` left NULL by pipeline, populated manually in EDA
- [ ] Rule 5 — Balance assertion in `validate_raw.py`
- [ ] Rule 6 — `PRAGMA foreign_keys = ON` in every `load_data.py` connection
- [ ] Rule 7 — `make backup` documented and tested before any rebuild
- [ ] Rule 8 — Per-source quarantine threshold enforced in `validate_raw.py`
- [x] Rule 9 — Grade D defined as "undisclosed methodology" consistently across all documents (definition only — no implementation required)