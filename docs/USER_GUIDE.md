# Instructor and candidate guide

## Instructor: initial setup

1. Sign in at `/admin/` with a superuser account.
2. Under **Authentication and Authorization → Users**, create each candidate. Use a stable academy candidate number as username and a unique email. Do not give staff/superuser status.
3. Under **Modules**, create curriculum modules such as Air Law or Meteorology.
4. Add categories within each module. Categories drive the result breakdown.

## Instructor: add questions manually

1. Open **Questions → Add**.
2. Choose module and a category belonging to it.
3. Select `SINGLE` or `MULTIPLE` explicitly.
4. Enter the stem, marks, difficulty and optional explanation.
5. Optionally upload a PNG/JPEG/WebP diagram and provide meaningful alt text.
6. Add at least two options in the inline table and mark the correct option(s).
7. Save as `DRAFT`; independently review wording, answer and image; then change to `PUBLISHED`.

A `SINGLE` question must have exactly one correct option. A `MULTIPLE` question needs two or more and is marked only when the candidate selects the exact complete set.

## Instructor: bulk question import

The default importer now uses one short spreadsheet and one upload:

1. Visit `/staff/import/` and click **Download simple template**.
2. Fill one question per row on the `Questions` sheet.
3. Use `A` for one correct answer or `A,C` for multiple correct answers.
4. If a row uses a picture, enter its exact filename in **Image** and a useful description in **Image Description**.
5. Upload the spreadsheet. Select all referenced pictures in the optional picture field at the same time.
6. Click **Import questions** once.
7. Correct any row errors shown. Nothing is written when any row is invalid.
8. Review the imported drafts in administration and publish them when approved.

There is no question-code column, question-type column, marks column, difficulty column, status column, ZIP packaging, or validate-and-reupload step. The system:

- generates a unique question code;
- treats one correct letter as `SINGLE` and multiple letters as `MULTIPLE`;
- assigns 1 mark and medium difficulty;
- imports every question as `DRAFT`;
- creates missing modules/categories;
- uses `General` when Category is blank.

### The ten columns

| Column | Rule |
|---|---|
| `Module` | Required. Human-readable name, for example `Air Law`. |
| `Category` | Optional. Blank becomes `General`. |
| `Question` | Required question text. |
| `Option A`, `Option B` | Required. |
| `Option C`, `Option D` | Optional. |
| `Correct Answer` | `B` for one answer; `A,C` for multiple answers. In a hand-written CSV, quote comma-containing values or use `A;C`. |
| `Image` | Optional exact selected filename, for example `chart-04.png`. |
| `Image Description` | Required only with an image; describe it without revealing the answer. |

Imports are atomic: if one row or picture is invalid, no question from that upload is created.

## Instructor: create and assign an exam

1. Add an **Exam** as `DRAFT`.
2. Select one module. Release 1 draws from all valid, published questions in that module.
3. Set duration, count, pass mark, maximum attempts and optional availability dates.
4. Choose shuffling and whether answers may be reviewed after submission.
5. Publish only when the pool contains enough valid questions.
6. Add one **Assignment** per candidate. Use `extra_time_minutes` for an approved accommodation.

The pass mark defaults to 75% but is not hard-coded as a legal rule. Use the academy's approved requirement.

## Instructor: monitor results

- **Attempts** is read-only and shows status, percentage and pass/fail.
- **Audit events** records attempt start/submission/expiry and result-PDF downloads.
- Run `python manage.py verify_audit_chain` periodically and after restore.
- Candidate answer review is governed per exam. Keep it off when questions will be reused and disclosure is inappropriate.

## Candidate workflow

1. Sign in with issued username/email and password.
2. The dashboard shows assigned exams, availability, duration, pass mark and attempts remaining.
3. **Start examination** creates the timed attempt. Starting again resumes it; it does not create or reshuffle another sitting.
4. Read the type instruction. Circles mean one answer; squares mean all applicable answers.
5. Selecting an answer triggers autosave. Confirm the status says **Saved**. **Save & next** also posts the answer normally.
6. Use numbered navigation and **Flag for review**.
7. The displayed timer is synchronized to the server. If it reaches zero, the server closes and marks the attempt.
8. On final review, check unanswered/flagged counts and submit. Submission is irreversible.
9. View the recorded score, topic breakdown and PDF result slip. Correct answers appear only if the instructor enabled review.

## Connection loss

Sign in again on the same or another supported browser. The dashboard offers **Resume attempt** and the same question/option order. Time continues while disconnected because the deadline is server-owned. Very late offline changes cannot be accepted after expiry.

## Image-authoring checklist

- Is the image legally reusable and free of personal data?
- Is all necessary text legible on a phone/tablet?
- Does colour have a redundant label/pattern?
- Does alt text convey the information needed by a candidate who cannot see it, without giving away the answer?
- Is the image free of answer ticks, instructor annotations and metadata-based spoilers?
- Does the rendered preview preserve orientation and aspect ratio?
