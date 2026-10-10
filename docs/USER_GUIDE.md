# Instructor and student guide

## Accounts and roles

Students can register at `/signup/` (if public registration is enabled) or receive an instructor-created email invitation. Invitations contain a link to set a password; no raw passwords are sent. Sign in using username or email. If a student has never set a password and their invitation expires, an authorized instructor/administrator uses the user-list **Send Password Setup / Reset email** action to resend it.

Administrators create/promote instructors. Regular instructors cannot edit, delete, reset or take over administrator/instructor accounts. Instructor access to Django admin additionally requires appropriate model permissions; `is_staff` grants admin-site access, not every model permission.

## Learning modules

1. Choose **Modules → Create module**. Use a stable code of letters/numbers/hyphens/underscores (30 characters maximum). `NEW` is reserved for the create route.
2. Add a title/description and lessons. Plain-text lessons require text or an attachment (PDF, PNG, JPG/JPEG or TXT, at most 10 MB).
3. Draft lessons are visible to the module author/administrator, not students or unrelated instructors. Publish each lesson when ready.
4. Students enroll in active modules to see published lessons and private resources. Inactive modules are unlisted from the student catalog.
5. Course enrollment does not automatically assign any exam. Exams remain deliberately assigned by staff.

## Question import and exam creation

Download `/staff/import/template.xlsx`. The current template has nine columns:

`Category, Question, Option A, Option B, Option C, Option D, Correct Answer, Image, Image Description`

`Section`/`Stem` are accepted aliases for Category/Question. Legacy Module columns are accepted for standalone imports; **Create Examination requires one module per sheet**. A correct-answer value like `A` gives single choice; `A;C` gives multiple choice. Multiple-choice marking requires the selected set to exactly match the correct set; no partial credit is awarded.

Choose pictures in the same upload form. The image column matches a selected filename (or its stem without the extension); supply alt text that conveys the diagram without giving away the answer. Spreadsheet limit: 12 MB; each picture: 5 MB; total exam import: 25 MB.

**Standalone Import** stores draft questions for review. Dashboard/attempt-start requests no longer silently publish drafts, rename/reparent questions or lower the exam question count. Review/publish questions deliberately in administration.

**Create Examination** imports and publishes only the questions from that sheet; unrelated drafts remain untouched. Set duration (1–480 minutes), pass mark, attempt count, shuffling, optional schedule and selected active students. If the valid published pool is smaller than the configured question count, repair it before opening the exam rather than expecting an automatic shorter exam.

Availability uses the configured academy timezone (default Africa/Harare). Future exams are hidden until their schedule opens; expired exam cards are hidden unless an open attempt remains. Extra time is set on the assignment in administration.

## Students taking an exam

1. Sign in and open **Dashboard**. Only explicitly assigned exams are accessible.
2. Start/resume the attempt. Starting again resumes the existing snapshot; time continues while disconnected.
3. Choose one or all answers as instructed. Watch for **Saved** and use normal **Save & next** submission if autosave fails.
4. Use the numbered question navigator and review flags while the attempt remains open.
5. Review unanswered/flagged questions and submit. The server deadline is authoritative; late attempts are marked expired.
6. View score, category breakdown and PDF result slip. Correct answers appear only when answer review is enabled.

## Instructor previews and records

Staff can view a student question page in read-only preview. It does not autosave, change flags, set first-viewed timestamps or finish the student's attempt. The preview can display an expired-but-not-yet-finalized snapshot without mutating it; the student workflow performs expiry.

Results/audit records are read-only. CSV exports are available to authorized admin users. Exams that have attempts cannot be permanently deleted via the app; change their status to Closed. Retention deletion is a separate administrative policy, not a routine UI action.

## Content and accessibility checks

Use legally reusable images, legible mobile text and redundant labels instead of color alone. Provide meaningful alternative text without hints. Test keyboard navigation, screen readers and lesson/PDF content on your target devices. The platform's styles/labels support accessibility, but passing automated tests is not an independent accessibility certification or aviation-regulator approval.
