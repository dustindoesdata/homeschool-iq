"""
HomeschoolIQ — Dashboard
File: dashboard/app.py

Run with:
    python3 -m streamlit run dashboard/app.py

Pass history:
    Pass 1 — Data table on screen
    Pass 2 — Summary metrics, charts, stat cards
    Pass 3 — Comparison charts by metric_key + subject
    Pass 4 — Full rebuild: 5 questions, 5 chart types, hybrid data  ← current
"""

import sqlite3
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="HomeschoolIQ",
    page_icon="🏠",
    layout="wide",
)

# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .section-header {
        font-size: 1.05em;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #a6adc8;
        margin: 32px 0 10px 0;
        padding-bottom: 6px;
        border-bottom: 1px solid #313244;
    }
    .callout {
        background: #181825;
        border-left: 4px solid #89b4fa;
        padding: 11px 16px;
        border-radius: 0 8px 8px 0;
        margin: 6px 0 14px 0;
        font-size: 0.88em;
        color: #cdd6f4;
        line-height: 1.5;
    }
    .callout-warn {
        background: #181825;
        border-left: 4px solid #f9e2af;
        padding: 11px 16px;
        border-radius: 0 8px 8px 0;
        margin: 6px 0 14px 0;
        font-size: 0.88em;
        color: #cdd6f4;
        line-height: 1.5;
    }
    .source-tag {
        font-size: 0.78em;
        color: #6c7086;
        margin-top: 4px;
    }
    .question-label {
        font-size: 1.5em;
        font-weight: 800;
        color: #cdd6f4;
        margin-bottom: 2px;
    }
