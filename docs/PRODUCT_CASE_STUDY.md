# Vantage AI: from feature comparison to evidence-based product decisions

## 1. Product overview

Vantage AI is a Streamlit competitive-intelligence workspace for comparing a
product with up to three alternatives across five critical features. It connects
source inspection, editable assessments, weighted comparisons, roadmap assumptions,
and executive exports in one workflow.

The upgrade implements product and reliability capabilities. It does not claim
new customer adoption, validated satisfaction, revenue, or measured business impact.

## 2. User problem and audience

Product managers, founders, and analysts often move between vendor pages,
spreadsheets, and presentation documents to answer two questions: what can each
product do, and which differences warrant further product investment?

An AI-generated feature matrix is insufficient when users cannot inspect its
evidence, correct mistakes, or connect a gap to explicit prioritization assumptions.
The intended value is a faster path to an auditable decision, including review time.
That value remains a hypothesis for user testing.

## 3. Existing limitations

The original application already provided Gemini feature discovery, Yes/No/Partial
ratings, adjustable weights, radar and bar charts, CSV export, and strategic insights.
Its ratings lacked traceable sources; absent values could behave like No; changing
product inputs could display old results; and users could not correct the matrix.
Its roadmap listed gaps without an impact-versus-effort decision framework. The
legacy SDK and loosely validated responses also created reliability concerns.

## 4. Prioritization rationale

Evidence and state correctness came first because an attractive matrix with
unsupported or misattributed claims can mislead a product decision. Manual correction
came next because research outputs need human judgment. Transparent prioritization
and consistent exports completed the decision workflow. Visual polish supports
those tasks; it does not replace them.

Demo and manual modes were included so people can evaluate the workflow when
model access, grounding, or quota is unavailable. Durable collaboration and a larger
data platform were deferred to keep the existing architecture practical.

## 5. Implemented features

- Claim-linked source URLs from Gemini search grounding, with explanation, date,
  provenance, qualitative confidence, and evidence inspection for each assessment.
- Distinct Source-backed, AI inference, Unverified, Manual, and Sample states.
- Editable ratings and optional notes; recalculated scores, charts, and roadmap;
  original research retained for audit; reset without losing other assumptions.
- Weighted known-feature scores with assessed coverage, source-backed coverage,
  and possible overall bounds instead of treating unknowns as absent.
- Adjustable impact and effort, transparent priority formula, ranked opportunities,
  strategic rationale, and next actions. Missing evidence creates research tasks.
- Navy Streamlit dashboard with onboarding, loading/error states, and fictional demo.
- Comparison CSV, roadmap CSV, and a styled executive PDF with evidence appendix.
- Voluntary feedback download, opt-in session event counts, and a 5–10 person study guide.
- Modular Python contracts, API controls, state isolation, tests, and CI configuration.

## 6. Technical and product trade-offs

**Provenance versus unsupported completeness.** A rating is accepted only when
grounding metadata maps a source to that individual claim. Broad citations or
missing supports can leave more Unverified cells, but a full matrix was not allowed
to take precedence over traceability. Source linkage is still not independent
verification; users must review plan, scope, and source quality.

**Human control versus apparent precision.** User overrides are preserved separately
and remain labeled judgments. Confidence is qualitative rather than an invented
probability. Impact and effort are assumptions, not measured business outcomes.

**Useful scores versus unknown data.** Unknowns are excluded from the known-feature
score and coverage is shown alongside it. Bounds expose remaining uncertainty.
The UI avoids presenting a missing feature assessment as a confirmed product gap.

**Continuity versus unnecessary platform work.** Streamlit, Python, Plotly, the
existing entry point, and the public URL remain the deployment architecture.
Sessions and downloads were chosen over adding a database or accounts before
testing whether the workflow is useful. The supported Google Gen AI SDK replaces
the legacy dependency.

**Cost versus freshness.** Research and AI insights are explicit actions. A private
session cache, cooldowns, bounded retries, and a shared process budget limit repeated
calls. Refresh remains available; weights and edits need no additional AI requests.

## 7. Reliability and evidence quality

Strict schemas reject incomplete grids, invalid ratings, extra model fields,
duplicate JSON keys, and model-authored citation URLs. The request fingerprint
prevents stale results from appearing under changed product names. Decision
fingerprints invalidate outdated AI insights and prepared PDFs after edits.

Automated tests cover calculations, missing evidence, claim attribution, overrides,
state transitions, errors, exports, and Streamlit startup/interactions. Calls are
mocked in automated tests. The test suite is engineering validation, not proof of
research accuracy or user value; see [testing notes](TESTING.md) for run evidence.

## 8. Success metrics to measure

Measure unaided task completion, time to an evidence-reviewed comparison, source
support precision, uncertainty comprehension, override persistence, export accuracy,
and perceived usefulness. Compare matched tasks against participants' existing
workflows. Report sample sizes and distributions. No new measured performance
improvement is asserted by this case study.

## 9. User-testing plan

Run moderated sessions with 5–10 intended users using the
[usability-testing guide](USABILITY_TESTING.md). Begin with the fictional demo, then
use real product research where available. Observe source inspection, correction,
prioritization, stale-input handling, and export. Collect voluntary feedback after
tasks and prioritize observed problems before expanding scope.

## 10. Future roadmap — proposed, not implemented

1. Independently evaluate citation support and compare alternative grounding strategies.
2. Test whether product URLs, category context, and plan selection reduce identity ambiguity.
3. Add customer-opportunity evidence alongside competitor gaps after observing real workflows.
4. Consider saved/shared workspaces only if user testing supports a recurring collaboration need.
5. Consider durable, consent-based feedback collection and robust multi-instance budgets.
6. Revisit prioritization using customer reach, confidence, and delivery constraints once actual
   user and engineering evidence is available.

The current release demonstrates an implemented decision workflow. Its next product
decisions depend on observed user behavior and research-quality evaluation.
