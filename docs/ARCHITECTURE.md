# Architecture

## Runtime and hosting

This is a Django 5.2 monolith with server-rendered templates/CSS, a small exam-autosave JavaScript layer, Django admin, and Gunicorn. Render runs its Docker service. PostgreSQL stores users, course content metadata, assignments, immutable attempt snapshots, responses and audit events. Private lesson/question files live in S3-compatible storage or an explicitly mounted persistent disk. WhiteNoise serves built static assets.

Builds collect static assets only; production database migrations belong to a single release/startup workflow. `/health/` checks database readiness. No serverless adapter, Vercel configuration, default administrator or automatic demo data remains in the current workflow.

## Data model

- **Module**: stable code, title/description, author, active flag and default pass mark.
- **Lesson**: module text/resource, order and draft/published state.
- **Enrollment**: unique student/module pair; does not grant exam access.
- **Category / Question / Option**: module-aligned reusable question bank and choice correctness.
- **Exam / Assignment**: published rules/schedule and explicit candidate access/extra time.
- **Attempt / AttemptQuestion / AttemptOption**: timed sitting and immutable question/option snapshots.
- **Response**: selected snapshot keys, server-calculated correctness and marks.
- **AuditEvent**: linked application event hashes and contextual details.

## Authorization

Module authors and administrators edit lessons; enrolled students see published active-module lessons. Generic protected-media routing serves question images only; private lesson downloads use their enrollment/ownership checks. Staff exam preview is read-only. Candidate mutation routes check ownership; services reject cross-attempt questions and unauthorized submissions. Administrators alone manage staff identities; Django model permissions still govern admin actions.

## Transactions and scoring

Assignment row locks serialize candidate starts on PostgreSQL. Attempts snapshot valid published questions and require the configured question count rather than changing the syllabus silently. Deadline expiry commits before a validation error is returned for exhausted attempts. Response/submission locks prevent writes after marking. Multiple choice uses exact set equality; the result percentage uses decimal arithmetic and half-up rounding.

The global PostgreSQL audit writer uses a transaction-scoped advisory lock before reading/inserting the chain head, including the first event. SQLite tests exercise sequential correctness, not production concurrent-worker behavior. Existing corrupted chains are reported rather than repaired.

## Email

Resend's HTTPS backend sends HTML and plain text. Invitations use Django password-set tokens rather than raw credentials. `PUBLIC_BASE_URL` (default Render origin) produces absolute action links. Notices run after successful database commit and are best-effort/synchronous; failures do not roll back grading. Guaranteed delivery requires an outbox/queue and provider reconciliation that are not included here.

## Explicit limits

The system is not multi-tenant, a payment platform, regulatory approval or browser proctoring. Email identity uniqueness is form-validated but not fully case-insensitive database constrained. No email verification/rate limiting, file antivirus service, automatic orphan cleanup, durable email retry queue or independent audit notarization is provided. See [operations](OPERATIONS.md) and [verification](TEST_REPORT.md) for release gates and untested integrations.
