"""Vantage AI — Streamlit entry point. Run: streamlit run app.py."""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from pydantic import ValidationError

from vantage import __version__
from vantage.calculations import decision_fingerprint, effective_assessments, prioritize, scores_for
from vantage.charts import bar_chart, radar_chart
from vantage.config import settings
from vantage.demo import demonstration
from vantage.exports import comparison_rows, csv_bytes, executive_pdf, roadmap_rows
from vantage.models import RATINGS, ResearchRequest, cell_id, utc_now
from vantage.research import CallBudget, GeminiResearcher, ResearchError, manual_analysis
from vantage.session import (
    activate,
    apply_editor_delta,
    apply_roadmap_delta,
    cache_analysis,
    cached_analysis,
    is_current,
    record_event,
    reserve_session_request,
    reset_overrides,
)

st.set_page_config(page_title="Vantage AI | Competitive Intelligence", page_icon="◈", layout="wide")
st.markdown(
    """<style>
    .block-container {max-width: 1320px; padding-top: 3.5rem; padding-bottom: 3rem;}
    h1,h2,h3 {color: #123E68; letter-spacing: -.025em;}
    [data-testid="stMetric"] {background: #FFFFFF; border: 1px solid #DCE5EF;
        border-radius: 12px; padding: 1rem;}
    [data-testid="stMetricLabel"] {font-weight: 600;}
    div[data-testid="stSidebarContent"] {padding-top: 1rem;}
    .vantage-kicker {font-size: .74rem; color: #387082; letter-spacing: .15em;
        font-weight: 700; margin-bottom: .25rem;}
    .vantage-rule {border-top: 3px solid #123E68; margin: 1rem 0 1.5rem;}
    .stButton > button[kind="primary"] {background: #123E68; border-color: #123E68;}
</style>""",
    unsafe_allow_html=True,
)

state = st.session_state
config = settings()


@st.cache_resource
def shared_budget(limit: int) -> CallBudget:
    return CallBudget(limit)


def show_demo() -> None:
    sample = demonstration()
    state["product_name"] = sample.request.product
    for i in range(3):
        state[f"competitor_{i}"] = (
            sample.request.competitors[i] if i < len(sample.request.competitors) else ""
        )
    state["feature_input"] = ""
    activate(state, sample)
    record_event(state, "demo_loaded")


def edit_assessments(key: str, product_index: int) -> None:
    try:
        apply_editor_delta(state, state["active_analysis"], product_index, state[key])
    except ValueError:
        st.error(
            "That assessment edit is invalid. Choose a listed rating and a note under 1,000 characters."
        )


def edit_roadmap(key: str) -> None:
    try:
        apply_roadmap_delta(state, state[key])
    except ValueError:
        st.error("Use whole numbers from 1 to 5 for impact and effort.")


def restore_assessments() -> None:
    reset_overrides(state)


def run_research(request: ResearchRequest, force: bool) -> None:
    cache_key = config.model + ":v2:" + request.fingerprint()
    cached = None if force else cached_analysis(state, cache_key)
    if cached:
        activate(state, cached)
        st.success("Loaded this session's research cache. No new AI request was made.")
        return
    researcher = None
    try:
        reserve_session_request(state)
        researcher = GeminiResearcher(
            config.api_key, config.model, shared_budget(config.max_hourly_calls)
        )
        with st.status("Researching the comparison…", expanded=True) as status:
            analysis = researcher.analyze(request, progress=st.write)
            status.update(label="Research workspace ready", state="complete", expanded=False)
        activate(state, analysis)
        cache_analysis(state, cache_key, analysis)
        record_event(state, "research_completed")
    except (ResearchError, ValueError) as exc:
        st.error(str(exc))
        record_event(state, "research_failed")
    finally:
        if researcher:
            researcher.close()


