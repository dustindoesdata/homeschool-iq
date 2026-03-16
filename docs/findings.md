# Findings
### HomeschoolIQ — A Father's Interpretation of the Data

> *This document is written alongside the data, not after it. Conclusions are drawn only from what the evidence supports. Where the data is thin, ambiguous, or contradictory, that is stated plainly.*

**Author:** Dustin · Data Scientist · Army Veteran · Homeschooling Father
**Last Updated:** *(updated each time a new analysis pass is completed)*

---

## How to Read This Document

Every finding in this document is linked to the data that supports it. Each section identifies:
- **The claim** — what the finding states
- **The evidence** — which sources and stats support it, with credibility grades
- **The caveats** — what the data does not say, where bias exists, and what remains uncertain
- **The verdict** — a plain-language conclusion based on the weight of the evidence

A finding graded on controlled, Tier A sources carries more weight than one graded on self-selected, Tier C advocacy data. That distinction is always made visible.

---

## Section 1 — Academic Outcomes

**The question this section answers:**
Do homeschooled students perform better, worse, or the same academically compared to their public school peers — and what does the evidence actually control for?

**Claims to test:**
- [ ] Homeschooled students outperform public school peers on standardized tests
- [ ] The performance gap persists when controlling for income and parent education level
- [ ] The performance gap narrows or disappears in controlled studies vs. self-selected samples
- [ ] College acceptance and completion rates for homeschooled students

**Known caveats going in:**
- Most academic performance studies draw from self-selected, motivated homeschool families — not a representative sample
- Families who attempt homeschooling and quit are systematically absent from the data
- Controlling for parent education level is critical — homeschooling parents skew higher educated than the general population

**Finding:** *(to be written after EDA)*

---

## Section 2 — The Socialization Question

**The question this section answers:**
Does homeschooling produce worse social outcomes — and does "socialization" as used in the critique actually mean what critics think it means?

**The reframe:**
The word "socialization" in the research literature describes at least five distinct constructs. This section treats each separately:

| Construct | Question Being Tested |
|---|---|
| `peer_interaction` | Do homeschooled children interact with peers less frequently? |
| `clique_formation` | Do age-segregated environments produce clique dynamics at documented rates? |
| `conflict_resolution` | How do homeschooled children perform on conflict resolution measures? |
| `anxiety_rates` | What do social anxiety rates look like across educational environments? |
| `adult_outcomes` | How do homeschooled adults report their social functioning and satisfaction? |

**Claims to test:**
- [ ] Homeschooled children have fewer peer interactions than traditionally schooled children
- [ ] Age-segregated school environments produce measurable clique formation and in-group/out-group dynamics
- [ ] Social anxiety rates differ between homeschooled and traditionally schooled populations
- [ ] Homeschooled adults report equivalent or better social functioning than traditionally schooled adults

**Known caveats going in:**
- Peer interaction frequency is not the same as social skill development — volume is not quality
- Co-op participation, extracurriculars, and community involvement vary widely by homeschool family — this is a confounding variable
- Adult social outcome studies are limited in number and sample size

**Finding:** *(to be written after EDA)*

---

## Section 3 — Cost

**The question this section answers:**
What does homeschooling actually cost a family, and how does it compare to public per-pupil expenditure?

**Claims to test:**
- [ ] Average annual family cost of homeschooling (curriculum, materials, programs)
- [ ] Public school per-pupil expenditure as a comparison baseline
- [ ] Hidden costs — parent time, foregone income, reduced workforce participation
- [ ] Cost variation by homeschool approach (classical, unschooling, hybrid)

**Known caveats going in:**
- Family cost data is largely self-reported through advocacy organization surveys
- Foregone income is real but difficult to quantify and not consistently captured
- Public per-pupil expenditure includes infrastructure and administrative costs that are not comparable to a family's direct curriculum spend

**Finding:** *(to be written after EDA)*

---

## Section 4 — Long-Term Outcomes

**The question this section answers:**
How do homeschooled individuals fare in college, careers, and civic life compared to their peers?

**Claims to test:**
- [ ] College acceptance rates for homeschooled applicants
- [ ] College GPA and graduation rates for formerly homeschooled students
- [ ] Career outcomes and income levels
- [ ] Civic engagement — voting, volunteering, community participation

**Known caveats going in:**
- Long-term outcome data is sparse and heavily influenced by the self-selection problem
- College-going homeschooled students are not representative of all homeschooled students
- Longitudinal studies on this population are limited

**Finding:** *(to be written after EDA)*

---

## Section 5 — The Hard Truths

**The question this section answers:**
What does the data say about the real risks and documented downsides of homeschooling — and what does it not say?

**Claims to test:**
- [ ] Documented cases of abuse occurring under homeschool cover
- [ ] Regulatory gaps — which states have the least oversight and what correlates with that
- [ ] Outcomes for children homeschooled against their will or in neglectful environments
- [ ] The difference between what motivated, engaged homeschool families produce and what the policy environment allows for all homeschool families

**Known caveats going in:**
- Abuse cases are real but represent a minority of homeschool families — the data must not conflate the exception with the norm
- The absence of oversight data is itself a data point — states with no reporting requirements produce no data on bad outcomes
- This section is not an argument against homeschooling; it is an honest accounting of the risk environment

**Finding:** *(to be written after EDA)*

---

## Summary Verdict

*(to be written last — after all five sections are complete)*

This section will state, in plain language, what a reasonable person should conclude after reviewing the evidence across all five categories. It will identify where the data is strong, where it is weak, and where a homeschooling parent should focus their attention as they make decisions for their family.

---

## Methodological Notes

- All findings are weighted by the `methodology_grade` of their supporting sources
- Stats with `selection_bias_flag = 1` are presented with that flag visible
- Stats with `sample_size` below 100 are treated as low-confidence and noted
- Conflicting stats are presented side by side where `conflicts_with` is populated
- Era filters are always applied — pre-2012 and post-2020 findings are never aggregated without explicit disclosure
