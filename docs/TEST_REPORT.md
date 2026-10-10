# Verification and test report

**Execution date:** 2026-09-27 UTC  
**Runtime:** Python 3.13 / Django 5.2  
**Command:** `python manage.py test exams --verbosity=2`  
**Database:** clean ephemeral SQLite test database (production packaging uses PostgreSQL)

## Executed result

- 30 tests discovered
- 30 passed
- 0 failed
- Django system check: 0 issues
- elapsed test time: 16.422 seconds

## Coverage by behaviour

| Area | Executed checks |
|---|---|
| Question rules | Rejects a multiple-choice item with fewer than two correct options. |
| Attempt creation | Creates exact question/option snapshots; active page does not contain correctness fields/labels. |
| Scoring | Full correct answer passes; incomplete multi-select receives zero under exact-match policy. |
| Timing | Expired attempt rejects saves and transitions to `EXPIRED`. |
| Recovery | Repeated start returns the same open attempt, preserving order/state. |
| Limits/access | Maximum attempts enforced; unassigned candidate blocked; candidate cannot open another candidate's attempt. |
| Historical integrity | Editing a source question does not alter an existing attempt snapshot. |
| Audit | Start and submit events link; verification command logic returns valid. |
| Web workflow | Dashboard, begin redirect, asynchronous answer save, email login, PDF generation and review policy. |
| Imports | Simple ten-column sheet, automatic type/defaults/IDs, direct pictures without ZIP, one-step staff form, atomic invalid-row rejection, plus retained legacy-format safety checks. |

## Defect found and fixed during testing

The first pass found three substantive issues:

1. development/test static files incorrectly required a production manifest;
2. an expiry transition was rolled back because a validation exception was raised inside the same transaction;
3. one multi-choice test fixture sampled from a mixed random pool instead of isolating its target item.

I changed development storage selection, committed expiry before returning the closed-attempt error, corrected the fixture and reran the entire suite. All tests then passed; the suite now contains 30 checks, including seven focused checks for the simplified importer and direct-picture form path.

## HTTP workflow smoke test

I also ran the development server and exercised a real HTTP session with cookies and CSRF protection: login → dashboard → start → three shuffled questions → answer saves → confirmation → submission → 100.00% pass → PDF download (2,737 bytes) → review. Seven rendered HTML/PDF artifacts are in `docs/http-smoke/`. Full Chromium rendering was attempted but the execution container lacks required shared libraries and does not grant package-manager elevation; this is reported rather than misrepresented as a browser pass.

## Additional executed checks

The build process generated and applied migrations `0001` and `0002`; `python manage.py check` reported no issues. Production static collection and package/archive checks are recorded during final packaging.

## Security and build checks

- `bandit -r config exams -x exams/tests.py`: 0 findings.
- `pip-audit -r requirements.txt`: no known vulnerabilities after upgrading Django to 5.2.17 and Pillow to 12.3.0.
- Python bytecode compilation: passed.
- Production `collectstatic`: 129 files copied, 387 post-processed; manifest created.
- `manage.py check --deploy` with the hardened production profile: 0 issues.
- Migration drift check: no changes detected.
- Compose YAML parsed successfully. Docker itself was unavailable, so the image was not built in this environment.

## What this does not establish

The automated suite is meaningful but not a complete production qualification. It does not include:

- PostgreSQL concurrency/load tests under the academy's expected simultaneous-start spike;
- penetration testing, dependency/container vulnerability scanning or malware scanning;
- independent accessibility audit;
- all target browser/device combinations;
- reverse-proxy/TLS/backup restoration in the academy's infrastructure;
- regulator or accountable-manager validation of content/scoring;
- disaster/outage exercises.

These are explicit go-live gates in `OPERATIONS.md`, not claims silently implied by passing unit tests.
