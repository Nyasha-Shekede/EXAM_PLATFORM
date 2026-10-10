<p align="center">
  <img src="static/img/adk-logo.png" alt="Africa Drone Kings" width="280">
</p>

# Africa Drone Kings Academy

A single-academy **Django learning and examination platform**, deployed on **Render**. Instructors create modules and publish lessons/resources; students register, enroll in modules, and take explicitly assigned examinations. The app includes no payments or multi-tenant marketplace features.

## What it does

- Instructor-authored modules, draft/published lessons and private attachments (up to 10 MB).
- Student registration, email invitations, password setup/recovery, and username/email sign-in.
- CSV/XLSX question imports with optional images and required alternative text.
- Explicit exam assignment, scheduled availability, accommodations and attempt limits.
- Balanced category sampling, randomized questions/options and immutable question snapshots.
- Server-side deadlines, autosave, resume, read-only instructor previews and review flags.
- Exact-match scoring, category results, optional answer review, PDF slips and CSV exports.
- Resend HTML/plain-text email notifications and a hash-linked application audit trail.
- Docker packaging, managed PostgreSQL, private S3-compatible storage or a Render disk.

## Deployment on Render

Read **[Render deployment and upgrades](docs/RENDER_DEPLOYMENT.md)** before deploying. The repository contains **no environment files or real credentials**. Configure production secrets in Render's Environment dashboard or a secret manager, not in commits or Docker images.

For an **existing deployment**, preserve your live `SECRET_KEY` (unless it was exposed), database, and uploaded files. This review adds fail-closed Render settings: supply a private bucket or a persistent-disk `MEDIA_ROOT`, a PostgreSQL `DATABASE_URL`, a Resend API key, and an explicit hostname (Render's own hostname is added automatically). Bootstrap admin passwords are no longer reset on restart.

> Removing committed secrets does not revoke them or remove them from Git history. Rotate anything exposed, then coordinate a history cleanup if required. See [security operations](docs/OPERATIONS.md).

## Local development (Python)

```bash
python -m venv .venv
# Linux/macOS:
. .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Local defaults use SQLite, local private media and console email. **No `.env` is loaded automatically by Django.** Export variables in your shell if needed. Development defaults are not suitable for a public deployment.

## Local Docker evaluation

Create an **ignored** `.env` privately. Replace every placeholder below with a newly generated value; the same database and MinIO passwords must match across their paired settings:

```dotenv
DEBUG=1
SECRET_KEY=<new-long-random-development-key>
POSTGRES_DB=drone_exams
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<new-database-password>
DATABASE_URL=postgresql://postgres:<url-encoded-database-password>@db:5432/drone_exams
MINIO_ROOT_USER=<new-storage-user>
MINIO_ROOT_PASSWORD=<new-storage-password>
AWS_STORAGE_BUCKET_NAME=exam-platform
AWS_ACCESS_KEY_ID=<same-storage-user>
AWS_SECRET_ACCESS_KEY=<same-storage-password>
AWS_S3_ENDPOINT_URL=http://minio:9000
AWS_S3_REGION_NAME=us-east-1
PUBLIC_SIGNUP=1
PUBLIC_BASE_URL=http://localhost:8000
```

```bash
docker compose up -d --build
docker compose exec web python manage.py createsuperuser
```

Open <http://localhost:8000/>. There are **no default login credentials** and no automatic demo seeding. Compose initializes a private MinIO bucket and waits for it before starting the app. The web/database/storage containers use local volumes; exposed ports bind only to loopback. Database credentials used in a URI must be URL-encoded. Never run `docker compose down -v` if you need to retain local data.

## Daily workflow

1. Instructors create modules from **Modules → Create module**, add lessons, and publish them when ready.
2. Students register at `/signup/`, enroll in active modules, and view published lessons/resources.
3. Instructors create students with email invitations or let them self-register. Only administrators create/promote instructors.
4. Import questions with **Import**; standalone imports remain **draft**. Review and publish them deliberately.
5. **Create Examination** imports one module per spreadsheet and publishes only those newly imported questions. Other drafts remain unpublished.
6. Assign exams explicitly. Course enrollment does **not** grant exam access.
7. Students start/resume, save answers, submit and view results. Staff previews cannot submit or alter student answers.
8. Exams with attempts cannot be deleted; close them to preserve results.

## Verification

```bash
python manage.py test
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py verify_audit_chain
```

See [test results and limitations](docs/TEST_REPORT.md) and [source review](docs/CODE_REVIEW.md). `/health/` returns a small database readiness response; no secrets or student data are included.

## Documentation

- [Render deployment and upgrade checklist](docs/RENDER_DEPLOYMENT.md)
- [Operations, secrets and backups](docs/OPERATIONS.md)
- [Instructor and student guide](docs/USER_GUIDE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Code review and residual risks](docs/CODE_REVIEW.md)
- [Executed verification report](docs/TEST_REPORT.md)
- [Original reference analysis (historical scope)](docs/REFERENCE_ANALYSIS.md)
- Question template: sign in as staff and open `/staff/import/template.xlsx`.

## Important boundaries

Passing tests is not regulatory approval or a full production qualification. The academy's accountable instructor and applicable aviation authority must approve the content, pass rules, retention and operating procedure. Public signup does not verify email ownership or include anti-abuse rate limits; emails are synchronous best-effort delivery, not a durable retry queue. PostgreSQL concurrency, live Render/Resend delivery, backups and browser accessibility require deployment-specific checks.
