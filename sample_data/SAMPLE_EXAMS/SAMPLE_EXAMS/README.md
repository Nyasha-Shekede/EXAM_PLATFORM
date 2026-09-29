# SAMPLE EXAMS — instructor-reviewed practice bank

**Six CSV files × 100 questions = 600 draft practice questions.** The package also contains **30 original PNG diagrams** (five per module). Each diagram is used by two related questions: 10 image-backed questions per module and 60 image-backed questions overall.

**Do not use these questions as an approved, regulator-recognized examination without independent technical and legal review.** They are newly authored practice examples, not copied Drone-X questions, and have not been approved by the Civil Aviation Authority of Zimbabwe (CAAZ), South African Civil Aviation Authority (SACAA), or any other regulator. Aviation rules and drone operating approvals vary by country, aircraft, operation, and date. There is deliberately **no claim that a 75% pass mark or any depicted operating limit is legally required**. Numbers on diagrams are explicitly illustrative, not real limits.

## Package contents

| File | Module | Questions | Single correct | Two correct | Three correct | Categories | Linked diagrams |
|---|---|---:|---:|---:|---:|---:|---:|
| `01_AIR_LAW.csv` | Air Law | 100 | 50 | 24 | 26 | 5 | 5 |
| `02_METEOROLOGY.csv` | Meteorology | 100 | 50 | 22 | 28 | 5 | 5 |
| `03_FLIGHT_PRINCIPLES.csv` | Principles of Flight | 100 | 50 | 22 | 28 | 5 | 5 |
| `04_NAVIGATION_BVLOS.csv` | Navigation and BVLOS | 100 | 50 | 22 | 28 | 5 | 5 |
| `05_UAS_SYSTEMS.csv` | UAS Systems | 100 | 50 | 22 | 28 | 5 | 5 |
| `06_HUMAN_FACTORS_SAFETY.csv` | Human Factors and Safety | 100 | 50 | 22 | 28 | 5 | 5 |

The modules cover **Air Law**, **Meteorology**, **Principles of Flight**, **Navigation and BVLOS (beyond visual line of sight)**, **UAS (unmanned aircraft systems) Systems**, and **Human Factors and Safety**. `manifest.json` records every module's actual categories and picture filenames.

## Import into EXAM_PLATFORM

The academy's simple importer does **not** accept this ZIP directly. Unzip it first.

1. Sign into EXAM_PLATFORM with a staff account; open **Import** (`/staff/import/`).
2. Select **one** module's `.csv` file as the question spreadsheet.
3. In the **Question pictures** input, select that module's **five** PNG filenames listed under `images/` in `manifest.json`. Select all five in the same upload. Do not select the full folder and do not rename the images.
4. Click **Import questions** once. The UI imports 100 **drafts** or reports row-specific errors; it does not silently import a partial file.
5. Review each draft, verify the answer key, diagrams and alt text, correct local terminology/legal rules and publish only approved items. Then create/assign an exam separately.
6. Repeat for the next CSV and its five images.

**How single/multiple answers work:** the ten-column CSV uses `Correct Answer` as a letter (`B`), two letters (`A,C`) or three letters (`A,B,D`). The platform automatically infers question type and marks multiple-answer items **only on an exact match**. All questions enter with 1 mark, medium difficulty and draft status; generated codes are assigned by the platform.

**Image handling:** images are 1600 × 950 px PNG diagrams. `Image` contains the exact basename under `images/`; `Image Description` gives textual access to the scenario data without naming the correct choice. The diagrams illustrate sample workflows, vectors, schematic routes, mock weather observations and mock telemetry. They are **not** navigational charts, approved airspace maps, aircraft limits, actual weather forecasts or real operational approvals. A CSV referencing a picture without its selected file will be rejected safely.

**CSV encoding:** UTF-8 with byte-order mark (UTF-8-SIG) for compatibility with common spreadsheet programs. The first row is the simple importer's ten-column header. A multiple-correct answer such as `A,C` is quoted by the CSV writer and is one field, not two.

## Authorship and limitations

Each module has 45 distinct text scenarios explored in two ways—one best immediate response and one multi-select preparation/mitigation item—plus five diagram scenarios with two individually authored questions each. Thus each module has 100 *unique question stems*, but some items deliberately share a scenario. For high-stakes exams, an instructor should avoid placing both variants of the same scenario in a single sitting (the release-1 platform does not enforce scenario de-duplication); have a qualified subject expert review every distractor and answer; and replace these practice cases with locally approved curriculum items where required.

Items focus on broadly applicable aeronautical concepts and conservative operational decision-making. I deliberately avoided asserting specific CAAZ/SACAA altitude limits, separation distances, licensing privileges or compulsory pass marks because no current authoritative local regulations or academy approval manual were provided. Terms such as "approved" refer to the academy's own documented permissions/procedures, which must be checked for each real operation.

### Background reading (not a substitute for local rules)

- FAA, [Remote Pilot – Small Unmanned Aircraft Systems Study Guide](https://www.faa.gov/sites/faa.gov/files/uas/resources/policy_library/remote_pilot_study_guide.pdf) — broad knowledge-area map: airspace, weather, performance, decision-making and maintenance (US context; original 2016 guide; check for updates).
- FAA, [Aviation Weather Handbook landing page](https://www.faa.gov/regulationspolicies/handbooksmanuals/aviation/faa-h-8083-28b-aviation-weather-handbook) — meteorology background (US context).
- FAA, [Pilot's Handbook of Aeronautical Knowledge, Principles of Flight](https://www.faa.gov/regulationspolicies/handbooksmanuals/aviation/phak/chapter-4-principles-flight) — aerodynamics background (primarily crewed-aircraft context; adapt carefully to rotorcraft).

The three FAA URLs returned HTTP 200 when checked on 2026-09-27. These are **reading references**, not item-by-item citations or proof of any CAAZ/SACAA requirement. Apply current national regulations and the academy's approved training manual before operational use.

## Verification performed

- Counted exactly six CSVs and 100 data rows per CSV (600 total); all 600 stems unique.
- Checked four non-empty, distinct options on every row; correct-answer letters match existing options and include 1–3 distinct answers.
- Checked all 60 picture references against 30 present, valid PNGs, with non-empty descriptions.
- Shuffled displayed answers with a fixed seed to avoid a constant letter pattern.
- Imported all 600 questions, with their images, through the **real** EXAM_PLATFORM importer into a temporary database: 100 drafts per module, no import errors.
- Created a 20-question Meteorology exam from imported items and submitted correct answers through the platform's scoring service: **100.00% and PASS**.
- Visually inspected representative generated diagrams; all diagrams are synthetic and credited within the package.

`manifest.json` includes category coverage; `SHA256SUMS.txt` supplies per-file integrity checks. The temporary test database and any credentials are **not** in this ZIP. This verification checks formatting and code compatibility, not aviation/legal correctness or psychometric validity.
