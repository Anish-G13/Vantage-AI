# Usability study: 5–10 participants

This is a study plan, not completed research. No interviews, adoption, satisfaction,
or product impact are claimed from this release.

## Participants and setup

Recruit 5–10 people who compare products: product managers, early-stage founders,
analysts, or students doing product research. Include both spreadsheet-oriented
and less technical participants. Run individual 20–30 minute sessions. Obtain
consent before recording; use public product examples and avoid confidential work.

Start in the fictional demonstration to isolate usability from API availability.
Then, where an API key and quota are available, use a real product landscape.
Explain that ratings may be incomplete and that feedback is voluntary. Do not
demonstrate the core controls before observing unaided task performance.

## Tasks

| Task | Observable completion condition |
| --- | --- |
| Understand the comparison | Participant identifies the focal product, two competitors, and five criteria. |
| Interpret uncertainty | Participant explains why a 100% known-feature score with low assessed coverage is incomplete. |
| Audit one claim | Participant opens a source and checks product identity, plan, and whether it supports the actual feature claim. Unverified is acceptable if evidence is missing. |
| Correct an assessment | Participant edits a rating and adds a note; the score and roadmap change. |
| Change priorities | Participant changes importance, then impact/effort; explains why the ranked order changes. |
| Preserve and reset edits | Participant confirms edits survive a weight change, then restores original assessments. |
| Avoid stale results | Participant changes a product and recognizes that old results are hidden. |
| Export a decision brief | Participant downloads comparison CSV, roadmap CSV, and the current PDF. |
| Recover from unavailable research | Participant creates a manual workspace with five features or uses the demo. |

Record completion, assistance, time, errors, and comments for each task. Ask:
"What would you do next?" rather than coaching toward the intended control.

## Measures and initial hypotheses

Targets below are proposed release hypotheses, not achieved results:

- Core task completion without assistance: initially aim for at least 80%.
- Score/uncertainty comprehension: participant correctly explains unknowns and coverage.
- Citation precision: manually review sampled source-backed claims; record supported,
  partly supported, unsupported, wrong plan, wrong product, or inaccessible source.
- Time to complete a defensible comparison and export: compare with the participant's
  existing workflow on a matched task; record review time, not just generation time.
- Override persistence and export consistency: expected to pass every observed check.
- Ease of use and usefulness: collect 1–5 ratings only after tasks; report the sample
  size, distribution, and task context rather than generalizing to all users.
- Missing-evidence recovery: note whether people can proceed without assuming absence.

The optional session event counter records actions, not outcomes or successful
completion. Do not interpret a button click as task success or adoption.

## Feedback and analysis

Use Export & feedback to prepare an anonymous JSON file. Nothing is submitted
remotely. Participants may voluntarily share that file through an agreed channel;
the app does not send messages. Keep the consent process and collection channel
separate from product usage. Do not collect identifying information unnecessarily.

Summarize findings in a task-by-participant matrix. Separate usability failures,
research-quality failures, API availability issues, and feature requests. Prioritize
issues by observed severity and recurrence, and test fixes with follow-up tasks.
Do not publish participant quotes or recordings without permission.