with st.sidebar:
    st.markdown("### Vantage AI")
    st.caption("A product research workspace")
    st.button("Explore the demonstration", on_click=show_demo, width="stretch")
    st.divider()
    st.subheader("Your landscape")
    st.text_input("Your product", key="product_name", max_chars=80, placeholder="e.g. Linear")
    for i, example in enumerate(["Asana", "ClickUp", "Optional"]):
        st.text_input(
            f"Competitor {i + 1}", key=f"competitor_{i}", max_chars=80, placeholder=example
        )
    with st.expander("Choose your own five features"):
        st.text_area(
            "Five features, one per line (optional)",
            key="feature_input",
            height=155,
            max_chars=500,
            help="Leave blank for Gemini to propose five criteria. Enter five to use your own criteria or work without AI.",
        )
    force = st.checkbox(
        "Refresh existing research",
        help="Bypass this session's 30-minute cache. Uses new AI requests.",
    )
    analyze_clicked = st.button(
        "Research competitors", type="primary", width="stretch", disabled=not config.api_key
    )
    manual_clicked = st.button(
        "Start a manual workspace",
        width="stretch",
        help="Enter five features above. No API key or AI request is needed.",
    )
    st.caption(
        "Use public product names. Live research sends these names and criteria to Gemini and Google Search. "
        "New research replaces this workspace's edits; weights and manual changes never trigger AI requests."
    )
    if not config.api_key:
        st.info(
            "Live research is not configured. Try the demonstration or enter five features for a manual workspace."
        )
    st.divider()
    st.checkbox(
        "Keep anonymous session event counts",
        key="usage_opt_in",
        help="Off by default. Counts actions in this session only, without names or identifiers. "
        "Nothing is sent to an analytics service. You can download the counts with voluntary feedback.",
    )
    if not state.get("usage_opt_in"):
        state.pop("usage_counts", None)
    st.caption(f"Version {__version__} · Streamlit + Gemini")

st.markdown(
    '<div class="vantage-kicker">RESEARCH / COMPARE / PRIORITIZE</div>', unsafe_allow_html=True
)
st.title("Vantage AI")
st.write("Turn competitive evidence into clear product decisions.")
st.markdown('<div class="vantage-rule"></div>', unsafe_allow_html=True)

request = None
input_error = None
try:
    features = [f.strip() for f in state.get("feature_input", "").splitlines() if f.strip()] or None
    request = ResearchRequest(
        product=state.get("product_name", ""),
        competitors=[
            state.get(f"competitor_{i}", "").strip()
            for i in range(3)
            if state.get(f"competitor_{i}", "").strip()
        ],
        custom_features=features,
    )
except ValidationError as exc:
    input_error = exc.errors(include_input=False)[0]["msg"]

if analyze_clicked or manual_clicked:
    if request is None:
        st.error(
            "Check your inputs: " + (input_error or "Enter a product and at least one competitor.")
        )
    elif manual_clicked:
        try:
            activate(state, manual_analysis(request))
            record_event(state, "manual_workspace_created")
        except ValueError as exc:
            st.error(str(exc))
    else:
        run_research(request, force)

analysis = state.get("active_analysis")
if analysis is None:
    left, right = st.columns([1.35, 1])
    with left:
        st.subheader("Start with a question. Keep the evidence.")
        st.write(
            "Compare your product with up to three alternatives across five critical features. "
            "Inspect the sources, correct assessments, and prioritize the next product decisions."
        )
        st.markdown(
            "1. Enter product names or open the fictional demonstration.\n"
            "2. Research five criteria and inspect claim-level evidence.\n"
            "3. Adjust ratings and assumptions, then export the decision brief."
        )
    with right:
        with st.container(border=True):
            st.markdown("#### Evidence before certainty")
            st.write(
                "Source-backed facts, AI inferences, manual judgments, and missing evidence stay distinct. "
                "An unverified feature is never treated as absent."
            )
            st.caption("No account needed. Start with the demonstration to explore the workflow.")
    st.stop()

if request is None or not is_current(analysis, request):
    st.warning(
        "Your inputs have changed. Research this landscape or start a new manual workspace to see matching results. "
        "The previous analysis is hidden so old findings cannot be attributed to new products."
    )
    st.stop()

date_label = "Research snapshot" if analysis.mode == "Live research" else "Session snapshot"
st.caption(
    f"{analysis.discovery.category} · {analysis.mode} · {date_label}: {analysis.display_date}"
)
for notice in analysis.notices:
    st.info(notice)

workspace = state["workspace_id"]
with st.sidebar:
    st.divider()
    st.subheader("Feature importance")
    st.caption("1–10. Higher values give a feature more weight. These are your assumptions.")
    weights = [
        st.slider(
            feature.name,
            1,
            10,
            5,
            key=f"workspace_{workspace}_weight_{f}",
            on_change=record_event,
            args=(state, "weight_changed"),
        )
        for f, feature in enumerate(analysis.discovery.features)
    ]

