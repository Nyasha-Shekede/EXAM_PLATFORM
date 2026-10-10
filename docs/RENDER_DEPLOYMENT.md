# Render deployment and upgrade guide

This app is one Django monolith served by Gunicorn. Render runs the Docker web service; **PostgreSQL and uploads must be persistent**. A container's ordinary filesystem is ephemeral even on a paid web-service plan unless a persistent disk is attached.

## Existing service: apply this review safely

1. Back up the live PostgreSQL database and uploads. Record the current `SECRET_KEY` in a secret manager. Removing `.env` from Git does not change Render's stored environment variables, but a rebuild discards unmounted container files.
2. Check Environment settings before redeploying:
   - `DEBUG=0` and a strong stable `SECRET_KEY` (32+ characters).
   - A **PostgreSQL** `DATABASE_URL`, not a SQLite path.
   - `RESEND_API_KEY` and a verified `DEFAULT_FROM_EMAIL`.
   - `AWS_STORAGE_BUCKET_NAME` with private bucket credentials **or** `MEDIA_ROOT` pointing to an attached persistent disk.
   - `ALLOWED_HOSTS` with exact custom hostnames if you use them. Render's `RENDER_EXTERNAL_HOSTNAME` is automatically allowed. Remove `*` and `.onrender.com` wildcard values.
   - Optional `CSRF_TRUSTED_ORIGINS` with your exact HTTPS origins; remove `https://*.onrender.com` and old preview-platform wildcards.
   - `PUBLIC_BASE_URL=https://your-canonical-domain` for email links; defaults to Render's own HTTPS origin.
3. The reviewed app now refuses unsafe Render configurations. If uploads currently live only in the container, copy them to the bucket/disk **before redeploying**. Preserve file names recorded in the database. Merely switching the storage backend does not copy old files.
4. Remove `DEV_ADMIN_PASSWORD`/`ADMIN_PASSWORD` after the first account exists. `ensure_admin` accepts old variable names for compatibility, but never changes an existing administrator's password/profile or deletes demonstration records.
5. Apply migrations as part of the release workflow. No schema migration is introduced by this patch; running `migrate --noinput` still checks any pending upstream migrations. With one web instance, startup migrations remain enabled by default. With multiple replicas, run a single migration job and set `RUN_MIGRATIONS=0` on web processes.
6. Redeploy the **existing service**; do not apply a new Blueprint as a substitute for an upgrade unless you intend to create new resources. Check `/health/`, login, a lesson download, a test invitation and exam attempt email, then run `python manage.py verify_audit_chain`. Pre-existing broken audit links are reported, not rewritten.

## New service / Blueprint

[`../render.yaml`](../render.yaml) describes a Docker web service and PostgreSQL database. It keeps evaluation plans rather than silently upgrading you to a paid plan. Verify current plan availability, database expiry/retention, disk support and pricing in Render before provisioning. Evaluation/free services are not a production availability guarantee.

1. Connect the repository from Render's **New → Blueprint** flow, or create a Docker web service manually.
2. Set the required storage and email secrets prompted by the Blueprint. Private object storage is the default Blueprint option; alternatively remove the bucket variables, attach a persistent disk and set `MEDIA_ROOT` to its mount path. A disk mount must be writable by the container's `app` user (UID 10001). Test write/read access after deployment.
3. Keep the generated signing secret stable and save it in a secret manager. The build uses only a disposable build-time key for `collectstatic`; it does not migrate the database or create accounts.
4. Create the first administrator in the Render service shell with `python manage.py createsuperuser`. If a shell is unavailable, temporarily set `ADMIN_USERNAME`, `ADMIN_EMAIL` and a strong `ADMIN_PASSWORD`; startup will create that account only if it does not exist. Remove the bootstrap password immediately afterward. No default administrator exists.
5. Set the Health Check Path to `/health/` for the current service. Readiness checks the database and returns 503 when it is unavailable. It is the only URL exempted from HTTPS redirection for internal health probes.

## Environment reference

Names are configuration interfaces, not values to commit. Keep actual secrets in Render.

| Name | Purpose |
|---|---|
| `DEBUG` | `0` in production |
| `SECRET_KEY` | Strong stable signing secret |
| `DATABASE_URL` | Render internal PostgreSQL connection string or other managed PostgreSQL URI |
| `ALLOWED_HOSTS` | Comma-separated exact custom hostnames; Render hostname added automatically |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated exact HTTPS custom origins if needed |
| `PUBLIC_BASE_URL` | Canonical HTTPS origin for emails, no path/query |
| `RESEND_API_KEY` | Resend credential |
| `DEFAULT_FROM_EMAIL` | Verified sender on your Resend domain |
| `AWS_STORAGE_BUCKET_NAME` | Private object-storage bucket (if using S3-compatible storage) |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | Least-privilege bucket credentials; AWS roles can replace these where supported |
| `AWS_S3_ENDPOINT_URL`, `AWS_S3_REGION_NAME` | Provider-specific endpoint/region |
| `AWS_S3_ADDRESSING_STYLE` | Optional addressing style; defaults to path for custom endpoints |
| `MEDIA_ROOT` | Absolute mount path on an attached persistent disk, if not using object storage |
| `PUBLIC_SIGNUP` | `1` by default; `0` disables public registration |
| `RUN_MIGRATIONS` | `1` by default for single-instance startup; use `0` with a single release migration job |
| `WEB_CONCURRENCY` | Gunicorn workers (default 3); tune to your Render memory/CPU budget |
| `ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Optional temporary one-time bootstrap only |
| `SITE_NAME`, `SUPPORT_EMAIL`, `TIME_ZONE` | Branding and academy timezone (default Africa/Harare) |

For an optional native-Python service, `bash build.sh` installs dependencies and collects static assets only. Run `sh entrypoint.sh` as the start command; for multiple replicas arrange migrations in a single release job. Native services should use a suitable `MEDIA_ROOT` or a private bucket just like Docker.

## Email and uploads

Verify your Resend domain and DNS records before using real student recipients. Test both HTML and plain-text messages. New staff-created students receive a password-set link, not a password; accounts with unusable passwords need an administrator to resend an invitation if their initial link expires (Django's ordinary reset form deliberately excludes unusable-password accounts).

Lesson downloads check enrollment and publication, or module ownership/administrator status. Keep buckets private and do not configure a public media CDN. Changing `MEDIA_ROOT` or bucket settings does not migrate existing uploads. Upload limits are 10 MB for lessons, 12 MB per spreadsheet, 5 MB per picture and 25 MB combined for exam imports. Validate your Render proxy and worker timeout against real workloads.

Emails are best-effort post-commit actions; failures are logged and do not undo accounts or grading. Use the admin resend action for invitations. Add a durable job queue/outbox if guaranteed retry is a requirement.

## References

- [Render Django deployment](https://render.com/docs/deploy-django)
- [Render persistent disks](https://render.com/docs/disks)
- [Render Blueprint reference](https://render.com/docs/blueprint-spec)