</style>
""", unsafe_allow_html=True)

# ── DB connection ─────────────────────────────────────────────────────────────

@st.cache_data
def load_all_stats():
    conn = sqlite3.connect("data/homeschooliq.db")
    df = pd.read_sql_query("""
        SELECT s.stat_text, s.numeric_value, s.unit, s.sentiment,
               s.era, s.selection_bias_flag, s.metric_key, s.subject,
               c.name AS category,
               src.credibility_tier, src.methodology_grade,
               src.title AS source_title, src.url AS source_url,
               src.publisher
        FROM stats s
        JOIN categories c   ON c.id  = s.category_id
        JOIN sources    src ON src.id = s.source_id
    """, conn)
    conn.close()
    return df

@st.cache_data
def load_metric(metric_key):
    conn = sqlite3.connect("data/homeschooliq.db")
    df = pd.read_sql_query("""
        SELECT s.stat_text, s.numeric_value, s.unit, s.subject,
               s.selection_bias_flag,
               src.credibility_tier, src.methodology_grade,
               src.title AS source_title, src.url AS source_url
        FROM stats s
        JOIN sources src ON src.id = s.source_id
        WHERE s.metric_key = ?
          AND s.subject IS NOT NULL
          AND s.numeric_value IS NOT NULL
        ORDER BY src.credibility_tier, s.numeric_value DESC
    """, conn, params=(metric_key,))
    conn.close()
    return df

@st.cache_data
def load_reasons():
    """Load why parents choose to homeschool — from Pew 2025 and NCES."""
    conn = sqlite3.connect("data/homeschooliq.db")
    df = pd.read_sql_query("""
        SELECT s.stat_text, s.numeric_value, s.unit,
               src.title AS source_title, src.credibility_tier
        FROM stats s
        JOIN sources src ON src.id = s.source_id
        WHERE s.unit = '%'
          AND s.numeric_value IS NOT NULL
          AND (s.stat_text LIKE '%school environment%'
            OR s.stat_text LIKE '%moral instruction%'
            OR s.stat_text LIKE '%family life%'
            OR s.stat_text LIKE '%dissatisfaction with academic%'
            OR s.stat_text LIKE '%special needs%'
            OR s.stat_text LIKE '%physical or mental health%'
            OR s.stat_text LIKE '%religious instruction%')
          AND (src.title LIKE '%Pew%' OR src.title LIKE '%NCES%'
            OR src.title LIKE '%Parent and Family%')
        ORDER BY s.numeric_value DESC
    """, conn)
    conn.close()
    return df

df_all = load_all_stats()

# ── Colour palette ────────────────────────────────────────────────────────────

C = {
    "homeschool":      "#89b4fa",
    "public_school":   "#a6e3a1",
    "black_homeschool":"#cba6f7",
    "black_public":    "#f38ba8",
    "axis":            "#313244",
    "text":            "#cdd6f4",
    "muted":           "#6c7086",
    "warn":            "#f9e2af",
}

PLOT_BASE = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font_color=C["text"],
    margin=dict(t=20, b=10, l=10, r=10),
)

SUBJECT_LABELS = {
    "homeschool":       "Homeschool",
    "public_school":    "Public School",
    "black_homeschool": "Black Homeschool",
    "black_public":     "Black Public School",
    "all_students":     "All Students",
}

TIER_ICONS = {
    "government": "🏛️", "peer_reviewed": "🔬",
    "advocacy": "📢",   "news": "📰",
}

GRADE_LABELS = {
    "A": "Grade A — Controlled study",
    "B": "Grade B — Large sample",
    "C": "Grade C — Self-selected / advocacy",
    "D": "Grade D — Anecdotal",
}

# ── Hardcoded verified data ───────────────────────────────────────────────────
# These values fail automated extraction but are verified from source text.
# Every value has a citation.

# Academic test scores (NHERI/Ray, Rudner 1999 — Grade C, bias flagged)
ACADEMIC = {
    "Homeschool\n(all students)": 70,    # midpoint of "15-25 percentile points above 50th" → 65-75 → 70
    "Public School\n(average)":    50,    # by definition — NCES
    "Black Homeschool":           72,    # 40 (Black public baseline) + midpoint(23-42)=32.5 → ~72, Ray 2015
    "Black Public School":        40,    # NAEP data — Black students average ~40th percentile nationally
}
ACADEMIC_SOURCE = "NHERI/Ray 2010–2017 (Grade C ⚠️ self-selected), Ray 2015; Black baseline from NAEP"

# Enrollment timeline (Census HPS + NCES NHES — Grade A)
ENROLLMENT_TIMELINE = {
    "2018–19\n(pre-pandemic)": 3.3,
    "Spring 2020":             5.4,
    "Fall 2020\n(peak)":      11.1,
    "2022–23":                 6.4,
}
ENROLLMENT_SOURCE = "U.S. Census Household Pulse Survey + NCES NHES 2024 (Grade A)"

# Socialization (NHERI NSCH population study — Grade B)
SOCIAL_DATA = {
    "Sports / athletic teams": {"Homeschool": 45.9, "Public School": 56.9},
    "Clubs & organizations":   {"Homeschool": 62.3, "Public School": 56.9},
    "Volunteer / community":   {"Homeschool": 83.0, "Public School": 83.0},
}
SOCIAL_SOURCE = "NHERI — National Survey of Child Health (n=55,000+, Grade B)"

# Income data — hardcoded because extraction broke after Bug #2 fix
INCOME_DATA = {
    "Homeschool\n(long-term)": 35,
    "Non-Homeschool":          52,
}
INCOME_SOURCE = "Cardus Education Survey 2025 (n=181, Grade B)"

# ── Sidebar ───────────────────────────────────────────────────────────────────

st.sidebar.title("🏠 HomeschoolIQ")
st.sidebar.caption("Research-backed homeschool data")
st.sidebar.markdown("---")

view = st.sidebar.radio(
    "Navigate",
    ["📊 The Research", "📋 All Stats", "ℹ️ About"],
    index=0,
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "**Methodology grades**\n\n"
    "**A** — Federal survey / controlled study\n\n"
    "**B** — Large sample, some controls\n\n"
    "**C** — Self-selected / advocacy-funded\n\n"
    "**D** — Anecdotal / opinion"
)
st.sidebar.caption(
    "⚠️ Selection bias flag on any Grade C/D source — "
    "results may overrepresent motivated, high-income families."
)

# ══════════════════════════════════════════════════════════════════════════════
# VIEW: THE RESEARCH
# ══════════════════════════════════════════════════════════════════════════════

if view == "📊 The Research":

    st.title("HomeschoolIQ")
    st.caption(
        "Five questions. What the research actually says — "
        "with every source graded and every bias flagged."
    )

    # Summary row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Stats in database", len(df_all))
    c2.metric("Sources", df_all["source_title"].nunique())
    c3.metric("Govt + Peer-Reviewed rows",
              len(df_all[df_all["credibility_tier"].isin(["government","peer_reviewed"])]))
    c4.metric("⚠️ Selection bias flagged",
              len(df_all[df_all["selection_bias_flag"]==1]))

    st.markdown("---")

    # ════════════════════════════════════════════════════════════════
    # Q1 — ACADEMIC PERFORMANCE
    # ════════════════════════════════════════════════════════════════

    st.markdown('<div class="question-label">📚 Q1 — How do homeschoolers perform academically?</div>', unsafe_allow_html=True)
    st.markdown('<div class="callout-warn">⚠️ <strong>Critical caveat:</strong> Nearly all homeschool test score studies use self-selected volunteer samples — families who choose to participate tend to be more motivated and higher-income than average homeschoolers. Treat these figures as upper bounds, not typical outcomes. 78% of peer-reviewed studies show positive academic outcomes (Ray 2017).</div>', unsafe_allow_html=True)

    academic_col, note_col = st.columns([3, 1])

    with academic_col:
        groups  = list(ACADEMIC.keys())
        scores  = list(ACADEMIC.values())
        colors  = [C["homeschool"], C["public_school"], C["black_homeschool"], C["black_public"]]

        fig1 = go.Figure()
        fig1.add_vline(x=50, line_dash="dash", line_color=C["muted"],
                       annotation_text="Public school average (50th)", 
                       annotation_position="top right",
                       annotation_font_color=C["muted"])
        fig1.add_trace(go.Bar(
            y=groups, x=scores,
            orientation="h",
            marker_color=colors,
            text=[f"{s}th percentile" for s in scores],
            textposition="outside",
            textfont=dict(size=13, color=C["text"]),
        ))
        fig1.update_layout(
            **PLOT_BASE,
            xaxis=dict(title="Percentile Score", range=[0, 105],
                       gridcolor=C["axis"]),
            yaxis=dict(tickfont=dict(size=13)),
            height=260,
        )
        st.plotly_chart(fig1, use_container_width=True)
        st.markdown(f'<div class="source-tag">Source: {ACADEMIC_SOURCE}</div>',
                    unsafe_allow_html=True)

    with note_col:
        st.markdown("**Key finding**")
        st.metric("Homeschool avg", "70th percentile",
                  delta="+20 vs public avg", delta_color="normal")
        st.metric("Black homeschool", "72nd percentile",
                  delta="+32 vs Black public", delta_color="normal")
        st.caption("⚠️ Grade C sources — "
                   "self-selected samples only")

    with st.expander("📎 Academic stats from database"):
        acad_df = df_all[df_all["category"] == "Academic"].head(20)
        st.dataframe(
            acad_df[["stat_text","numeric_value","credibility_tier",
                     "methodology_grade","selection_bias_flag","source_title"]],
            hide_index=True, use_container_width=True)

    st.markdown("---")

    # ════════════════════════════════════════════════════════════════
    # Q2 — COST
    # ════════════════════════════════════════════════════════════════

    st.markdown('<div class="question-label">💰 Q2 — What does homeschooling actually cost?</div>', unsafe_allow_html=True)
    st.markdown('<div class="callout">Public schools are funded through state, federal, and local taxes. Homeschool families pay that tax <em>and</em> bear their own curriculum costs. The gap between what the public system spends and what homeschool families spend is one of the starkest numbers in the dataset.</div>', unsafe_allow_html=True)

    cost_df = load_metric("per_pupil_cost")

    if not cost_df.empty:
        # Use best credibility row per subject
        tier_rank = {"government": 0, "peer_reviewed": 1, "advocacy": 2, "news": 3}
        cost_df["tr"] = cost_df["credibility_tier"].map(tier_rank)
        cost_agg = cost_df.sort_values("tr").groupby("subject", as_index=False).first()

        cost_col, note_col2 = st.columns([3, 1])

        with cost_col:
            fig2 = go.Figure()
            subject_order = ["homeschool", "public_school"]
            for subj in subject_order:
                row = cost_agg[cost_agg["subject"] == subj]
                if row.empty:
                    continue
                val = row["numeric_value"].values[0]
                label = SUBJECT_LABELS.get(subj, subj)
                fig2.add_trace(go.Bar(
                    x=[label], y=[val],
                    marker_color=C[subj],
                    text=[f"${val:,.0f}/yr"],
                    textposition="outside",
                    textfont=dict(size=15, color=C["text"]),
                    name=label,
                ))
            fig2.update_layout(
                **PLOT_BASE,
                showlegend=False,
                yaxis=dict(title="Annual Cost per Student (USD)",
                           tickprefix="$", tickformat=",",
                           gridcolor=C["axis"]),
                xaxis=dict(tickfont=dict(size=14)),
                height=340,
            )
            st.plotly_chart(fig2, use_container_width=True)
            st.markdown('<div class="source-tag">Sources: NCES Per-Pupil Expenditure 2022 (Grade A) · NHERI Family Cost Estimate (Grade C ⚠️)</div>', unsafe_allow_html=True)

        with note_col2:
            hs_val  = cost_agg[cost_agg["subject"]=="homeschool"]["numeric_value"].values
            pub_val = cost_agg[cost_agg["subject"]=="public_school"]["numeric_value"].values
            if len(hs_val) and len(pub_val):
                ratio = pub_val[0] / hs_val[0]
                gap   = pub_val[0] - hs_val[0]
                st.metric("Public spends", f"{ratio:.0f}× more",
                          delta=f"${gap:,.0f} gap per student", delta_color="off")
            st.markdown("**Taxpayer savings**")
            st.metric("Annual savings", "$51 billion",
                      delta="3.1M homeschoolers × $16,446",
                      delta_color="off")
            st.caption("NHERI 2022 estimate · Grade C ⚠️")

        with st.expander("📎 Cost source rows"):
            st.dataframe(cost_df[["subject","numeric_value","unit",
                                   "credibility_tier","methodology_grade",
                                   "source_title"]],
                         hide_index=True, use_container_width=True)

    st.markdown("---")

    # ════════════════════════════════════════════════════════════════
    # Q3 — ADULT OUTCOMES
    # ════════════════════════════════════════════════════════════════

    st.markdown('<div class="question-label">🎓 Q3 — What happens when they grow up?</div>', unsafe_allow_html=True)
    st.markdown('<div class="callout">Cardus 2025 is the most recent peer-reviewed study of adult homeschool outcomes. It found that <strong>long-term homeschoolers</strong> (those schooled at home for most of K–12) attained bachelor\'s degrees and above-median incomes at lower rates than non-homeschoolers. Context: only 17% of homeschoolers are homeschooled for all of K–12 (Cardus 2025). <strong>Both panels below come from the same study (n=181)</strong> — they should not be interpreted as convergent findings from independent sources.</div>', unsafe_allow_html=True)

    deg_col, inc_col = st.columns(2)

    # Panel A — Bachelor's degree (DB-driven)
    with deg_col:
        st.markdown("**Bachelor's Degree Attainment**")
        deg_df = load_metric("bachelor_degree_rate")
        if not deg_df.empty:
            tier_rank = {"government": 0, "peer_reviewed": 1, "advocacy": 2, "news": 3}
            deg_df["tr"] = deg_df["credibility_tier"].map(tier_rank)
            deg_agg = deg_df.sort_values("tr").groupby("subject", as_index=False).first()

            fig3a = go.Figure()
            for subj, label, color in [
                ("homeschool", "Homeschool\n(long-term)", C["homeschool"]),
                ("public_school", "Non-Homeschool", C["public_school"]),
            ]:
                row = deg_agg[deg_agg["subject"] == subj]
                if row.empty:
                    continue
                val = row["numeric_value"].values[0]
                fig3a.add_trace(go.Bar(
                    x=[label], y=[val],
                    marker_color=color,
                    text=[f"{val:.0f}%"],
                    textposition="outside",
                    textfont=dict(size=14, color=C["text"]),
                    name=label,
                ))
            fig3a.update_layout(
                **PLOT_BASE,
                showlegend=False,
                yaxis=dict(title="% with Bachelor's or Higher",
                           range=[0, 65], ticksuffix="%",
                           gridcolor=C["axis"]),
                height=300,
            )
            st.plotly_chart(fig3a, use_container_width=True)

            hs  = deg_agg[deg_agg["subject"]=="homeschool"]["numeric_value"].values
            pub = deg_agg[deg_agg["subject"]=="public_school"]["numeric_value"].values
            if len(hs) and len(pub):
                st.metric("Gap", f"{hs[0]:.0f}% vs {pub[0]:.0f}%",
                          delta=f"{hs[0]-pub[0]:+.0f}pp", delta_color="normal")
        st.markdown('<div class="source-tag">Cardus Education Survey 2025 · n=181 · Grade B</div>', unsafe_allow_html=True)

    # Panel B — Household income (hardcoded — extraction broken)
    with inc_col:
        st.markdown("**Household Income Above Median**")
        inc_groups = list(INCOME_DATA.keys())
        inc_vals   = list(INCOME_DATA.values())
        inc_colors = [C["homeschool"], C["public_school"]]

        fig3b = go.Figure()
        for g, v, c in zip(inc_groups, inc_vals, inc_colors):
            fig3b.add_trace(go.Bar(
                x=[g], y=[v],
                marker_color=c,
                text=[f"{v}%"],
                textposition="outside",
                textfont=dict(size=14, color=C["text"]),
                name=g,
            ))
        fig3b.update_layout(
            **PLOT_BASE,
            showlegend=False,
            yaxis=dict(title="% with Income Above National Median",
                       range=[0, 75], ticksuffix="%",
                       gridcolor=C["axis"]),
            height=300,
        )
        st.plotly_chart(fig3b, use_container_width=True)
        st.metric("Gap", "35% vs 52%", delta="-17pp", delta_color="normal")
        st.markdown(f'<div class="source-tag">{INCOME_SOURCE}</div>',
                    unsafe_allow_html=True)

    with st.expander("📎 Adult outcomes source rows"):
        ao_df = df_all[df_all["category"]=="Outcomes"]
        st.dataframe(ao_df[["stat_text","numeric_value","unit","credibility_tier",
                              "methodology_grade","source_title"]],
                     hide_index=True, use_container_width=True)

    st.markdown("---")

    # ════════════════════════════════════════════════════════════════
    # Q4 — SOCIALIZATION
    # ════════════════════════════════════════════════════════════════

    st.markdown('<div class="question-label">👥 Q4 — What about socialization?</div>', unsafe_allow_html=True)
    st.markdown('<div class="callout">The most common concern about homeschooling. The data shows homeschoolers participate <em>differently</em> — less likely to play organized sports, more likely to join clubs and volunteer. Community engagement is equal. The pattern suggests a community-based model of socialization rather than a school-based one.</div>', unsafe_allow_html=True)

    # Build grouped horizontal bar
    activities   = list(SOCIAL_DATA.keys())
    hs_vals      = [SOCIAL_DATA[a]["Homeschool"]    for a in activities]
    pub_vals     = [SOCIAL_DATA[a]["Public School"]  for a in activities]

    fig4 = go.Figure()
    fig4.add_trace(go.Bar(
        y=activities, x=hs_vals,
        name="Homeschool",
        orientation="h",
        marker_color=C["homeschool"],
        text=[f"{v}%" for v in hs_vals],
        textposition="outside",
        textfont=dict(size=13, color=C["text"]),
    ))
    fig4.add_trace(go.Bar(
        y=activities, x=pub_vals,
        name="Public School",
        orientation="h",
        marker_color=C["public_school"],
        text=[f"{v}%" for v in pub_vals],
        textposition="outside",
        textfont=dict(size=13, color=C["text"]),
    ))
    fig4.update_layout(
        **PLOT_BASE,
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1),
        xaxis=dict(title="Participation Rate (%)", range=[0, 115],
                   ticksuffix="%", gridcolor=C["axis"]),
        yaxis=dict(tickfont=dict(size=13)),
        height=280,
    )
    st.plotly_chart(fig4, use_container_width=True)
    st.markdown(f'<div class="source-tag">Source: {SOCIAL_SOURCE}</div>',
                unsafe_allow_html=True)

    with st.expander("📎 Social-Emotional source rows"):
        se_df = df_all[df_all["category"]=="Social-Emotional"]
        st.dataframe(se_df[["stat_text","numeric_value","unit","credibility_tier",
                              "methodology_grade","source_title"]],
                     hide_index=True, use_container_width=True)

    st.markdown("---")

    # ════════════════════════════════════════════════════════════════
    # Q5 — WHO IS HOMESCHOOLING AND WHY
    # ════════════════════════════════════════════════════════════════

    st.markdown('<div class="question-label">📈 Q5 — Who is homeschooling, and why?</div>', unsafe_allow_html=True)

    why_col, trend_col = st.columns([3, 2])

    # Left — Reasons (DB-driven from Pew 2025)
    with why_col:
        st.markdown("**Why parents choose to homeschool** *(Pew Research 2025)*")
        st.markdown('<div class="callout">% of homeschool parents who cite each reason. Multiple reasons allowed.</div>', unsafe_allow_html=True)

        # Hardcode Pew 2025 reasons since DB extraction isn't reliable enough
        reasons = {
            "Concerns about school\nenvironment / safety": 83,
            "Provide moral instruction":                   75,
            "Emphasize family life together":              72,
            "Dissatisfied with academic\ninstruction":     72,
            "Provide religious instruction":               53,
            "Nontraditional approach\nto education":       50,
            "Child has special needs":                     21,
            "Physical / mental health":                    15,
        }

        fig5a = go.Figure(go.Bar(
            y=list(reasons.keys()),
            x=list(reasons.values()),
            orientation="h",
            marker_color="#89b4fa",
            text=[f"{v}%" for v in reasons.values()],
            textposition="outside",
            textfont=dict(size=12, color=C["text"]),
        ))
        fig5a.update_layout(
            **PLOT_BASE,
            xaxis=dict(range=[0, 105], ticksuffix="%", gridcolor=C["axis"]),
            yaxis=dict(tickfont=dict(size=11)),
            height=380,
        )
        st.plotly_chart(fig5a, use_container_width=True)
        st.markdown('<div class="source-tag">Pew Research Center 2025 · n=19,562 nationally representative · Grade A</div>', unsafe_allow_html=True)

    # Right — Enrollment trend (hardcoded timeline)
    with trend_col:
        st.markdown("**Enrollment trend** *(% of K–12 students homeschooled)*")
        st.markdown('<div class="callout">The pandemic drove a dramatic spike. Rates remained above pre-pandemic levels after schools reopened.</div>', unsafe_allow_html=True)

        timeline_x = list(ENROLLMENT_TIMELINE.keys())
        timeline_y = list(ENROLLMENT_TIMELINE.values())

        fig5b = go.Figure()
        fig5b.add_trace(go.Scatter(
            x=timeline_x,
            y=timeline_y,
            mode="lines+markers+text",
            line=dict(color="#89b4fa", width=3),
            marker=dict(size=10, color="#89b4fa"),
            text=[f"{v}%" for v in timeline_y],
            textposition=["bottom center","bottom center","top center","bottom center"],
            textfont=dict(size=13, color=C["text"]),
        ))
        # Annotation for pandemic surge
        fig5b.add_annotation(
            x="Fall 2020\n(peak)",
            y=11.1,
            text="Pandemic surge",
            showarrow=True,
            arrowhead=2,
            arrowcolor=C["warn"],
            font=dict(color=C["warn"], size=11),
            ax=40, ay=-30,
        )
        fig5b.add_annotation(
            x="2022–23",
            y=6.4,
            text="New baseline",
            showarrow=True,
            arrowhead=2,
            arrowcolor=C["muted"],
            font=dict(color=C["muted"], size=11),
            ax=40, ay=-30,
        )
        fig5b.update_layout(
            **PLOT_BASE,
            yaxis=dict(title="% of K–12 students", range=[0, 14],
                       ticksuffix="%", gridcolor=C["axis"]),
            xaxis=dict(tickfont=dict(size=11)),
            height=380,
            showlegend=False,
        )
        st.plotly_chart(fig5b, use_container_width=True)
        st.markdown(f'<div class="source-tag">Source: {ENROLLMENT_SOURCE}</div>',
                    unsafe_allow_html=True)

        # Demographic breakdown
        st.markdown("**Peak rates by group** *(Fall 2020, Census HPS)*")
        demo_data = {
            "Black families":    16.1,
            "All households":    11.1,
            "White families":     8.8,
            "Hispanic families":  6.2,
        }
        for group, rate in demo_data.items():
            delta_vs_overall = rate - 11.1
            st.metric(group, f"{rate}%",
                      delta=f"{delta_vs_overall:+.1f}% vs overall" if group != "All households" else None,
                      delta_color="off")

    st.markdown("---")

    # ════════════════════════════════════════════════════════════════
    # Q6 — THE HARD TRUTHS
    # ════════════════════════════════════════════════════════════════

    st.markdown('<div class="question-label">⚠️ Q6 — What are the documented risks?</div>', unsafe_allow_html=True)
    st.markdown('<div class="callout-warn">A project that only shows the positive findings is not a research project — it\'s a sales pitch. The following findings come from critical-perspective sources and state-level investigations. They are included because intellectual honesty requires it.</div>', unsafe_allow_html=True)

    h1, h2 = st.columns(2)

    with h1:
        st.markdown("**Child Welfare — School Withdrawal Patterns**")
        st.markdown('<div class="callout-warn">Research from state-level child welfare investigations (CRHE, Connecticut OCA) found overlapping patterns between school withdrawal for homeschooling and prior child welfare involvement.</div>', unsafe_allow_html=True)

        withdrawal_data = {
            "Withdrawn to homeschool\nhad prior DCF reports":    36,
            "Withdrawn to homeschool\nwere chronically truant":  62,
            "Abuse victims removed\nfrom school to homeschool":  47,
        }

        fig6a = go.Figure(go.Bar(
            y=list(withdrawal_data.keys()),
            x=list(withdrawal_data.values()),
            orientation="h",
            marker_color="#f38ba8",
            text=[f"{v}%" for v in withdrawal_data.values()],
            textposition="outside",
            textfont=dict(size=12, color=C["text"]),
        ))
        fig6a.update_layout(
            **PLOT_BASE,
            xaxis=dict(range=[0, 85], ticksuffix="%", gridcolor=C["axis"]),
            yaxis=dict(tickfont=dict(size=11)),
            height=240,
        )
        st.plotly_chart(fig6a, use_container_width=True)
        st.markdown('<div class="source-tag">CRHE — Coalition for Responsible Home Education · State investigation data · Grade C (advocacy) ⚠️ Not nationally representative</div>', unsafe_allow_html=True)

    with h2:
        st.markdown("**Regulatory Oversight — State Variation**")
        st.markdown('<div class="callout-warn">Homeschool oversight varies dramatically by state. There is no federal standard. The absence of oversight makes both abuse and educational neglect harder to detect.</div>', unsafe_allow_html=True)

        oversight_data = {
            "States requiring\nacademic assessment":         20,
            "States requiring\nsubject matter standards":    29,
            "States requiring\nnotification only":           11,
            "States with\nno requirements at all":           10,
        }

        fig6b = go.Figure(go.Bar(
            y=list(oversight_data.keys()),
            x=list(oversight_data.values()),
            orientation="h",
            marker_color="#f9e2af",
            text=[f"{v} states" for v in oversight_data.values()],
            textposition="outside",
            textfont=dict(size=12, color=C["text"]),
        ))
        fig6b.update_layout(
            **PLOT_BASE,
            xaxis=dict(title="Number of States", range=[0, 40],
                       gridcolor=C["axis"]),
            yaxis=dict(tickfont=dict(size=11)),
            height=240,
        )
        st.plotly_chart(fig6b, use_container_width=True)
        st.markdown('<div class="source-tag">Education Week 2022 · CRHE State Law Database · Grade B/C</div>', unsafe_allow_html=True)

        st.markdown("**Key context**")
        st.markdown(
            "The vast majority of homeschooling families are not in these patterns. "
            "These statistics describe a subset — but the absence of mandatory "
            "oversight means there is no systematic way to identify which families "
            "that subset includes."
        )

    with st.expander("📎 Critique source rows from database"):
        crit_df = df_all[df_all["category"] == "Critique"]
        st.dataframe(
            crit_df[["stat_text","numeric_value","unit","credibility_tier",
                      "methodology_grade","source_title"]],
            hide_index=True, use_container_width=True)

    st.markdown("---")
    st.caption(
        "HomeschoolIQ · Every stat labeled with source, credibility grade, and bias flag. "
        "No institutional stake in the outcome. "
        "Built by Dustin · Data Scientist · Army Veteran · Homeschooling Father"
    )


# ══════════════════════════════════════════════════════════════════════════════
# VIEW: ALL STATS
# ══════════════════════════════════════════════════════════════════════════════

elif view == "📋 All Stats":

    st.title("All Stats")
    st.caption(f"{len(df_all)} stats from {df_all['source_title'].nunique()} sources")

    c1, c2, c3 = st.columns(3)
    sel_cat  = c1.selectbox("Category",
                            ["All"] + sorted(df_all["category"].unique().tolist()))
    sel_tier = c2.selectbox("Credibility Tier",
                            ["All"] + sorted(df_all["credibility_tier"].unique().tolist()))
    sel_bias = c3.selectbox("Selection Bias",
                            ["All", "Clean (controls documented)", "Flagged (no controls)"])

    filtered = df_all.copy()
    if sel_cat  != "All": filtered = filtered[filtered["category"] == sel_cat]
    if sel_tier != "All": filtered = filtered[filtered["credibility_tier"] == sel_tier]
    if sel_bias == "Clean (controls documented)":
        filtered = filtered[filtered["selection_bias_flag"] == 0]
    elif sel_bias == "Flagged (no controls)":
        filtered = filtered[filtered["selection_bias_flag"] == 1]

    st.markdown(f"**{len(filtered)} stats**")

    CAT_COLORS = {
        "Academic": "#89b4fa", "Social-Emotional": "#a6e3a1",
        "Cost": "#f9e2af", "Outcomes": "#cba6f7", "Critique": "#f38ba8",
    }

    for _, row in filtered.iterrows():
        label = row["stat_text"][:120] + ("…" if len(row["stat_text"]) > 120 else "")
        with st.expander(label):
            st.markdown(f"**{row['stat_text']}**")
            st.markdown("<br>", unsafe_allow_html=True)
            m1, m2, m3, m4 = st.columns(4)
            cc = CAT_COLORS.get(row["category"], "#888")
            m1.markdown(
                f"**Category**\n\n"
                f"<span style='background:{cc};color:#1e1e2e;padding:2px 8px;"
                f"border-radius:4px;font-size:0.85em;font-weight:700'>"
                f"{row['category']}</span>",
                unsafe_allow_html=True)
            m2.markdown(
                f"**Tier**\n\n"
                f"{TIER_ICONS.get(row['credibility_tier'],'')} "
                f"{row['credibility_tier'].replace('_',' ').title()}")
            m3.markdown(
                f"**Methodology**\n\n"
                f"{GRADE_LABELS.get(row['methodology_grade'], row['methodology_grade'])}")
            m4.markdown(
                f"**Bias**\n\n"
                f"{'⚠️ No controls' if row['selection_bias_flag'] else '✅ Controls'}")
            if row.get("metric_key"):
                st.markdown(
                    f"`{row['metric_key']}` · "
                    f"subject: `{row['subject'] or 'undetected'}`")
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                f"📎 [{row['source_title']}]({row['source_url']}) "
                f"— *{row['publisher']}*")


# ══════════════════════════════════════════════════════════════════════════════
# VIEW: ABOUT
# ══════════════════════════════════════════════════════════════════════════════

elif view == "ℹ️ About":

    st.title("About HomeschoolIQ")
    st.markdown("""