overrides = state.get("overrides", {})
effective = effective_assessments(analysis, overrides)
assumptions = state.get("roadmap_assumptions", {})
impacts = [assumptions.get(f, {}).get("impact", 3) for f in range(5)]
efforts = [assumptions.get(f, {}).get("effort", 3) for f in range(5)]
roadmap = prioritize(analysis, effective, weights, impacts, efforts)
scores = scores_for(analysis, effective, weights)
fingerprint = decision_fingerprint(analysis, effective, weights, roadmap)
current_insights = (
    state.get("insights") if state.get("insights_fingerprint") == fingerprint else None
)

for col, (product, score) in zip(st.columns(len(scores)), scores.items()):
    with col:
        st.metric(product, "N/A" if score.score is None else f"{score.score:.1f}%")
        st.caption(
            f"Assessed weight: {score.assessed_weight_pct:.0f}% · Source-backed: {score.source_backed_weight_pct:.0f}%"
        )
st.caption(
    "Known-feature score: Yes = 1, Partial = 0.5, No = 0. Unverified is excluded, not scored as No. "
    "A high score with low assessed coverage is incomplete evidence. Source-backed excludes user overrides and AI inferences."
)

overview, evidence, roadmap_tab, exports = st.tabs(
    ["Overview", "Evidence & edits", "Product roadmap", "Export & feedback"]
)

with overview:
    st.subheader("Feature comparison")
    matrix = []
    for f, feature in enumerate(analysis.discovery.features):
        row = {"Feature": feature.name, "Importance": weights[f]}
        for p, product in enumerate(analysis.request.products):
            key = cell_id(p, f)
            row[product] = effective[key].rating + (" · edited" if key in overrides else "")
        matrix.append(row)
    st.dataframe(pd.DataFrame(matrix), hide_index=True, width="stretch")
    st.caption(
        "See Evidence & edits for explanations and sources beside each assessment. Edited ratings are user judgments."
    )
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(bar_chart(scores), width="stretch")
    with c2:
        st.plotly_chart(radar_chart(analysis, effective), width="stretch")
    st.caption(
        "Unverified values remain gaps in the radar chart. The radar uses raw feature ratings; importance weights affect the bar chart."
    )
    with st.expander("Scoring and uncertainty"):
        st.write(
            "Known-feature score = 100 × Σ(weight × rating) / Σ(assessed weights). "
            "Assessed coverage = assessed weight / total weight. Source-backed coverage includes only AI facts with claim-linked citations. "
            "Inference and manual ratings count toward assessed coverage but remain distinct from source-backed facts."
        )
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Product": p,
                        "Known score (%)": s.score,
                        "Assessed weight (%)": s.assessed_weight_pct,
                        "Source-backed weight (%)": s.source_backed_weight_pct,
                        "Possible overall lower (%)": s.lower_bound,
                        "Possible overall upper (%)": s.upper_bound,
                    }
                    for p, s in scores.items()
                ]
            ),
            hide_index=True,
            width="stretch",
        )
        st.caption(
            "The possible overall range illustrates unknown features taking values from 0 to 1; it does not assert that either bound is true."
        )
    st.subheader("Strategic interpretation")
    positive = [i.feature for i in roadmap if i.gap is not None and i.gap > 0]
    unknown = [i.feature for i in roadmap if i.gap is None]
    st.write(
        f"Competitive gaps: {len(positive)}. Criteria needing more evidence: {len(unknown)} of 5."
    )
    st.caption(
        "Competitive gaps are inputs to discovery, not proof that customers need a feature or that building it will produce ROI."
    )
    if st.button("Generate AI strategic insights", disabled=not config.api_key):
        researcher = None
        try:
            cache = state.get("insight_cache", {})
            if fingerprint in cache:
                state["insights"] = cache[fingerprint]
            else:
                reserve_session_request(state)
                researcher = GeminiResearcher(
                    config.api_key, config.model, shared_budget(config.max_hourly_calls)
                )
                with st.spinner("Interpreting this decision snapshot…"):
                    state["insights"] = researcher.insights(analysis, effective, weights, roadmap)
                state["insight_cache"] = dict(
                    [*list(cache.items())[-4:], (fingerprint, state["insights"])]
                )
            state["insights_fingerprint"] = fingerprint
            current_insights = state["insights"]
            record_event(state, "insights_generated")
        except (ResearchError, ValueError) as exc:
            st.error(str(exc))
        finally:
            if researcher:
                researcher.close()
    if current_insights:
        st.success("Strengths: " + current_insights.strengths)
        st.info("Context: " + current_insights.neutral_observations)
        st.warning("Risks / next decisions: " + current_insights.critical_gaps_risks)
        st.caption(
            "AI interpretation of this exact snapshot, including user judgments and assumptions. It is not new research."
        )
    elif state.get("insights"):
        st.caption(
            "The comparison or assumptions changed. Generate insights again to interpret the current snapshot."
        )
    if analysis.search_suggestions_html:
        with st.expander("Google Search suggestions"):
            # Provider-returned search attribution is isolated in a component iframe.
            components.html(analysis.search_suggestions_html, height=140, scrolling=True)

