# Render-era source review

Reviewed a fresh copy of the public repository's `main` branch downloaded on 2026-10-10. The Git endpoint could not be cloned in this environment (certificate verification failed); the source was retrieved from GitHub's codeload archive instead. This is a source review, not a scan of the live Render database, secrets or service.

## Baseline and result

The unchanged latest source discovered 50 Django tests; 49 passed and `test_staff_can_view_student_attempt_question` failed (expected 200, received 404). After the fixes and regression additions, 76 tests pass. See [executed verification](TEST_REPORT.md).

## Defects fixed

| Area | Defect / consequence | Change |
|---|---|---|
| Admin bootstrap | Restarts reset administrator passwords/profiles, could promote an existing student, and purged demo records (or crashed on protected relations). A fallback public password existed. | Explicit one-time bootstrap, no defaults, no mutation of existing accounts, no data deletion. |
| Render trust | Wildcard Render hosts/origins and old preview origins were trusted globally. | Exact Render hostname/custom origins; reject unsafe production defaults. |
| Persistence | Render could silently use SQLite or lose uploaded files on an ordinary container filesystem. | Require PostgreSQL and configured private storage/persistent-disk path; document that the mount must actually exist. |
| Docker | Secrets, old patches and runtime files could enter the image via `COPY . .`. | `.dockerignore`; remove committed environment files and obsolete artifacts. |
| Release workflow | Build/startup scripts mixed migrations and bootstrap, while Compose duplicated them. | Build writes only static assets; one explicit startup workflow; custom commands bypass it. |
| Local storage setup | MinIO bucket setup lacked its environment, hid failures, and did not gate application startup. | Share private local configuration, wait with bounded retries, fail on errors, initialize private bucket, gate web startup. |
| Staff preview | Student question pages returned 404 to staff; allowing mutation would violate student ownership. | Explicit read-only preview without autosave, flags, first-viewed writes or expiry mutation. |
| Question-bank integrity | Dashboard/start self-healing published all drafts, reparented similar-module questions and silently reduced exam length. | Remove that side effect; require the full configured valid published pool. |
| Stratified sampling | Sparse categories could overdraw when the target was smaller than the number of categories. | Exact target, random tie-breaking and balanced allocation within capacity. No unsupported regulatory-standard claim. |
| Exam import | Module normalization used a length inconsistent with the schema and could reparent questions away from their category. Mixed modules/unrelated drafts could be published together. | Match module code length; preserve importer-owned module/category pairs; one-module transactional exam import; only newly imported questions published. |
| Form feedback | Exam form validation errors were not displayed; Create Exam omitted the combined upload cap. | Visible linked field errors, 25 MB combined limit, active-student assignment choices. |
| Attempt integrity | Response services did not check a question belonged to the locked attempt; expiry could roll back on a resume-limit error; closed attempts could still be flagged. | Source linkage checks, committed expiry, deadline-derived status, locked closed-flag rejection. |
| Results retention | Staff deletion erased attempts/results with an exam; admin attempt deletion remained possible. | Preserve attempts; close exams instead; disable attempt deletion in admin. |
| Administrative identity | Users with user-edit permission could target privileged users, including demotion/email reset paths. | Hide/protect staff identities from regular instructors and recheck original identity before save. |
| Account validation | Malformed JSON/non-string fields or invalid email/field lengths could cause 500s; ambiguous case-insensitive usernames caused login exceptions. | Validated candidate endpoint; consistent form identity checks/password validators; fail closed on legacy ambiguity. |
| Email links | Attempt HTML used an unset setting and emitted relative URLs; accommodation duration was ignored. | Canonical absolute `PUBLIC_BASE_URL`, Render fallback, plain-text URLs and actual timed duration. |
| Lesson boundaries | Unrelated staff saw draft metadata; generic media routing could bypass lesson access checks; reserved/unroutable module codes and clearing the only attachment caused unusable content. | Consistent owner/enrollment checks, question-image-only generic routing, safe codes and resource/text validation. |
| CSV/API logs | User text could execute spreadsheet formulas; Resend error payloads were echoed into logs. | Neutralized formula-like CSV cells and status-only provider errors. |
| Operations/docs | README logo missing; demo/default-account, persistence, backup and serverless claims were stale. | ADK logo, Render-first docs, corrected local backup commands, removal of stale HTTP captures/checksum manifest/old patch and Vercel guide. |

## Deliberate boundaries / follow-up

- No schema migration is introduced; existing users, results and historical audit events are not rewritten.
- A PostgreSQL advisory transaction lock now serializes the audit writer across workers. Sequential SQLite tests pass, but actual concurrent PostgreSQL load has not been executed here. Existing forks cannot be repaired by changing new writes; verify them on your own database.
- Admin model permissions must still be assigned deliberately. Staff status alone is not a grant of every Django admin permission.
- Case-insensitive username/email checks are application-level, not a full database uniqueness migration; simultaneous identity creation and pre-existing duplicates remain follow-up work.
- Public signup/password reset have no built-in email-ownership verification or rate limiter. Add anti-abuse controls before high-traffic public use.
- Post-commit emails remain synchronous best-effort sends without a durable retry queue. No live Resend delivery, storage upload, Render deployment, Docker execution or backup restore was performed.
- Setting `MEDIA_ROOT` is not proof that a persistent disk is mounted/writable. Verify the actual Render mount and migrate existing files explicitly.
- Signed historical result codes depend on the signing key; any required exposed-key rotation needs a documented transition plan.
- HSTS preload remains intentionally opt-in. Browser/accessibility/penetration testing and regulator approval are not inferred from test success.
- The patch removes files from the next commit only. Revoke exposed credentials and separately clean history/releases/forks; do not assume deletion makes old secrets safe.
