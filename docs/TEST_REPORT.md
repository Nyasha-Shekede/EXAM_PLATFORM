# Executed verification report

**Review date:** 2026-10-10 UTC
**Runtime:** Python 3.13 / Django 5.2.17
**Test database:** ephemeral SQLite (no live Render database used)

## Baseline

`python manage.py test --verbosity=1` on the unchanged downloaded `main` source discovered 50 tests: **49 passed, 1 failed**. The failing test was staff access to a student question page (expected 200; received 404). Other production hazards were found by source inspection and addressed with regression tests, not by claiming the old suite covered them.

## Reviewed source

`python manage.py test --verbosity=1`: **76 discovered, 76 passed, 0 failed** in **37.907 seconds**. The added checks cover administrator bootstrap preservation, protected staff previews, draft publication/pool integrity, small-target category sampling, module-aligned imports, retained results, deadline persistence, account validation, absolute email links, safe forms, readiness and CSV formula neutralization. Existing exam/import/enrollment/Resend-mock tests continue to pass.

| Check | Executed result |
|---|---|
| `manage.py check` | No issues |
| `makemigrations --check --dry-run` | No changes detected |
| `manage.py check --deploy` with placeholder Render production settings | Exit 0; one warning: HSTS preload intentionally opt-in |
| Production `collectstatic --noinput` | 130 files copied, 388 post-processed; manifest created |
| `python -m compileall -q config exams` | Passed |
| Render/Compose YAML parsing | Passed (syntax only, not service provisioning) |
| `sh -n entrypoint.sh`, `bash -n build.sh` | Passed |
| Entrypoint custom-command bypass | Passed; no migrations/bootstrap invoked |
| Render unsafe configuration import checks | Rejected debug mode, SQLite, missing durable-media config, wildcard hostname, missing Resend key and insecure email origin |
| README logo path | Existing `static/img/adk-logo.png` verified |

The production checks used invented placeholder credentials solely for configuration validation; no provider connection or mail send was represented as successful. The Resend tests mock HTTP. Database health tests use the SQLite test connection and mocked failures.

## Patch verification

The delivered update is checked with `git apply --check` against a clean export of the downloaded baseline and applied to a fresh tree. Sensitive deleted files use forward-only binary deletion blocks (zero-length result) instead of including their former values. No schema migration is required by these changes.

## Not executed / release gates

- Live Render deployment, PostgreSQL concurrent-worker/load behavior or provider storage connectivity.
- Docker image/container execution (Docker was unavailable in this environment).
- Real Resend delivery, sending-domain DNS checks or durable retry behavior.
- Current dependency/container vulnerability scan, penetration test, browser automation or independent accessibility audit.
- Backup restore, secrets/history remediation or production data migration.
- Aviation-regulator/accountable-instructor qualification of content or scoring.

The older generated HTTP captures and stale checksum manifest were removed rather than treated as proof that the current app is browser-verified.