with evidence:
    st.subheader("Inspect the evidence. Correct the model.")
    st.caption(
        "Source-backed means the grounding provider linked a source to this claim. It does not mean the feature was independently tested. "
        "Confidence labels describe provenance, not a calibrated probability."
    )
    selected = st.selectbox(
        "Product to inspect and edit",
        analysis.request.products,
        key=f"workspace_{workspace}_product",
    )
    p_index = analysis.request.products.index(selected)
    st.button(
        "Restore original assessments",
        on_click=restore_assessments,
        help="Clear all manual changes. Keep weights and roadmap assumptions.",
    )
    baseline = [
        {
            "Feature": feature.name,
            "Original rating": analysis.assessments[cell_id(p_index, f)].rating,
            "Rating": analysis.assessments[cell_id(p_index, f)].rating,
            "Override note": "",
        }
        for f, feature in enumerate(analysis.discovery.features)
    ]
    editor_key = f"workspace_{workspace}_editor_{state['editor_revision']}_{p_index}"
    st.data_editor(
        pd.DataFrame(baseline),
        key=editor_key,
        on_change=edit_assessments,
        args=(editor_key, p_index),
        hide_index=True,
        width="stretch",
        disabled=["Feature", "Original rating"],
        column_config={
            "Rating": st.column_config.SelectboxColumn(options=list(RATINGS), required=True),
            "Override note": st.column_config.TextColumn(max_chars=1000, width="large"),
        },
    )
    st.caption(
        "Edits immediately recalculate scores, charts, and priorities. Notes are optional and included in exports and optional AI insights. "
        "Edits last for this session; download the comparison before leaving."
    )
    for f, feature in enumerate(analysis.discovery.features):
        key = cell_id(p_index, f)
        a, original = effective[key], analysis.assessments[key]
        with st.container(border=True):
            st.markdown(f"#### {feature.name}")
            st.caption(feature.description)
            st.write(f"{selected}: {a.rating} · {a.origin} · {a.basis}")
            st.caption("Confidence: " + a.confidence)
            st.text(a.explanation)
            if key in overrides:
                st.caption("Original research: " + original.rating + " · " + original.basis)
                st.text(original.explanation)
            if original.sources:
                st.caption("Sources attached to the original AI claim:")
                for n, source in enumerate(original.sources, 1):
                    st.link_button(f"{n}. {source.title[:100]}", source.url)
                    with st.expander(f"Inspect linked claim {n}"):
                        st.text(source.supported_text)
                        st.caption(
                            "This is the model text mapped to a source by grounding, not a verbatim excerpt fetched from that page. "
                            "Open the source to verify scope, plan, and current availability."
                        )
            else:
                st.caption("No source-backed evidence is attached to this assessment.")

