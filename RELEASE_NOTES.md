# Render maintenance review (unversioned)

See `docs/CODE_REVIEW.md` and `docs/TEST_REPORT.md` for the current fixes and executed checks. This maintenance patch preserves the existing database schema, removes tracked environment/serverless artifacts, hardens bootstrap/attempts/storage and refreshes Render documentation. The entries below describe historical releases, not current test coverage or import-column counts.

# 1.0.0-rc2 — 2026-09-27

Question importing is now a one-upload workflow:

- reduced the default sheet from 19 columns to 10 plain-language columns;
- removed instructor-managed IDs, question type, marks, difficulty and status;
- infers single/multiple choice from `A` versus `A,C`;
- generates IDs and applies 1 mark, medium difficulty and draft status automatically;
- allows pictures to be selected directly with the spreadsheet—no ZIP required;
- validates everything atomically and shows row-specific errors without a separate validation upload;
- added a blank template, filled example, matching sample picture and 7 focused importer tests.

# 1.0.0-rc1 — 2026-09-27

First release candidate of the single-academy drone ground-school examination and marking system. Includes structured question/image import, candidate delivery and recovery, exact-match marking, reports/PDFs, protected media, audit/result integrity controls, Docker packaging, documentation and tests.

Production release remains conditional on academy content/rule approval, infrastructure acceptance, PostgreSQL concurrency/load testing, browser/device and accessibility acceptance, backup restoration, and security review described in `docs/OPERATIONS.md`.
