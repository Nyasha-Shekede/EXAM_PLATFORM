# Deploying the academy to Vercel

This is **one Django monolith**, not a separate front end and API. Vercel’s native Django integration detects `manage.py` and the existing `WSGI_APPLICATION`, deploys a Python function, runs `collectstatic`, and serves static files from its content delivery network. Vercel is stateless: it does **not** host the persistent SQL database or private training files. You must provision those separately.

## Before deployment

1. Provision a managed PostgreSQL database and a **private** S3-compatible bucket (AWS S3 or compatible object storage with S3 credentials and an endpoint). Give the application account read/write access. Keep public bucket ACLs and public bucket policies disabled. Plan separate backups for database and bucket. The database and bucket should be in a region near Vercel's serverless function.
2. Create a Resend account, verify a sending domain (including its required DNS records), and create an API key. Set `DEFAULT_FROM_EMAIL` to a verified sender on that domain. Resend test domains cannot deliver to arbitrary students.
3. Import the repository into Vercel with the project root set to this directory. Select the **Django** framework preset (or allow automatic detection) and set a supported Python version in the Vercel project settings if prompted. No custom function rewrite or static build command is needed. **Do not run migrations at build time**: every deployment can build multiple times. [Vercel’s Django guide](https://vercel.com/docs/frameworks/backend/django) documents automatic WSGI detection and static asset collection.
4. Configure project environment variables for Production (and separately for Preview if previews should use independent test data):

| Variable | Required value |
|---|---|
| `DATABASE_URL` | PostgreSQL URI with SSL required where supported, e.g. `postgresql://USER:PASSWORD@HOST/DB?sslmode=require` |
| `SECRET_KEY` | Long, random Django signing secret; keep stable across deployments |
| `DEBUG` | `0` |
| `ALLOWED_HOSTS` | Comma-separated custom hostnames; Vercel automatically supplies the current `VERCEL_URL` hostname |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated full HTTPS origins for your custom hostname(s); current Vercel preview origin is added automatically |
| `RESEND_API_KEY` | Resend API key |
| `DEFAULT_FROM_EMAIL` | Verified sender, e.g. `Africa Drone Kings <training@yourdomain.example>` |
| `AWS_STORAGE_BUCKET_NAME` | Private S3-compatible bucket name |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | Bucket credentials with least-privilege access |
| `AWS_S3_ENDPOINT_URL` | For non-AWS S3-compatible storage only |
| `AWS_S3_REGION_NAME` | Storage region if needed by your provider |
| `SITE_NAME`, `SUPPORT_EMAIL` | Optional branding/contact |
| `PUBLIC_SIGNUP` | `1` (default), or `0` to disable public student registration |

Vercel sets `VERCEL` and `VERCEL_URL` automatically. The app fails fast on Vercel when the database, bucket, signing key or Resend key is missing. Do not paste secrets into code, commits, a patch, or a public screenshot. **The source archive already contains a tracked `.env`; audit its history and rotate any real credentials there before deployment.** `.gitignore` only protects future untracked files; it cannot untrack a file already committed. Remove/rotate it safely in your own repository without sharing its contents in a patch.

5. From a trusted machine/CI job with the *production* `DATABASE_URL`, install dependencies and run `python manage.py migrate --noinput`, then `python manage.py createsuperuser`. Use the same stable `SECRET_KEY` as production. Do this on every schema-changing release, before serving traffic. Do not run migrations from a request handler. If importing data from an existing SQLite/PostgreSQL installation, plan a separate backup and migration; new production databases start empty.
6. Deploy; open `/signup/`, `/modules/`, `/dashboard/`, and `/admin/`. Verify that instructor emails, signup emails and attempt notices are delivered, that student attachment links require enrollment, and that `/static/css/app.css` loads. Test with `DEBUG=0` and HTTPS. Set up logging and monitor Resend failures, Postgres pool limits, and bucket costs.

## Operational limits / when to choose another host

- A course enrollment does **not** grant exam access automatically: instructors still assign exams explicitly, to avoid exposing restricted tests. All students may self-enroll in active training modules; only published lessons are visible to enrollees.
- Direct uploads go through the serverless function. Lesson files are capped at 4 MB on Vercel; spreadsheet/image imports have existing higher application limits and may exceed Vercel's request body or execution limits. For large imports, use the Docker/long-lived-host deployment or implement presigned direct-to-bucket uploads.
- Sending emails is synchronous on successful database commit (not a durable queue). Failed sends are logged and do not undo an account/exam transaction; retry manually or add a job queue if guaranteed delivery is required. The app never emails raw passwords: instructor-created users receive a short-lived password-set link; self-registered users select their own password.
- Public signup needs anti-abuse controls (rate limiting/CAPTCHA and optional email verification) before a high-traffic launch. This patch does not implement verified-email ownership or guaranteed delivery. The admin remains Django admin, styled to match the app; it is not a complete replacement for the admin forms.
- Keep the serverless function and database in nearby regions, set up health checks/backups, and validate Vercel plan limits (body size, function duration, deployment bundle size) before relying on high-volume exam sessions. Docker on a persistent host is a simpler choice if uploads/imports are central to your workflow.