with roadmap_tab:
    st.subheader("From competitive gaps to product decisions")
    st.write("Priority = competitive gap × importance × impact / effort.")
    st.caption(
        "Gap = max(0, strongest assessed competitor − your rating), using Yes=1, Partial=0.5, No=0. "
        "Impact and effort are relative 1–5 assumptions, not measured outcomes. Missing ratings create research tasks."
    )
    roadmap_key = f"workspace_{workspace}_roadmap_editor"
    st.data_editor(
        pd.DataFrame(
            [{"Feature": f.name, "Impact": 3, "Effort": 3} for f in analysis.discovery.features]
        ),
        key=roadmap_key,
        on_change=edit_roadmap,
        args=(roadmap_key,),
        hide_index=True,
        width="stretch",
        disabled=["Feature"],
        column_config={
            "Impact": st.column_config.NumberColumn(
                min_value=1, max_value=5, step=1, required=True
            ),
            "Effort": st.column_config.NumberColumn(
                min_value=1, max_value=5, step=1, required=True
            ),
        },
    )
    ranked = roadmap_rows(roadmap)
    st.dataframe(
        pd.DataFrame(
            [
                {
                    k: row[k]
                    for k in (
                        "Rank",
                        "Feature",
                        "Your rating",
                        "Competitive gap (0–1)",
                        "Priority score",
                    )
                }
                for row in ranked
            ]
        ),
        hide_index=True,
        width="stretch",
    )
    for item in roadmap:
        score = "Research needed" if item.priority is None else f"Priority {item.priority:.2f}"
        with st.expander(f"{item.feature} · {score}"):
            st.text(item.rationale)
            st.caption("Competitor reference: " + item.competitor_reference)
            st.write("Next action: " + item.next_action)

with exports:
    st.subheader("Take the decision brief with you")
    st.caption(
        "Exports contain the current ratings, overrides, importance weights, and prioritization assumptions. "
        "CSV includes explanations, provenance, and supporting source URLs."
    )
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "Download competitor comparison CSV",
            csv_bytes(comparison_rows(analysis, effective, weights, overrides)),
            "vantage_competitor_comparison.csv",
            "text/csv",
            width="stretch",
        )
    with c2:
        st.download_button(
            "Download prioritized roadmap CSV",
            csv_bytes(roadmap_rows(roadmap)),
            "vantage_prioritized_roadmap.csv",
            "text/csv",
            width="stretch",
        )
    if st.button("Prepare executive PDF", width="stretch"):
        with st.spinner("Preparing the current decision brief…"):
            state["pdf_report"] = (
                fingerprint,
                executive_pdf(analysis, effective, weights, roadmap, overrides, current_insights),
            )
            record_event(state, "report_prepared")
    report = state.get("pdf_report")
    if report and report[0] == fingerprint:
        st.download_button(
            "Download executive report PDF",
            report[1],
            "vantage_executive_report.pdf",
            "application/pdf",
            width="stretch",
        )
    elif report:
        st.caption("The analysis changed. Prepare the PDF again to export current figures.")
    st.divider()
    st.subheader("Voluntary product feedback")
    st.caption(
        "Feedback stays in this session. Download it and share it voluntarily with the project owner; "
        "there is no remote feedback database. Avoid names, contact details, or confidential information."
    )
    with st.form("feedback_form"):
        ease = st.select_slider(
            "Ease of use",
            options=[1, 2, 3, 4, 5],
            value=3,
            help="1 = very difficult, 5 = very easy",
        )
        usefulness = st.select_slider(
            "Perceived usefulness",
            options=[1, 2, 3, 4, 5],
            value=3,
            help="1 = not useful, 5 = very useful",
        )
        problems = st.text_area("Problems encountered (optional)", max_chars=2000)
        suggestions = st.text_area("Improvement suggestions (optional)", max_chars=2000)
        feedback_submitted = st.form_submit_button("Prepare anonymous feedback download")
    if feedback_submitted:
        feedback = {
            "submitted_at_utc": utc_now(),
            "app_version": __version__,
            "mode": analysis.mode,
            "ease_of_use": ease,
            "perceived_usefulness": usefulness,
            "problems": problems,
            "suggestions": suggestions,
        }
        if state.get("usage_opt_in"):
            feedback["anonymous_session_events"] = state.get("usage_counts", {})
        state["feedback_download"] = json.dumps(feedback, indent=2).encode()
        st.success(
            "Feedback prepared in this session. No feedback was transmitted or saved externally."
        )
    if state.get("feedback_download"):
        st.download_button(
            "Download anonymous feedback JSON",
            state["feedback_download"],
            "vantage_feedback.json",
            "application/json",
        )

st.divider()
st.caption(
    "Vantage AI · Evidence supports decisions; customer research and product validation determine what to build."
)
