# Vantage AI

**Competitive evidence. Clear product decisions.**

Vantage AI is a Streamlit workspace for researching a product and up to three
competitors, correcting the findings, and prioritizing the next product decisions.

- **Application:** https://vantageai.streamlit.app/
- **Repository:** https://github.com/Anish-G13/Vantage-AI
- **Product case study:** [docs/PRODUCT_CASE_STUDY.md](docs/PRODUCT_CASE_STUDY.md)

## What the product does

1. Identify five critical comparison features with Gemini, or supply your own.
2. Research product capabilities using Google Search grounding, prioritizing
   official documentation and pricing pages.
3. Inspect explanations, claim-linked sources, research date, provenance, and
   qualitative confidence beside each assessment.
4. Edit Yes / Partial / No / Unverified ratings, add optional notes, and restore
   original assessments without losing feature weights.
5. Compare weighted scores with assessed coverage and uncertainty, using
   interactive tables, radar charts, and bar charts.
6. Adjust impact and effort to rank product opportunities with a transparent
   formula, rationale, and next action.
7. Export comparison CSV, roadmap CSV, and a styled executive PDF with evidence.
8. Prepare voluntary feedback and optionally download anonymous session event counts.

A clearly labeled **fictional demonstration** works without a key. A **manual
workspace** works without AI when you provide five features. The application
preserves the original five-feature comparison workflow and navy visual design.

## Evidence, not invented certainty

Source URLs come only from the provider's grounding metadata, never from
model-authored citation fields. Each source must map to the individual claim.
No usable support means **Unverified**, not No. No is reserved for documented
absence; Partial describes a limitation rather than missing information.

**Source-backed** means linked provenance, not independent feature testing.
**AI inference**, **user overrides**, **sample data**, and **insufficient evidence**
remain distinct. Open sources to verify product identity, plan, and current scope.
The inspector shows the model claim linked by grounding; it does not present it
as a verbatim source-page excerpt.

Known-feature scores exclude Unverified values and display assessed coverage
alongside them. A high score with low coverage is incomplete evidence. Importance,
impact, and effort are user assumptions, not measured business outcomes.

## Local setup

Use **Python 3.11 or 3.12**. Runtime dependencies are pinned to tested versions.

~~~bash
git clone https://github.com/Anish-G13/Vantage-AI.git
cd Vantage-AI
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
~~~

For live research, create `.streamlit/secrets.toml` using the example file:

~~~toml
GOOGLE_API_KEY = "your-key-here"
GEMINI_MODEL = "gemini-2.5-flash"
MAX_HOURLY_AI_CALLS = 60
~~~

The existing `GOOGLE_API_KEY` configuration is preserved. `GEMINI_API_KEY` is also
accepted. These explicit environment variables work for local development too.
Never commit the real secrets file; it is ignored. No key is needed for demo/manual mode.

~~~bash
streamlit run app.py
~~~

In Streamlit Community Cloud, keep the existing repository, `main` branch, and
`app.py` entry point. Keep the existing URL and server-side secret. The
[deployment guide](docs/DEPLOYMENT.md) explains verification and recovery.

## Scoring and roadmap

~~~text
Known-feature score = 100 * sum(weight * rating) / sum(assessed weights)
Rating values       = Yes: 1, Partial: 0.5, No: 0, Unverified: excluded
Competitive gap     = max(0, strongest assessed competitor rating - your rating)
Priority score      = competitive gap * importance * impact / effort
~~~

No known rating produces N/A. If the focal product or competitor reference is
unverified, the roadmap creates a research task without a numeric priority.
Source-backed coverage excludes manual judgments and AI inference. Overall
bounds show how unknowns could affect the full comparison.

See [architecture and calculation contracts](docs/ARCHITECTURE.md) for exact
formulas, provenance handling, session behavior, and limitations.

## Reliability, cost, and privacy

- Strict schemas validate names, five features, all assessment cells, enums, and
  AI insight structure. Malformed responses fail safely.
- Changing inputs hides old results; changing decisions invalidates old insights/PDFs.
- Original research is immutable. Overrides and roadmap assumptions survive reruns.
- Weighting, edits, charts, and exports do not trigger AI requests.
- A 30-minute private session cache avoids repeated research. Refresh and AI
  insights are explicit actions.
- A 40-second timeout per attempt, one transient retry, a session cooldown/hourly
  action limit, and a configurable process budget bound requests. These are
  application controls, not a provider billing cap.
- Feedback is prepared in the session for voluntary download, not sent to a
  database. Anonymous event counts are off by default and are not transmitted
  to analytics. There is no persistent shared analysis store.
- CSV export neutralizes spreadsheet formulas. PDF content is escaped, fonts are
  embedded, and uncommon glyphs use visible Unicode codes instead of missing boxes.

Standard research uses feature discovery plus grounded research; supplying five
features skips discovery. Optional strategic insights use an additional request.
Retries can add one call per stage. Grounding/search charges and available models
depend on the API account.

## Tests and documentation

~~~bash
python -m pip install -r requirements-dev.txt
ruff check .
ruff format --check .
python -m pytest --cov=vantage --cov-report=term-missing
~~~

Automated tests use mocked external calls. CI runs the suite on Python 3.11 and
3.12. Passing tests do not establish live API access or independent research accuracy.

- [Testing and manual QA](docs/TESTING.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Usability study for 5–10 participants](docs/USABILITY_TESTING.md)
- [Product-management case study](docs/PRODUCT_CASE_STUDY.md)
- [Changelog](CHANGELOG.md)

No interviews, adoption numbers, satisfaction scores, revenue, or measured
commercial impact are fabricated. The study guide and future roadmap describe
planned validation; they are not completed research.
