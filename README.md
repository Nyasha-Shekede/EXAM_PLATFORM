# Drone Academy Examination System

A focused, single-academy web application for creating, delivering, marking and auditing drone ground-school examinations. It has **no payments, subscriptions, packages, marketplace, self-service registration, advertising or multi-tenant SaaS machinery**.

## What is included

- reusable module/category question bank;
- single-choice and multiple-choice questions;
- question images with required alternative text and SHA-256 content hashes;
- one-step ten-column XLSX/CSV question import with optional pictures selected directly;
- candidate accounts and explicit exam assignments;
- scheduled exams, attempt limits, accommodations and a configurable pass mark;
- cryptographically secure question/option shuffling;
- server-authoritative deadline, per-answer autosave, resume after disconnection and review flags;
- exact-match automatic marking (no partial credit);
- results by category, optional answer review and PDF result slips;
- attempt snapshots, HMAC result-verification codes and a hash-linked application audit trail;
- responsive candidate UI and built-in Django instructor administration;
- Docker/PostgreSQL production packaging and 20 automated tests.

## Quick evaluation (Docker)

```bash
make up
```
*(Or without make: `docker compose up -d --build`)*

This starts PostgreSQL and the application container, automatically runs migrations, and seeds the demonstration accounts.

Open <http://127.0.0.1:8000/>.

- Instructor: `admin` / `ChangeMe-Admin-2026`
- Candidate: `DEMO001` / `ChangeMe-Candidate-2026`

These are demonstration credentials only. Change or delete them before production deployment.

## Production outline

```bash
make up
make superuser                       # create your production administrator
```

The Compose service binds only to `127.0.0.1:8000`. Put an HTTPS reverse proxy (Nginx or Caddy) in front of it. Read [Deployment and operations](docs/OPERATIONS.md) before going live.

## Instructor workflow

1. Create candidate users in **Administration → Users**.
2. Open **Import**, download the simple template, fill one row per question, and upload it once. Select any referenced pictures in the same form; no ZIP or second validation upload is required.
3. Review/publish questions in **Administration → Questions**.
4. Create a draft exam, ensure the published pool is large enough, then publish it.
5. Assign named candidates and any individual extra time.
6. Candidates take the exam. Results and audit events are read-only in administration.

## Documentation

- [Reference-system analysis and scope](docs/REFERENCE_ANALYSIS.md)
- [System architecture and data model](docs/ARCHITECTURE.md)
- [Instructor and candidate guide](docs/USER_GUIDE.md)
- [Deployment, security and backup runbook](docs/OPERATIONS.md)
- [Test report](docs/TEST_REPORT.md)
- Simple ten-column import template: sign in as staff and visit `/staff/import/template.xlsx`

## Important boundary

This is a tested release candidate, not a declaration of regulatory approval. The academy must have its accountable instructor and applicable aviation authority approve the syllabi, questions, pass rules, result wording, retention period and operating procedure. The supplied reference files do not prove that 75% is universally mandated by CAAZ or SACAA, so the threshold is configurable.
