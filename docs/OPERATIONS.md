# Deployment, security and operations runbook

## Production prerequisites

- Linux host with Docker Engine/Compose;
- an academy-controlled DNS name;
- reverse proxy providing TLS 1.2+ (Caddy, Nginx or managed equivalent);
- SMTP is optional and not configured in release 1;
- encrypted backup destination separate from the host;
- named application owner, question-bank owner and incident contact.

## First deployment

1. Copy `.env.example` to `.env` and replace **every** placeholder.
2. Generate the secret with `python -c "import secrets; print(secrets.token_urlsafe(64))"`.
3. Set exact host/origin values; do not use `*`.
4. `chmod 600 .env`.
5. Run `docker compose build && docker compose up -d`.
6. Create the first admin: `docker compose exec web python manage.py createsuperuser`.
7. Verify: `docker compose exec web python manage.py check --deploy`.
8. Configure the reverse proxy to `127.0.0.1:8000`, preserve `Host`, and send `X-Forwarded-Proto: https`.
9. Test candidate and staff workflows using non-production sample data.
10. Delete sample accounts/data and obtain the academy's acceptance sign-off.

Do not run `seed_demo` in production. Do not expose PostgreSQL or port 8000 directly to the internet.

## Release procedure

1. Back up database and media.
2. Review migrations: `python manage.py showmigrations`.
3. Build an immutable image tagged with a version/commit.
4. In staging: migrate, run `python manage.py check --deploy`, execute tests and complete a timed exam smoke test.
5. Deploy during a no-exam window.
6. Run migrations once, then roll application containers.
7. Verify sign-in, image display, autosave, submission, PDF and audit-chain command.
8. Retain previous image and tested rollback instructions.

Do not perform schema releases during live examinations without a rehearsed zero-downtime plan.

## Backup and restore

Back up **both** PostgreSQL and the media volume; a database-only backup loses diagrams.

Example database backup:

```bash
docker compose exec -T db pg_dump -Fc -U "$POSTGRES_USER" "$POSTGRES_DB" > exam-$(date +%F-%H%M).dump
```

Example media backup:

```bash
docker run --rm -v drone_exam_media_data:/data:ro -v "$PWD/backups":/backup \
  alpine tar czf /backup/media-$(date +%F-%H%M).tgz -C /data .
```

Encrypt, checksum, transfer off-host and enforce retention. Quarterly, restore into an isolated environment, run migrations/checks, run `verify_audit_chain`, compare record/media counts and open representative results/images. A backup that has never been restored is unverified.

## Monitoring

Alert on:

- HTTP 5xx rate and latency;
- failed sign-ins and unexpected staff-account changes;
- database/volume capacity;
- backup age/failure;
- container restarts;
- clock synchronization failure;
- audit-chain verification failure;
- elevated autosave conflicts near exam deadlines.

Use NTP/chrony on every node because deadlines and audit timestamps depend on accurate time.

## Security operations

- Require unique staff accounts and long passwords; put the admin route behind VPN/allow-list where practical.
- Add multi-factor authentication before high-stakes use (not included in release 1).
- Apply OS/container/dependency patches on a defined cadence.
- Scan uploaded files with the organization's malware scanner before production use.
- Review staff membership monthly and immediately on role departure.
- Never send passwords in clear text email; use a secure handover or implement expiring activation links.
- Treat downloaded scorecards as personal data.
- Set a documented retention/deletion policy for candidates, responses, images, exports and logs.
- Keep `SECRET_KEY` stable and protected: changing it changes future verification codes and invalidates sessions; compromise weakens HMAC assurance.

## Incident response

1. Preserve logs/database/media snapshots and record exact UTC/local times.
2. Stop new exam starts if marking, timing or data integrity may be affected.
3. Do not edit submitted attempts directly.
4. Determine affected exam versions/attempt IDs and verify audit links/backups.
5. Have an authorized academic officer decide void/retest/retain; software flags do not make misconduct decisions.
6. Notify affected parties/regulators according to applicable law and academy policy.
7. Fix, test, document and obtain authorization before reopening.

## Go-live acceptance checklist

- [ ] Responsible instructor approved question text, correct answers and images.
- [ ] Authority/manual-specific pass rule and time limits documented.
- [ ] Candidate identity/account process approved.
- [ ] Staff permissions reviewed.
- [ ] HTTPS, secure headers and host/origin settings tested.
- [ ] PostgreSQL and media restore test passed.
- [ ] System clock monitoring enabled.
- [ ] Browser/device acceptance tests completed.
- [ ] Accessibility review completed with representative images.
- [ ] Load test reflects expected simultaneous candidates.
- [ ] Incident, outage and late-submission procedures approved.
- [ ] Privacy notice, retention schedule and result-release policy approved.
