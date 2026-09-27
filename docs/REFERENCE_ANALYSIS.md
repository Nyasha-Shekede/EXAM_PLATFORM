# Reference-system analysis and scope decision

## Material reviewed

I reviewed all four supplied PDFs:

| File | Pages | What it establishes |
|---|---:|---|
| `Untitled document (1).pdf` | 26 | Drone-X candidate sign-in/dashboard screenshots plus the underlying SpeedExam candidate-help material: upcoming exams, rejoin, payment, player controls, result history, notifications, profile and mobile advice. |
| `set2.pdf` | 2 | A real Drone-X BVLOS attempt-review screen and question-level review: question ID, marks, status, time spent, section summary, scorecard download and radio-choice display. |
| `Nyasha Shekede-BVLOS Mock-(Attempt 3).pdf` | 1 | Exported scorecard containing unique exam ID, candidate, attempt, start/end, 3/10 = 30%, fail, time and section summary. |
| `set3.pdf` | 40 | A prior functional/technical analysis of SpeedExam, including question types, XLSX imports, exam assembly, delivery, reporting, APIs, security, architecture, open-source options and delivery roadmap. |

The first reference contains live-looking credentials and personal data. I did **not** copy them into the application, demo data or documentation. They should be treated as compromised and rotated if real.

## What Drone-X is doing in the supplied evidence

The candidate screens are a branded SpeedExam deployment rather than evidence of a bespoke Drone-X engine. The help pages visibly retain SpeedExam terminology, screenshots and old system requirements. The observed workflow is:

1. organization issues a candidate account;
2. candidate signs in and sees upcoming/history pages;
3. exam appears according to its schedule;
4. the player shows one question at a time with IDs, marks, section, radio inputs, navigation/flags/clear and a timer;
5. rejoin supports interrupted link-based tests;
6. completed attempts produce score/history/review pages and a PDF scorecard;
7. reports track correct, partially correct, incorrect, negative and unanswered counts, per-question time and section summaries.

The prior analysis in `set3.pdf` states that SpeedExam separates reusable questions from exams; supports admin-created, Excel-imported or self-registered candidates; and imports questions with a rigid `.xlsx` template, ordered headers and an `Add Questions` sheet. It also mentions media/formulas and a paid conversion service for unstructured sources. Those statements are secondary analysis, not direct access to Drone-X's database or admin interface.

## Data-input comparison

| Concern | Reference behavior evidenced/described | This custom system |
|---|---|---|
| Questions | Reusable bank; manual authoring; documented XLSX template with rigid structure. | Manual entry plus a ten-column XLSX/CSV sheet. IDs/type/defaults are automatic; validation reports every bad row before any write. |
| Single vs multiple | Distinct question formats and controls. | Mandatory `question_type` (`SINGLE` or `MULTIPLE`); never inferred from a PDF shape. |
| Correct answers | Format-specific answer configuration. | `correct_options`: one key for `SINGLE`; comma-separated exact set for `MULTIPLE`. Correctness is stored server-side and omitted from active-exam HTML. |
| Candidate roster | Admin, Excel import or self-registration are described. | Staff create controlled local accounts. Self-registration is intentionally absent. Bulk roster import is not in release 1; use Django administration or add a reviewed roster importer later. |
| Exam construction | Many generic commercial options. | Module, count, duration, pass mark, attempts, availability, shuffling, post-result review and individual extra time only. |
| Recovery | Rejoin code and saved progress. | Authenticated candidate resumes the same in-progress attempt from the dashboard; each answer is saved. No insecure public rejoin code is needed. |
| Payments | Full payment help appears on pages 11–13 of the candidate document. | Completely omitted from schema, routes, templates and dependencies. |
| PDFs as input | Paid/assisted conversion is mentioned; arbitrary extraction is not reliable. | Not accepted as an authoritative import. Convert to the template and have an instructor review it. |

## Why I did not ingest arbitrary question PDFs

PDF is a presentation format. A visible checkbox may be a vector, glyph or flattened pixel; reading order may be wrong; an answer key may be in a different layer; and diagrams may become detached from stems. Automatic PDF-to-question conversion would create silent assessment errors. The safe workflow is structured import → validation → preview/review → publish. PDF or OCR assistance can be added as a *draft generator*, but a human must confirm every question and correct answer.

## Product scope chosen

I retained only functions needed to run an academy's exams:

- identity and explicit assignment;
- question bank and controlled import;
- images;
- timed delivery/recovery;
- marking/pass decision;
- results/PDF/audit.

I excluded commerce, public test sales, packages, tenant billing, marketing pages, candidate self-registration, SMS, generic notifications, self-study/Test Maker, AI proctoring and broad API integrations. This keeps the failure surface and instructor workload proportionate to one local academy.

## Legal and evidentiary caution

The reference supplied by the user and Gemini text mention a 75% “CAAZ/SACAA” threshold, but no primary regulation or approved training manual was supplied. I therefore made 75% a default/configurable field and do not label the software regulator-certified. Before operational release, the academy must map each exam to its approved curriculum and authority-specific rule set.
