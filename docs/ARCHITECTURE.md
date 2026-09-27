# Architecture and technical specification

## Design goals

1. One academy, not multi-tenant SaaS.
2. Correct marking and recoverable delivery before optional sophistication.
3. Keep correct-answer data off the active candidate page.
4. Preserve exactly what each candidate saw.
5. Use conventional components a small team can operate.

## Component view

```text
Browser
  ├─ Candidate portal: dashboard → player → result/review/PDF
  └─ Staff portal: Django administration + validated import
                │ HTTPS
                ▼
Django monolith (Gunicorn)
  ├─ authentication / CSRF / authorization
  ├─ question and exam services
  ├─ attempt snapshot + secure randomization
  ├─ autosave + deadline enforcement
  ├─ exact-match marking + analytics
  ├─ PDF generation
  └─ hash-linked audit events
                │
      ┌─────────┴─────────┐
      ▼                   ▼
PostgreSQL          Media volume/object store*
records/state       question images
```

`*` Release packaging uses a persistent Docker volume. An S3-compatible private store is a sensible future option for multiple application nodes.

## Key entities

| Entity | Purpose |
|---|---|
| `Module` / `Category` | Curriculum organization and category analytics. |
| `Question` / `Option` | Reusable authored item, image metadata and server-side correct flags. |
| `Exam` | Delivery rule: pool module, draw count, duration, threshold, attempts, window and review policy. |
| `Assignment` | Candidate authorization and individual extra time. |
| `Attempt` | One timed sitting, authoritative expiry, score, result and verification code. |
| `AttemptQuestion` / `AttemptOption` | Immutable-in-practice snapshot of stem, option text/order, correct mapping, marks, category and image reference. |
| `Response` | Candidate's currently saved displayed option keys and final mark. |
| `AuditEvent` | Actor/action/object metadata linked to the previous audit event hash. |

The attempt snapshot is critical. Changing the question bank after an attempt does not rewrite history. Option letters are assigned *after* shuffling; the response is checked against the snapshot's correct displayed keys.

## Attempt lifecycle

```text
ASSIGNED
   │ start: authorization + schedule + limits + valid pool
   ▼
IN_PROGRESS ── autosave/resume ── IN_PROGRESS
   │ submit                         │ authoritative deadline
   ▼                                ▼
SUBMITTED                         EXPIRED
   └──────── score + pass + audit + result ────────┘
```

Creation and submission use database transactions and row locks. The server stores `expires_at`; the JavaScript clock is only a display. Every save rechecks status and time. A reconnect opens the existing attempt and does not reshuffle it.

## Selection and marking

- `secrets.SystemRandom` samples questions and shuffles options.
- Only published, structurally valid questions can be drawn.
- Release 1 draws uniformly from all published questions in the selected module. It does not enforce category quotas.
- `SINGLE`: selected key set must equal the one correct key.
- `MULTIPLE`: selected key set must exactly equal all correct keys.
- No partial or negative credit is implemented.
- Percentage is `score / max_score × 100`, rounded half-up to two decimals.
- Pass is `percentage >= exam.pass_mark`.

These are deliberate, simple rules. If the academy needs weighted partial credit or category-level mandatory minima, they require an approved scoring specification and new tests rather than ad-hoc settings.

## Active-exam data boundary

The HTML sends:

- snapshot stem/image/alt text;
- displayed option key and text;
- candidate's saved selection;
- navigation/status data;
- server-derived deadline.

It does not send `is_correct`, source option keys, explanations or answer mappings. The normal candidate views also ownership-check every attempt. Staff-only routes use `is_staff` authorization.

## Result verification and audit

At submission, the application computes an HMAC-SHA-256 code over attempt ID, candidate, exam, score, maximum, percentage and submission timestamp using the deployment secret. HMAC avoids the insecure `SHA256(data + secret)` construction in the Gemini draft. It detects record/slip mismatch inside this deployment; it is **not** a qualified electronic signature.

Audit events contain a `previous_hash` and unique `event_hash`. `python manage.py verify_audit_chain` checks linkage. This is tamper-evident at application level, not immutable storage: a database administrator who can rewrite the entire chain and application secret can defeat it. Export logs to append-only/WORM storage if that threat matters.

## Question-image design

Images are first-class attachments, not embedded base64 inside CSV cells.

1. Instructor enters the exact picture filename in the simple sheet's `Image` column and supplies `Image Description`.
2. On the same page, the instructor selects all referenced picture files directly; no ZIP is required.
3. Import limits each image to 5 MB, permits PNG/JPEG/WebP and verifies its actual format with Pillow.
4. Storage assigns a server-side path; SHA-256 is recorded.
5. The attempt snapshot records image path, alt text and content hash.
6. Candidate UI uses responsive sizing and a caption/alt description.

Operationally, never put the answer in the filename or alt text. Crop out answer keys/annotations. Use at least ~1200 px width for maps/charts when fine detail matters, while keeping each file below 5 MB. Verify readability on the smallest supported screen. The current local media route is public when its URL is known; use a private/signed-media implementation if exam-content confidentiality requires it.

## Security controls present

- salted Django password hashes and standard password validators;
- username or unique-email login;
- CSRF protection, secure cookies in production, clickjacking denial and MIME sniffing protection;
- server-side authorization and deadline checks;
- transactional attempt creation/submission;
- no correct-answer fields in active HTML;
- randomized selection/order using an operating-system CSPRNG;
- validated spreadsheet/image uploads, filename matching, size limits and image signature checks;
- result HMAC and audit linkage;
- production process runs as a non-root container user;
- parameterized queries through the Django ORM.

## Known boundaries

- no webcam/lockdown/proctoring; browser event restrictions cannot guarantee candidate behaviour;
- no category quotas, essay/manual grading, partial credit or negative marking;
- no bulk candidate importer or email invitation service;
- no formal question approval/version workflow (attempt snapshots preserve historical delivery);
- no built-in virus scanner, private signed media URLs or external WORM audit sink;
- no high-availability deployment or load test is included;
- accessibility was designed semantically but has not been independently audited against WCAG 2.2;
- no primary aviation regulation was encoded or validated.
