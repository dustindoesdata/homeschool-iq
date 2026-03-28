"""
HomeschoolIQ — Dashboard
File: dashboard/app.py

Streamlit dashboard for exploring homeschool research stats.
Reads directly from data/homeschooliq.db.

Run with:
    python3 -m streamlit run dashboard/app.py

Pass history:
    Pass 1 — Data table on screen (proven pipeline end-to-end)
    Pass 2 — Summary metrics, charts, readable stat cards  ← current
    Pass 3 — Credibility labels inline, era filter, sentiment filter
    Pass 4 — Polish, deploy to Streamlit Community Cloud
"""

import sqlite3

import pandas as pd
import plotly.express as px
import streamlit as st

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="HomeschoolIQ",
    page_icon="🏠",
    layout="wide",
)

# ── Data loading ──────────────────────────────────────────────────────────────

@st.cache_data
def load_data():
    conn = sqlite3.connect("data/homeschooliq.db")
    df = pd.read_sql_query("""
        SELECT
            s.stat_text,
            s.numeric_value,
            s.unit,
            s.sentiment,
            s.era,
            s.selection_bias_flag,
            c.name   AS category,
            src.credibility_tier,
            src.methodology_grade,
            src.title       AS source_title,
            src.url         AS source_url,
            src.publisher
        FROM stats s
        JOIN categories c  ON c.id  = s.category_id
        JOIN sources    src ON src.id = s.source_id
    """, conn)
    conn.close()
    return df

df = load_data()

# ── Sidebar filters ───────────────────────────────────────────────────────────

st.sidebar.title("Filters")

category_options = ["All"] + sorted(df["category"].unique().tolist())
tier_options     = ["All"] + sorted(df["credibility_tier"].unique().tolist())
bias_options     = ["All", "Clean (controls documented)", "Flagged (no controls)"]

selected_category = st.sidebar.selectbox("Category",         category_options)
selected_tier     = st.sidebar.selectbox("Credibility Tier", tier_options)
selected_bias     = st.sidebar.selectbox("Selection Bias",   bias_options)

st.sidebar.markdown("---")
st.sidebar.caption(
    "**Methodology grades**\n\n"
    "**A** — Controlled study\n\n"
    "**B** — Large sample, some controls\n\n"
    "**C** — Self-selected / advocacy-funded\n\n"
    "**D** — Anecdotal / opinion"
)

# ── Apply filters ─────────────────────────────────────────────────────────────

filtered = df.copy()

if selected_category != "All":
    filtered = filtered[filtered["category"] == selected_category]
if selected_tier != "All":
    filtered = filtered[filtered["credibility_tier"] == selected_tier]
if selected_bias == "Clean (controls documented)":
    filtered = filtered[filtered["selection_bias_flag"] == 0]
elif selected_bias == "Flagged (no controls)":
    filtered = filtered[filtered["selection_bias_flag"] == 1]

# ── Header ────────────────────────────────────────────────────────────────────

st.title("🏠 HomeschoolIQ")
st.caption(
    "Research-backed answers to the questions every homeschooling parent gets asked. "
    "Every stat is labeled with its source, credibility grade, and bias flag "
    "so you always know how much weight to give it."
)

st.markdown("---")

# ── Summary metrics ───────────────────────────────────────────────────────────

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Stats Shown",
    len(filtered),
    delta=f"{len(filtered) - len(df)} from filters" if len(filtered) != len(df) else None,
)
col2.metric(
    "Sources",
    filtered["source_title"].nunique(),
)
col3.metric(
    "Govt + Peer-Reviewed",
    len(filtered[filtered["credibility_tier"].isin(["government", "peer_reviewed"])]),
)
col4.metric(
    "⚠️ Bias Flagged",
    len(filtered[filtered["selection_bias_flag"] == 1]),
)

st.markdown("---")

# ── Charts ────────────────────────────────────────────────────────────────────

chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    category_counts = (
        filtered
        .groupby("category")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    fig_cat = px.bar(
        category_counts,
        x="category",
        y="count",
        title="Stats by Category",
        color="category",
        color_discrete_sequence=px.colors.qualitative.Set2,
        labels={"category": "Category", "count": "# Stats"},
    )
    fig_cat.update_layout(showlegend=False, margin=dict(t=40, b=0))
    st.plotly_chart(fig_cat, use_container_width=True)

with chart_col2:
    tier_counts = (
        filtered
        .groupby("credibility_tier")
        .size()
        .reset_index(name="count")
    )
    # Consistent tier ordering
    tier_order = ["government", "peer_reviewed", "advocacy", "news"]
    tier_counts["credibility_tier"] = pd.Categorical(
        tier_counts["credibility_tier"], categories=tier_order, ordered=True
    )
    tier_counts = tier_counts.sort_values("credibility_tier")

    fig_tier = px.pie(
        tier_counts,
        names="credibility_tier",
        values="count",
        title="Stats by Credibility Tier",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig_tier.update_traces(textposition="inside", textinfo="percent+label")
    fig_tier.update_layout(showlegend=False, margin=dict(t=40, b=0))
    st.plotly_chart(fig_tier, use_container_width=True)

st.markdown("---")

# ── Stat cards ────────────────────────────────────────────────────────────────

st.subheader(f"📋 Stats ({len(filtered)})")

if filtered.empty:
    st.info("No stats match the current filters.")
else:
    # Category color mapping for badges
    CATEGORY_COLORS = {
        "Academic":         "#4C72B0",
        "Social-Emotional": "#55A868",
        "Cost":             "#C44E52",
        "Outcomes":         "#8172B2",
        "Critique":         "#CCB974",
    }

    TIER_ICONS = {
        "government":    "🏛️",
        "peer_reviewed": "🔬",
        "advocacy":      "📢",
        "news":          "📰",
    }

    GRADE_LABELS = {
        "A": "Grade A — Controlled study",
        "B": "Grade B — Large sample",
        "C": "Grade C — Self-selected / advocacy",
        "D": "Grade D — Anecdotal / opinion",
    }

    for _, row in filtered.iterrows():
        # Build expander label — truncate at 120 chars
        label = row["stat_text"]
        if len(label) > 120:
            label = label[:120] + "…"

        bias_label  = "⚠️ No documented controls" if row["selection_bias_flag"] else "✅ Controls documented"
        tier_icon   = TIER_ICONS.get(row["credibility_tier"], "")
        grade_label = GRADE_LABELS.get(row["methodology_grade"], row["methodology_grade"])
        cat_color   = CATEGORY_COLORS.get(row["category"], "#888888")

        with st.expander(label):
            # Full stat text
            st.markdown(f"**{row['stat_text']}**")

            st.markdown("<br>", unsafe_allow_html=True)

            # Metadata row
            meta_col1, meta_col2, meta_col3, meta_col4 = st.columns(4)

            meta_col1.markdown(
                f"**Category**\n\n"
                f"<span style='background:{cat_color};color:white;"
                f"padding:2px 8px;border-radius:4px;font-size:0.85em'>"
                f"{row['category']}</span>",
                unsafe_allow_html=True,
            )
            meta_col2.markdown(
                f"**Source tier**\n\n{tier_icon} {row['credibility_tier'].replace('_', ' ').title()}"
            )
            meta_col3.markdown(f"**Methodology**\n\n{grade_label}")
            meta_col4.markdown(f"**Bias flag**\n\n{bias_label}")

            st.markdown("<br>", unsafe_allow_html=True)

            # Source link
            st.markdown(
                f"📎 [{row['source_title']}]({row['source_url']})  "
                f"— *{row['publisher']}*"
            )