# Changelog

## 2.0.0 — 2026-10-23

- Added claim-level Google Search grounding, source inspection, explanation, date,
  and provenance; unsupported assessments become Unverified.
- Added manual rating/notes overrides with reset and immediate recalculation.
- Added explicit uncertainty coverage and bounds; missing evidence is not No.
- Added editable impact/effort prioritization, ranked roadmap, rationale, and actions.
- Preserved five-feature discovery, weighting, charts, CSV, and AI strategic insights.
- Added roadmap CSV, executive PDF, fictional demo, manual workspaces, and feedback download.
- Kept each PDF source heading, URL, and linked claim together across page breaks.
- Fixed stale input/result association and stale AI-insight/PDF snapshots.
- Added schemas, bounded retries/timeouts, session cache, cooldowns, and process budgets.
- Migrated to the supported Google Gen AI SDK and pinned tested runtime dependencies.
- Used standard JSON Schema requests for discovery and insights, with regression
  checks against actual SDK serialization. Added safe operator diagnostics and
  explicit handling for invalid or expired credentials returned as HTTP 400.
- Added automated tests, CI configuration, setup/architecture/testing documentation,
  a usability study plan, and a PM case study.

This release does not claim new users, interviews, adoption, satisfaction, revenue,
or independently measured productivity improvements.
