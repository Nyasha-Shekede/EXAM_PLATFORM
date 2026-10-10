# Operations and security

Use [Render deployment](RENDER_DEPLOYMENT.md) for release configuration and [README](../README.md) for local setup. Environment files are deliberately absent from Git, ignored by `.gitignore`, and excluded from Docker images by `.dockerignore`. Django does not automatically load `.env`; Compose loads your privately created local file.

## Secrets already committed in the past

Deleting a tracked file only removes it from the next commit. It does not erase Git history, forks, clones, build layers or deployed environments. Treat any real credentials in the former environment files as exposed:

1. Rotate/revoke the Resend key, storage credentials, database passwords and any exposed administrator passwords at their providers.
2. Update Render's Environment settings (and private local files) to match. Review provider access logs.
3. If `SECRET_KEY` was exposed, plan a signing-key rotation: sessions, password-reset tokens and historical result verification depend on it. Changing it invalidates signatures based on the old key; do not casually rotate it as an ordinary deploy step.
4. Coordinate repository-history cleanup with the team using a tool such as `git filter-repo` for the former environment files and sensitive patch artifacts. Back up first, plan force-push/reclone requirements, and remove stale releases/build artifacts. History rewriting is separate from this patch and is not performed automatically.
5. Do not publish `.env`, database dumps, student CSV exports or patch files containing secret-bearing deletion hunks. The update patch deletes sensitive files with forward-only binary deletion blocks that do not contain their original bytes.

## Administrator lifecycle

Create the initial administrator with `createsuperuser` or explicit temporary `ADMIN_*` credentials. `ensure_admin` never resets existing passwords, reactivates accounts, promotes students or purges records. Remove bootstrap passwords after first use. Administrators manage instructors; instructors can manage students only when appropriate Django permissions are granted. Avoid sharing administrator accounts.

Use admin invitation-resend actions for students who never finished setting a password. A normal password-reset form is intentionally available only after a usable password is established. Passwords are hashed, not reversible or viewable.

## Releases and readiness

Back up before upgrades. Builds install dependencies and collect static assets; they do not write to production databases. For a single web instance, the entrypoint applies migrations once on startup and performs optional non-destructive bootstrap. For multiple replicas, run migrations in one release job and set `RUN_MIGRATIONS=0` on the web processes. An explicit container command bypasses entrypoint bootstrap/migrations.

`/health/` checks database connectivity without exposing configuration. Set it as the Render Health Check Path. HTTPS redirection/cookies, exact allowed hostnames and exact trusted origins protect the rest of the app. Keep `DEBUG=0` in production. `SECURE_HSTS_PRELOAD` remains opt-in; do not enable browser preload without understanding the domain-wide commitment.

## Data integrity

Standalone question imports remain drafts. Dashboard/start requests never publish or move questions. Create Examination publishes only its new import and rejects mixed-module sheets. The configured number of valid published questions must exist; the app does not silently shorten an examination. Review invalid pools in admin before publishing a live exam.

Attempts preserve question/option text and image names/hashes. Instructor question previews are read-only and do not mark an attempt expired merely by viewing it. Deadline expiry persists if a student resumes after using their last attempt. Exams with attempts cannot be deleted from the app and attempt records are read-only/non-deletable in admin. Close exams rather than erasing results; any retention deletion must be a separately authorized and backed-up operation.

## Audit trail

```bash
python manage.py verify_audit_chain
```

The PostgreSQL writer uses a transaction-scoped advisory lock to serialize the global hash chain across workers. Verification reports existing forks or tampering; this patch does not rewrite historical audit data. An application hash chain is not an independent notarized log and cannot protect against a privileged actor rewriting the database and its hashes. IP-change events are hints, not evidence of cheating; proxies/mobile networks can change addresses. Configure trusted proxies and access-log policy before interpreting them.

## Backups and restoration

Back up PostgreSQL and uploads separately, encrypt them and limit access. Test a restore in an isolated environment with outbound email disabled. Preserve media object names and the signing secret in your protected recovery plan.

For local Compose only:

```bash
make backup-db       # Uses POSTGRES_USER/POSTGRES_DB from the database container
make backup-media    # Archives /app/media from the running web container
```

The local media backup covers the filesystem volume only. If uploads use MinIO/S3, export/version/back up that bucket separately; an empty `/app/media` archive is not an object-storage backup. Restore database dumps with matching PostgreSQL tooling and test all attachment/image paths. Never run `make clean` or `docker compose down -v` against data you need to retain.

## Monitoring and known limitations

Monitor failed Resend sends, database health, Gunicorn worker exits/timeouts, disk/bucket capacity and unusual authentication activity. Do not record passwords, tokens, request email bodies or secret values in logs. Resend error response bodies are not echoed into application logs.

- Email sends are synchronous and best-effort; there is no durable retry queue/outbox or delivery webhook reconciliation.
- Public registration/password reset need rate limiting and email verification/anti-abuse controls before a high-traffic launch.
- Application forms reject case-insensitive duplicate usernames/emails, but Django's underlying user table does not enforce case-insensitive email uniqueness. Simultaneous registrations/direct database writes can still create ambiguity; review existing duplicates and plan a database constraint migration separately.
- CSV exports neutralize formula-like user-controlled cells, but exports still contain student personal data and must be handled privately.
- Attachments are authenticated downloads; malware scanning and retention-based orphan-file cleanup are not included.
- No browser lock-down or webcam proctoring is claimed. No regulatory approval is implied.
- PostgreSQL load/concurrency tests, Docker image execution, live Render/Resend integration, full accessibility checks and backup restores are separate production qualification tasks.
