# Testing and release checks

## Automated suite

Install `requirements-dev.txt`, then run from the repository root:

```bash
ruff check .
ruff format --check .
python -m pytest --cov=vantage --cov-report=term-missing
```

| Area | Checks |
| --- | --- |
| Weighted scoring | Yes/Partial/No arithmetic, unknown exclusion, coverage, bounds, zero weights, invalid inputs |
| Overrides | Original immutability, manual provenance, notes, reset, persistence, product isolation, undo |
| Roadmap | Gap detection, rank order, impact/effort sensitivity, missing evidence, invalid assumptions |
| Session | Request identity, stale-result detection, cache TTL, fresh workspace reset, request limits, opt-in counts |
| Schemas | Exactly five distinct features, complete grids, invalid enums/extra fields, duplicate names/JSON keys |
| Evidence | Claim-level supports, real SDK metadata contract, missing/unsafe/broad citations, fabricated URLs |
| API | Mocked grounding failure, timeout retries, quota/access/model errors, safe public messages, budgets |
| Exports | Score/CSV consistency, overrides, UTF-8, spreadsheet formula safety, roadmap fields, readable PDF contents |
| Streamlit | Startup, demo, stale inputs, edits through weighting/reset, PDF preparation, feedback download |

All external model calls are mocked in automated tests. Source URLs and responses
in tests are synthetic fixtures, not product research. Tests assert behavior
rather than model accuracy or successful live API access.

The GitHub workflow runs on Python 3.11 and 3.12 with read-only repository
permissions and no API key. The local environment uses Python 3.12.

## Release verification — 2026-10-24 UTC

- 94 automated tests passed locally, with 95% coverage of the core `vantage`
  modules. Lint, formatting, and installed dependency checks passed. GitHub
  checks passed on Python 3.11 and 3.12, including SDK request serialization
  through a mocked HTTP transport. Automated tests never use a real API key.
- Version 2.0.0 was verified at the existing public URL after rebuilding the
  existing Community Cloud app on Python 3.12. The URL and server-side key
  configuration were preserved.
- In the deployed fictional demo, changing one rating updated Northstar PM's
  known score from 50.0% to 62.5%. Increasing that feature's importance from
  5 to 6 preserved the override and produced 64.3%. Reset restored the original
  ratings while preserving the new weight. The ranked roadmap remained usable.
- A real Linear/Asana request completed feature discovery and search-grounded
  research. All ten cells received claim-linked sources in that single
  response. Real AI strategic insights also completed. This confirms an
  operational provider connection at the time of the check, not independent
  accuracy, continuing availability, or validated customer value.
- Sample grounding links resolved to official Linear and Asana pages. The
  response also cited third-party sites; source linkage does not certify each
  detail, product plan, or comparative judgment. Review the actual evidence.
- The production comparison CSV and executive PDF downloaded successfully.
  The ten comparison rows and the PDF scores matched the displayed snapshot.
  Every page of the eight-page research report was rendered for visual review;
  citation grouping was improved after detecting split source blocks.
- Early live checks exposed a request-format rejection with the legacy schema
  request path. The standard `response_json_schema` path and a fresh app
  process resolved it. Regression tests cover both discovery and insight
  serialization; operator diagnostics omit messages, prompts, and credentials.

No external user study, interviews, adoption metrics, satisfaction results,
revenue impact, or independent assessment-accuracy benchmark were conducted.

## Manual interface checks

1. Start `streamlit run app.py` with no key. Verify onboarding, demo, and manual mode.
2. Load the demo and inspect table/chart layout, legibility, navigation, and source labels.
3. Edit a rating and note, change inspector products, and return. Confirm the edit
   persists. Change weights and confirm the same.
4. Undo an edit, then reset all assessments. Check that stale overrides do not remain.
5. Change impact/effort, observe rank changes, then undo to restore default assumptions.
6. Change a product input. Old findings must disappear until matching research is active.
7. Export CSV and PDF, then change a decision. Old PDFs and AI insights must no
   longer be presented as the current snapshot.
8. Render every PDF page and inspect clipping, table splits, orphaned headings,
   and readability. Verify exported figures against the dashboard.
9. Prepare voluntary feedback. Confirm no remote submission and no event counts
   unless opted in.

## Live API smoke check

With valid access and quota, research recognizable public products. Record the
model, date, whether grounding returned supports, accepted source-backed/inferred
cells, and any provider error. Open sampled sources and check the actual claim
and plan. Generate insights only after the cooldown. A successful response does
not establish independently validated accuracy or customer value.

Without usable claim links, unsupported cells must remain Unverified and the
workspace must still support edits and exports. Record model/quota failures as
provider limitations rather than successful live tests.

## Release discipline

Review changes for secrets, personal data, unexpected network destinations,
missing evidence paths, stale state, and obsolete SDK imports. Keep unrelated
repository files. Verify the deployed app at the existing URL; a commit alone
does not prove deployment. User validation is a separate study in
`USABILITY_TESTING.md`.
