# Architecture and decision contracts

Vantage AI remains a Python/Streamlit application. `app.py` composes the interface;
the `vantage/` package owns the contracts and calculations. Plotly supplies the
interactive radar and bar charts. No database, external analytics service, or
separate frontend is required.

## Modules

| Module | Responsibility |
| --- | --- |
| `models.py` | Strict Pydantic schemas, normalized inputs, complete grids, safe source links |
| `research.py` | Supported Google Gen AI SDK, bounded requests, search grounding, claim mapping |
| `calculations.py` | Effective ratings, scores, uncertainty ranges, roadmap, snapshot identity |
| `session.py` | Analysis activation, overrides, reset, request throttling, private session cache |
| `exports.py` | Formula-safe CSV and an executive PDF using the same decision snapshot |
| `charts.py` | Plotly views that preserve unknown values as missing data |
| `demo.py` | Clearly labeled fictional sample products and ratings |
| `config.py` | Explicit server-side secrets and configuration only |

## Research pipeline

1. Validate one focal product, one to three distinct competitors, and optionally
   five distinct user-selected features. Unicode normalization and case folding
   prevent accidental duplicates. Control characters and excessive lengths fail
   validation; names are serialized as data, not interpolated instructions.
2. If custom criteria are absent, ask Gemini for exactly five feature hypotheses
   and a category, using a structured response schema. These are comparison
   criteria, not validated customer research.
3. Request competitive research with the supported `google_search` tool. The
   prompt prioritizes official documentation, product pages, and pricing, and
   requires plan/scope caveats. A two-stage pipeline avoids relying on support for
   combining JSON-schema output mode and search tools in a particular model.
4. Validate the research JSON with exact cell IDs, required enums, explanation
   limits, a complete product-by-five-feature grid, and no extra fields. Reject
   duplicate keys and malformed or incomplete JSON. Valid JSON code fences are
   accepted; damaged responses are not guessed or silently repaired.
5. Map grounding supports to each assessment's original JSON span. A support must
   fall entirely within that assessment, refer to the correct response part,
   and point to a valid grounding chunk. UTF-8 byte offsets and unique exact-text
   supports are handled. Broad, ambiguous, or cross-assessment supports fail closed.
6. Accept citation URLs **only** from SDK grounding chunks, never from model JSON
   or prose. Public HTTPS links are required. Local/private addresses, executable
   schemes, embedded credentials, and nonstandard ports are rejected. The app does
   not fetch citation URLs itself, avoiding a server-side URL-fetch surface.
7. Without claim-linked support, retain the criterion but mark the assessment
   **Unverified**. No ungrounded ratings are substituted after a search failure.
   Users may inspect, override, reset, or export the resulting workspace.

The model classifies linked claims as explicit facts or interpretations. The UI
calls these **Source-backed** and **AI inference**. Source linkage is provenance,
not independent verification of truth or availability. Confidence is qualitative:
moderate for linked claims, low for interpretation, unknown for insufficient
evidence. User judgments and fictional samples have separate labels.

The evidence inspector shows the model segment associated with the citation,
not an alleged verbatim quotation from a fetched source page. Users can open the
source to inspect the underlying evidence. Google-provided search suggestions,
when returned, are displayed in an isolated Streamlit component iframe.

## Scoring and uncertainty

For each product, Yes = 1, Partial = 0.5, No = 0; Unverified has no numeric value.

```
known-feature score = 100 * sum(known weight * rating) / sum(known weights)
assessed coverage   = 100 * sum(known weights) / sum(all weights)
source coverage     = 100 * sum(source-backed fact weights) / sum(all weights)
lower overall bound = 100 * sum(known weight * rating) / sum(all weights)
upper overall bound = lower bound + 100 * unknown weight / sum(all weights)
```

No assessed weight produces **N/A**, not zero. The bounds illustrate uncertainty;
they do not assert that missing features are absent or present. The radar leaves
unknown values as gaps and does not connect through them. The bar chart shows
known-feature scores with assessed and source-backed coverage in hover details.
Scores are feature coverage judgments, not market share or business performance.

Manual ratings count as assessed, but do not become source-backed facts. Source
coverage excludes overrides, sample data, and AI inferences. The source context
in an overridden record remains explicitly attached to the **original** AI claim.

## Roadmap

```
gap      = max(0, strongest assessed competitor rating - focal-product rating)
priority = gap * importance * impact / effort
```

Importance is 1–10 in the interface; impact and effort are relative 1–5 user
assumptions. They are not measured business metrics. If the focal rating or all
competitor references are unknown, the priority is **Research needed**. Supported
priorities sort descending, with stable feature-order tie breaking; research
tasks follow without fabricated numeric scores. Every item includes its reference,
rationale, and a next action. Competitive gaps alone do not establish demand.

## State and cost controls

An immutable analysis stores original research. A separate override map stores
user ratings and explanations. Table deltas update that map before the rerun, so
charts, scores, and exports reflect corrections immediately. Weight changes do
not write to the override map. Reset clears edits and rotates editor keys while
retaining weights and roadmap assumptions.

The active request fingerprint includes product names, competitors, and custom
features. Changing inputs hides previous findings until matching research is
active. New analysis resets its workspace state. AI insights and prepared PDFs are
bound to a fingerprint including the effective ratings, weights, and roadmap;
they are hidden when that snapshot changes.

Research is cached for 30 minutes **within the session**, with at most five entries
and model/version-specific keys. A refresh is explicit. Insights run only on a
button click and cache up to five decision snapshots. Sliders and edits make no
API requests. Each session has a 30-second request cooldown and ten paid actions
per hour. A thread-safe, process-wide budget limits actual SDK calls, including
retries (60 per hour by default). These controls reset on process restart and are
not a provider billing cap or a multi-replica quota.

SDK timeouts are 40 seconds per attempt; transient timeouts/server failures retry
once. Quota, access, model, and grounding failures have safe public messages.
Raw provider exceptions, keys, and secrets are not rendered. The default model is
configurable without code changes. The unused legacy sentiment helper is retained
for compatibility with the supported SDK; it is not part of the dashboard workflow.

## Privacy and output safety

API keys remain server-side in Streamlit secrets or explicit environment variables.
No credential is accepted through a visitor-facing field. Session caches are not
shared across visitors. No durable analysis store is configured. Feedback is
voluntary, prepared in memory, and downloaded by the user; there is no remote
feedback submission or database. Opt-in usage measurements contain action counts
only, with no product names, user identifiers, or background transmission.
Streamlit's usage statistics are disabled in the app configuration.

CSV cells are quoted, UTF-8 encoded, and protected against spreadsheet formula
injection. PDF text and links are XML-escaped. Embedded fonts cover common glyphs;
unsupported characters appear as visible U+ codes, while CSV retains full Unicode.
Exports use the same effective assessments and calculation functions as the UI.

## External contracts

- [Google Gen AI Python SDK](https://googleapis.github.io/python-genai/)
- [Gemini search grounding](https://ai.google.dev/gemini-api/docs/google-search)
- [Streamlit data editor](https://docs.streamlit.io/develop/api-reference/data/st.data_editor)

Grounding metadata and model availability depend on the provider and API account.
Automated tests mock calls; successful tests do not establish live API availability
or independently validate the model's research quality.