HomeschoolIQ collects published research from government agencies,
peer-reviewed studies, and education journalism — then puts it all
in one honest, filterable dashboard so you can see what the data
actually says, not what advocates on either side want you to hear.

---

### Why I Built This

I am a homeschooling father. When I decided to homeschool my children,
I wanted a data-driven foundation — not blog posts, not Facebook groups,
not the loudest voices on either side.

I could not find that resource. So I built it.

Every finding in this project is written alongside the data as it was
collected — not after — to prevent the natural human tendency to find
evidence for what we already believe.

---

### How the Data Is Sourced

| Tier | Description | Examples |
|---|---|---|
| 🏛️ Government | Federal surveys and reports | NCES, U.S. Census |
| 🔬 Peer-Reviewed | Published research | PLOS ONE, NHERI, Cardus, Nature |
| 📢 Advocacy | Org-published research | HSLDA (pro), CRHE (critical) |
| 📰 News | Education journalism | NPR, Pew Research, Education Week |

Advocacy sources are included deliberately — both pro-homeschool (HSLDA)
and critical (CRHE) — graded and flagged so neither side runs unopposed.

---

### Selection Bias

Studies using self-selected volunteer samples are flagged ⚠️. These tend
to overrepresent motivated, high-income, educated homeschool families
and should be treated as upper bounds, not typical outcomes.

---

### About the Pipeline

Data flows through four stages:

```
scrape_sources.py → validate_raw.py → clean_data.py → load_data.py
```

64 verified HTML sources → 334 stats in SQLite → this dashboard.

Source code: [github.com/dustindoesdata/homeschool-iq](https://github.com/dustindoesdata/homeschool-iq)

---
    """)
    st.caption("Built by Dustin · Data Scientist · Army Veteran · Homeschooling Father")
    st.caption('*"Business drives Technology, not the other way around."*')