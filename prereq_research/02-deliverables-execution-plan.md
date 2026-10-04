# Rhombus AI Take-Home: Deliverables Execution Plan

> This is the build plan for every deliverable: what goes in the repo, how each part is designed, the exact protocol for every drift case, the templates for reports and README, the dashboard, the demo video, the timeline and the final QA gate.
> **Read first:** [`01-assessment-breakdown.md`](./01-assessment-breakdown.md). Requirement IDs (**R-xx**) refer to its §2 and §10.
> **Principle:** the brief rewards *judgement, test quality and clear reporting*, and says "quality over quantity". Every design choice below either produces evidence a reviewer can check or makes a trade-off explicit.

---

## Table of contents

1. [Strategy in one page](#1-strategy-in-one-page)
2. [Final repository structure](#2-final-repository-structure)
3. [Tech stack, environment and secrets](#3-tech-stack-environment-and-secrets)
4. [Datasets: baseline and drift files](#4-datasets-baseline-and-drift-files)
5. [Building the pipeline with AI only](#5-building-the-pipeline-with-ai-only)
6. [`/data-validation/` design](#6-data-validation-design)
7. [Drift execution protocol and classification](#7-drift-execution-protocol-and-classification)
8. [`/ui-tests/` design](#8-ui-tests-design)
9. [`/api-tests/` design](#9-api-tests-design)
10. [Timeline and run budget](#10-timeline-and-run-budget)
11. [Email template for blockers](#11-email-template-for-blockers)
12. [`/observations/` template and evidence conventions](#12-observations-template-and-evidence-conventions)
13. [`README.md` template](#13-readmemd-template)
14. [Bonus: observability dashboard](#14-bonus-observability-dashboard)
15. [Demo video script](#15-demo-video-script)
16. [Final QA gate and submission](#16-final-qa-gate-and-submission)

---

## 1. Strategy in one page

- **One small, seeded, fully-counted dataset.** Every defect is injected deliberately by a script, and the script writes a manifest of exact counts. Row-count and cleaning-rule checks then become exact assertions instead of guesses.
- **A written cleaning contract.** We tell the AI builder *exactly* which rules to apply (via `/pipeline`) and encode the same rules in `contract.yaml`. The validator checks the output against the **contract**, not against whatever the AI happened to build. Wherever the AI deviates, that's a finding.
- **Two validation layers.**
  1. *Oracle layer:* an independent pandas reference cleaner computes the expected output, and we compare row by row on `order_id`. This uses ground truth only a tester has.
  2. *Production layer:* schema, rule and statistical checks against a reference profile from the baseline run, with no ground truth needed. This is how a real customer would catch drift, and showing both is an observability talking point.
- **Change one variable per case.** Reset the input and the pipeline to baseline between cases, and prove the reset with a pipeline-definition snapshot (API) plus a green run.
- **Cross-system assertions.** The UI tests click in Rhombus and then assert the object actually landed in GCS. The API tests assert on status *and* body. The validator is unit-tested itself with synthetic fixtures, so the checks are known to fire.
- **Fixed vocabulary for reporting.** Every case is classified with the same enums (outcome, GCS impact, log clarity 0–3, diagnosis, fix, schedule, severity). That makes the README table, heat map and dashboard consistent with each other.
- **Opt-in for anything that costs credits or behaves non-deterministically.** The default test runs are fast, read-only and repeatable. Full AI-build end-to-end tests are opt-in (`-m e2e`).

---

## 2. Final repository structure

```
Rhombus-AI-Test/
├── README.md                         # the 4 mandatory sections + decisions & trade-offs
├── Makefile                          # make setup | ui | api | validate CASE=.. | validate-all | dashboard
├── requirements.txt                  # pinned versions
├── pytest.ini                        # markers: e2e, slow, negative; testpaths
├── .env.example                      # every variable, no values
├── .gitignore                        # .env, .auth/, *.json keys, traces, __pycache__
├── .github/workflows/
│   ├── ci.yml                        # lint + validator unit tests + "no fixed sleeps" guard
│   └── pages.yml                     # deploy /dashboard to GitHub Pages
│
├── datasets/
│   ├── generate.py                   # seeded generator (seed=42) → baseline + all drift files + manifest
│   ├── DATA_DICTIONARY.md            # columns, types, units, defect catalogue with counts
│   ├── manifest.json                 # exact defect counts & expected output rows per file
│   ├── baseline/orders.csv
│   ├── schema/
│   │   ├── S1-drop-column.csv
│   │   ├── S2-rename-column.csv
│   │   ├── S3-change-data-type.csv
│   │   ├── S4-add-column.csv
│   │   └── S5-combined.csv
│   └── semantic/
│       ├── M1-dollars-to-cents.csv
│       ├── M2-date-mmdd-to-ddmm.csv
│       └── M3-country-iso-codes.csv  # optional
│
├── data-validation/
│   ├── validate.py                   # CLI entry point
│   ├── contract.yaml                 # schema + cleaning rules + ranges (single source of truth)
│   ├── reference_profile.json        # stats from the validated baseline output (generated)
│   ├── rhombus_qa/
│   │   ├── io_s3.py                  # fetch input by key+versionId, verify ETag == local md5
│   │   ├── io_gcs.py                 # list/select output object by run timestamp, download
│   │   ├── oracle.py                 # independent reference cleaner implementing contract.yaml
│   │   ├── checks/
│   │   │   ├── schema.py
│   │   │   ├── row_counts.py
│   │   │   ├── cleaning_rules.py
│   │   │   ├── determinism.py
│   │   │   └── semantic.py
│   │   └── report.py                 # JSON + Markdown + HTML side-by-side diff
│   ├── runs.yaml                     # registry: case → s3 versionId → gcs object(s) → run ids
│   ├── run_all.py                    # validate every entry in runs.yaml
│   └── tests/                        # unit tests proving every check fires on synthetic bad data
│
├── ui-tests/
│   ├── conftest.py                   # storage state, tracing/video on failure, env loading
│   ├── scripts/save_auth.py          # one-off headed login → .auth/state.json
│   ├── pages/                        # page objects: projects, sources, canvas, chat, output, schedule
│   ├── helpers/gcs.py                # read-only GCS assertions (qa-reader SA)
│   └── tests/
│       ├── test_00_session.py
│       ├── test_01_s3_source.py
│       ├── test_02_ai_pipeline.py
│       ├── test_03_gcs_destination.py
│       └── test_04_schedule.py
│
├── api-tests/
│   ├── ENDPOINTS.md                  # endpoints discovered from the network tab (redacted)
│   ├── client.py                     # thin requests wrapper; token from env / storage state
│   ├── schemas.py                    # pydantic models of response bodies
│   ├── scripts/har_summary.py        # HAR → unique (method, path, status) table
│   └── tests/
│       ├── test_projects.py
│       ├── test_pipeline_and_runs.py
│       ├── test_schedules.py
│       └── test_negative_auth.py
│
├── observations/
│   ├── _TEMPLATE.md
│   ├── baseline.md
│   ├── schema-drop-column.md
│   ├── schema-rename-column.md
│   ├── schema-change-data-type.md
│   ├── schema-add-column.md
│   ├── schema-combined.md
│   ├── semantic-dollars-to-cents.md
│   ├── semantic-date-mmdd-to-ddmm.md
│   ├── semantic-country-iso-codes.md # optional
│   ├── usability-log.md              # running notes → README usability paragraphs
│   └── evidence/<case-id>/...        # screenshots, logs.csv, chatbot.md, validator.json, pipeline-*.json
│
├── results/
│   ├── runs.csv                      # one row per pipeline execution (manual + scheduled)
│   └── <case-id>/<run-id>/report.json
│
├── scripts/
│   ├── upload_drift.sh               # aws s3 cp <file> s3://…/pipeline/orders.csv + record versionId
│   ├── snapshot_pipeline.py          # GET pipeline definition via API → evidence/<case>/pipeline-*.json
│   └── build_dashboard.py            # results/** → dashboard/data/dashboard.json
│
├── dashboard/
│   ├── index.html                    # single-page interactive dashboard
│   ├── app.js
│   ├── style.css
│   └── data/dashboard.json
│
└── prereq_research/                  # this folder: brief images + research + plan
```

---

## 3. Tech stack, environment and secrets

### 3.1 Choices and the reasons for them

| Area | Choice | Why (trade-off) |
|---|---|---|
| Language | **Python 3.11** everywhere | One toolchain, one `requirements.txt`, one `pytest` command for all three suites. It's also my strongest language. Trade-off: Playwright's TypeScript runner has slightly richer reporting, but pytest-playwright has tracing, video and screenshots, which covers what we need. |
| UI automation | **Playwright** via `pytest-playwright` | Auto-waiting locators and web-first `expect` make "no fixed sleeps" natural. Trace viewer works for debugging. Cypress would also be fine, but it's JS-only and weaker with multi-tab/auth flows. |
| API tests | `pytest` + `requests` + `pydantic` | Explicit status and body assertions, schema validation via typed models. |
| Validation | `pandas` + `pyyaml` + `boto3` + `google-cloud-storage` | Standard. The contract lives in YAML so it can be read without the code. |
| Dashboard | Static HTML + **Chart.js** (CDN), hosted on **GitHub Pages** | No backend. Data is a committed JSON file. Free, public URL. Lives in the same repo. |
| CI | GitHub Actions | Runs validator unit tests, lint (ruff), and a grep guard that fails on `sleep(` / `wait_for_timeout` in test code. |

### 3.2 `requirements.txt` (pin exact versions at implementation time)
```
pytest
pytest-playwright
playwright
requests
pydantic
pandas
pyyaml
boto3
google-cloud-storage
python-dotenv
ruff
```

### 3.3 `.env.example`
```dotenv
# Rhombus
RHOMBUS_BASE_URL=https://rhombusai.com          # ⚠ VERIFY actual app host after login (from network tab)
RHOMBUS_API_BASE=                                # ⚠ fill from network tab (e.g. https://api.…)
RHOMBUS_PROJECT_NAME=rhombus-qa-etl
RHOMBUS_PROJECT_ID=
RHOMBUS_SCRATCH_PROJECT_NAME=rhombus-qa-scratch
RHOMBUS_STORAGE_STATE=.auth/state.json
RHOMBUS_TOKEN=                                   # optional override; else read from storage state

# AWS (source) - your own uploader identity, NOT what Rhombus uses
AWS_PROFILE=rhombus-qa-uploader
AWS_REGION=ap-southeast-2
S3_BUCKET=rhombus-qa-source-xxxx
S3_KEY=pipeline/orders.csv

# GCP (destination)
GCS_BUCKET=rhombus-qa-dest-xxxx
GCS_OUTPUT_PREFIX=orders_clean_
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/outside/repo/qa-reader.json   # read-only SA
```

### 3.4 Security rules (non-negotiable)
- Never commit `.env`, `.auth/`, or any `*.json` key (gitignore + run `git-secrets`/`gitleaks` before pushing).
- **Redact** account IDs, emails, ARNs and keys in screenshots (blur before saving to `evidence/`).
- The Rhombus writer SA key is pasted only into Rhombus. The validator uses the separate **read-only** `qa-reader` SA.
- After submission: rotate/delete the SA keys and IAM access keys, and remove the Rhombus bucket-policy statements.

---

## 4. Datasets: baseline and drift files

### 4.1 Baseline schema: `datasets/baseline/orders.csv`

| # | Column | Type (semantic) | Format / units | Example |
|---|---|---|---|---|
| 1 | `order_id` | integer, **business key** (unique after cleaning) | 1001–1500 | `1042` |
| 2 | `customer_name` | text | free text | `Priya Sharma` |
| 3 | `email` | text (nullable) | `local@domain.tld` | `priya@example.com` |
| 4 | `country` | categorical | canonical English name | `Australia` |
| 5 | `order_date` | date | **MM/DD/YYYY** (majority) | `03/14/2026` |
| 6 | `product` | text | product name | `USB-C Hub` |
| 7 | `category` | categorical | {Electronics, Home, Books, Sports, Fashion} | `Electronics` |
| 8 | `quantity` | integer | units, 1–20 | `3` |
| 9 | `unit_price` | decimal | **US dollars**, 2 dp, 1.00–1999.99 | `49.95` |
| 10 | `status` | categorical | {pending, shipped, delivered, cancelled} | `shipped` |

Size: **500 unique orders + 25 duplicate rows = 525 rows × 10 columns ≈ 5,250 cells.** That's well under the Impute model-based limit (10k rows / 20k cells), the Text Cleanup pandas limit (100k rows), and Data Input sampling (100k rows), so none of them can distort the results. Order dates fall between **01 Jan 2026 and 30 Jun 2026**. That narrow window makes date-swap drift statistically obvious.

**Days are deliberately mixed:** about 40% of rows have day ≤ 12 (ambiguous under a swap) and about 60% have day > 12 (impossible as a month). That way M2 tests both the *silent* and the *loud* failure modes.

### 4.2 Injected defects (disjoint rows, so every count is exact)

| Class (brief wording) | Defect | Rows | Expected cleaning action (contract) |
|---|---|---|---|
| **Duplicates** | Exact duplicate rows | 15 | Remove (keep first) |
| | Near-duplicates: same `order_id`, differ only by case/whitespace in text | 10 | Become exact duplicates after normalisation → remove |
| **Missing values** | `quantity` empty | 20 | Impute median (integer) |
| | `unit_price` empty | 20 | Impute median (2 dp) |
| | `email` empty | 15 | Leave null (nullable) |
| | `country` empty | 10 | Fill `Unknown` |
| | `customer_name` empty | 5 | Fill `Unknown` |
| **Inconsistent formatting** | `country` variants: `USA`, `usa`, `U.S.`, ` united states `, `UK`, `u.k.`, `Aus`, `india ` … | 60 | Map to canonical name |
| | `customer_name` casing/whitespace (`  priya   SHARMA `) | 40 | Trim, collapse spaces, Title Case |
| | `status` casing (`Shipped`, `SHIPPED`) | 30 | Lower-case |
| | `order_date` as ISO `YYYY-MM-DD` | 20 | Parse; output ISO |
| | `email` upper-case | 15 | Lower-case |
| **Invalid entries** | `quantity` ≤ 0 | 8 | Drop row |
| | `unit_price` < 0 | 5 | Drop row |
| | `order_date` impossible (`02/30/2026`, `13/45/2026`) | 3 | Drop row |
| | `status` outside the allowed set (`unknown`, `???`) | 4 | Drop row |
| | `email` malformed (no `@`) | 8 | Set null, keep row |

**Expected output (illustrative, the generator computes the real figure):** 525 − 25 duplicates − 20 invalid rows = **480 rows**. `manifest.json` stores the true numbers for every file, and the validator reads it from there.

### 4.3 Drift files (each derived from the baseline by the generator with a single, documented transform)

| ID | File | Change | Why this specific change | Hypothesis to test |
|---|---|---|---|---|
| **S1** | `schema/S1-drop-column.csv` | Remove `country` | It's referenced by a cleaning rule (canonical mapping, fill `Unknown`), so it's a *meaningful* drop rather than a trivial one. | The node referencing `country` fails → STOP. Or the AI-generated code skips it silently → CARRY-ON with fewer columns. |
| **S2** | `schema/S2-rename-column.csv` | `customer_name` → `customer_full_name` | Used by the Title-Case/fill rules, and possibly by Remove Duplicates' column list. | Column-bound nodes fail, or the renamed column passes through un-cleaned (silent degradation). |
| **S3** | `schema/S3-change-data-type.csv` | `unit_price` numeric → string currency `"$1,249.50"` | Realistic upstream change from an export tool. Tests Convert Type / Impute (numeric-only) / Text Cleanup interactions. | Impute rejects a non-numeric target, or coercion turns every value into NaN and then imputes the median everywhere (silent corruption). |
| **S4** | `schema/S4-add-column.csv` | Insert `discount_code` (≈30% filled) **between** `product` and `category` | Placed mid-row (not appended) to expose positional assumptions. | Most likely handled (passes through). Check whether it's cleaned, dropped, or shifts other columns. |
| **S5** | `schema/S5-combined.csv` | S1 + S2 + S3 + S4 together | Required by the brief. Shows whether the errors compound and whether the chatbot can untangle several causes at once. | First-failure masking: logs show only the first error. Chatbot fixes one cause at a time. |
| **M1** | `semantic/M1-dollars-to-cents.csv` | `unit_price` × 100 as integer cents (`49.95` → `4995`) | Classic unit drift. Same column name and type (numeric). | Rhombus carries on silently. Outlier handling may cap or remove values (corruption either way). Our range and ratio checks catch it. |
| **M2** | `semantic/M2-date-mmdd-to-ddmm.csv` | `order_date` rows written as **DD/MM/YYYY** (ISO rows unchanged) | Classic locale drift. Same column and same string type. | Days > 12: parse failure → rows dropped or nulled (loud-ish). Days ≤ 12: silently wrong dates (silent). Our join and window checks catch both. |
| **M3** *(optional)* | `semantic/M3-country-iso-codes.csv` | `country` as ISO-3166 alpha-2 (`AU`, `US`, `GB`, `IN`, `NZ`) | Encoding drift inside a categorical. Tests whether the AI's mapping generalises or falls back to `Unknown`. | Mapped partially, or everything becomes `Unknown`/raw codes. Caught by our allowed-values check. |

**Generator requirements (`datasets/generate.py`):** seeded (`numpy.random.default_rng(42)`); writes all files plus `manifest.json` (`{file: {rows_in, duplicates, invalid, expected_rows_out, columns, sha256}}`); idempotent (re-running gives byte-identical files, verified in CI); prints a defect summary that's copied into `DATA_DICTIONARY.md`.

---

## 5. Building the pipeline with AI only

### 5.1 Rules for the build
1. Every node must come from chat (`/plan` → `/pipeline`). **No** palette additions and **no** double-click parameter edits.
2. Allowed manual actions (configuration, not transformation): connecting the S3 source, creating the GCS destination credentials, choosing the destination in the Data Output form if the agent can't, and creating the schedule. State each one in the README.
3. Log every prompt and the result in `observations/evidence/pipeline-build/prompt-log.md`: timestamp, mode, prompt verbatim, agent reply (summary + screenshot), nodes before/after.
4. Once the pipeline passes validation, **freeze** it: snapshot the definition through the API to `evidence/pipeline-build/pipeline-baseline.json` and never rebuild it.

### 5.2 Prompt templates

**Planning (`/plan`):**
```
/plan I have connected an Amazon S3 file "pipeline/orders.csv" (e-commerce orders: order_id, customer_name,
email, country, order_date, product, category, quantity, unit_price, status). It contains duplicates,
missing values, inconsistent formatting and invalid entries. I want a cleaning pipeline that runs on a
schedule and writes a CSV to Google Cloud Storage. Before building anything, ask me what you need to know
about the cleaning rules.
```

**Build (`/pipeline`)**: explicit rules, in order, so the contract is unambiguous:
```
/pipeline Build a cleaning pipeline for the S3 dataset orders.csv, applying these rules in this order:
1. Text normalisation: trim leading/trailing whitespace and collapse repeated spaces in customer_name, email,
   country, product, category, status.
2. customer_name → Title Case; email → lower case; status → lower case.
3. country → canonical names: {USA, US, U.S., United States → "United States"}, {UK, U.K., United Kingdom →
   "United Kingdom"}, {Aus, AU, Australia → "Australia"}, {India → "India"}, {NZ, New Zealand → "New Zealand"}.
4. order_date: parse MM/DD/YYYY or YYYY-MM-DD and output as YYYY-MM-DD.
5. Remove invalid rows: quantity <= 0, unit_price < 0, unparseable order_date, status not in
   {pending, shipped, delivered, cancelled}.
6. Set email to empty if it does not contain "@".
7. Remove duplicate rows comparing ALL columns, keep the first occurrence.
8. Missing values: quantity → median (integer), unit_price → median (2 decimals),
   country and customer_name → "Unknown"; leave email empty.
9. Ensure types: order_id integer, quantity integer, unit_price decimal(2), order_date date.
10. Sort by order_id ascending.
11. Finish with a Data Output node that writes CSV to Google Cloud Storage with base filename "orders_clean".
```

If the agent builds only part of this, follow up with focused `/pipeline` prompts ("Step 3 is missing: add the country mapping …"). Each follow-up is logged. **The number of prompts needed to reach a correct pipeline is itself a usability data point.**

### 5.3 First smoke test: does a run re-read S3? (do this before the baseline)
1. Disable the schedule. Upload a variant with **one extra valid row** to the same key.
2. Run the pipeline manually. Does the output row count go up by 1?
   - **Yes** → live read. Proceed as planned.
   - **No** → try **Refresh access** on the source and run again. If that fixes it, the drift protocol includes a refresh step, and this is **finding #1** (customers would expect scheduled ETL to pick up new files).
3. Restore the baseline file and re-enable the schedule. Record the result in `observations/baseline.md`.

---

## 6. `/data-validation/` design

### 6.1 `contract.yaml` (single source of truth for "cleaning rules were applied")
```yaml
version: 1
key: order_id
columns:                      # expected output schema, in order
  - {name: order_id,      dtype: int,    nullable: false, unique: true}
  - {name: customer_name, dtype: string, nullable: false, rules: [trimmed, single_spaced, title_case]}
  - {name: email,         dtype: string, nullable: true,  rules: [trimmed, lower_case, contains_at_or_null]}
  - {name: country,       dtype: string, nullable: false,
     allowed: [Australia, United States, United Kingdom, India, New Zealand, Unknown]}
  - {name: order_date,    dtype: date,   nullable: false, format: "%Y-%m-%d",
     min: "2026-01-01", max: "2026-06-30"}
  - {name: product,       dtype: string, nullable: false, rules: [trimmed, single_spaced]}
  - {name: category,      dtype: string, nullable: false,
     allowed: [Electronics, Home, Books, Sports, Fashion]}
  - {name: quantity,      dtype: int,    nullable: false, min: 1, max: 20}
  - {name: unit_price,    dtype: float,  nullable: false, min: 1.00, max: 1999.99, decimals: 2}
  - {name: status,        dtype: string, nullable: false,
     allowed: [pending, shipped, delivered, cancelled]}
dedupe: {subset: all, keep: first}
sort: {by: order_id, ascending: true}
imputation:
  quantity:   {method: median, round: 0}
  unit_price: {method: median, round: 2}
semantic:
  unit_price: {max_median_ratio_vs_reference: 3.0}     # cents drift → ~100×
  order_date: {max_out_of_window_fraction: 0.0, max_month_distribution_jsd: 0.10}
```

### 6.2 Checks

| Group | Check ID | What it asserts | Layer |
|---|---|---|---|
| **Schema** | `SCH-01` | Output column names == contract, in order. Reports missing, extra and renamed (fuzzy-match suggestion). | production |
| | `SCH-02` | Each column parses to its contract dtype (≥ 99.5% cast success, otherwise lists the offending values). | production |
| | `SCH-03` | Input header vs baseline input header diff (detects the drift *cause* upstream). | production |
| **Row counts** | `ROW-01` | `rows_out == manifest.expected_rows_out` (exact). | oracle |
| | `ROW-02` | Accounting: `rows_in − dupes − invalid == rows_out`, with a breakdown of where rows went. | oracle |
| | `ROW-03` | `rows_out > 0` and not header-only. | production |
| **Cleaning rules** | `CLN-01` | No duplicate rows. `order_id` unique. | production |
| | `CLN-02` | No nulls except in nullable columns. | production |
| | `CLN-03` | Text rules (trimmed, single-spaced, case). | production |
| | `CLN-04` | Allowed values for categoricals. | production |
| | `CLN-05` | Ranges (quantity, unit_price, date window). | production |
| | `CLN-06` | Imputed cells equal the contract median of the valid non-null values (±0.01). | oracle |
| | `CLN-07` | Sorted by `order_id`. | production |
| | `CLN-08` | **Row-level equality with the oracle output** (joined on `order_id`). Lists every differing cell. | oracle |
| **Determinism** | `DET-01` | Canonical SHA-256 of the output (sort by key, fixed float format, ISO dates, `""` for null) is identical across N runs of the same config. | production |
| | `DET-02` | If hashes differ: cell-level diff + side-by-side HTML (`difflib.HtmlDiff`) for the dashboard. | production |
| **Semantic** | `SEM-01` | `median(unit_price) / reference.median` within `[1/3, 3]` (cents drift → ≈100). | production |
| | `SEM-02` | Join with the baseline output: per-order price ratio ≈ constant 100 → "unit change ×100" diagnosis. | oracle |
| | `SEM-03` | `order_date` out-of-window fraction > 0, or month-distribution Jensen-Shannon distance vs reference > threshold. | production |
| | `SEM-04` | Join with the baseline: `out.month == base.day and out.day == base.month` → "day/month transposed" diagnosis, counted separately for ambiguous (≤ 12) and impossible (> 12) days. | oracle |
| | `SEM-05` | Category frequencies vs reference (catches M3 country codes → everything `Unknown`). | production |

Every check returns `{id, status: PASS|FAIL|WARN|SKIP, message, evidence}`. **Exit code:** `0` all pass, `1` any FAIL, `2` execution error (couldn't fetch, etc.).

### 6.3 How input and output are located
- **Input (S3):** `io_s3.py` downloads `s3://$S3_BUCKET/$S3_KEY?versionId=<id>` (versions come from `runs.yaml`, recorded by `scripts/upload_drift.sh`) and asserts its MD5/ETag equals the local `datasets/...` file. That proves which file the pipeline actually saw.
- **Output (GCS):** Rhombus writes `orders_clean_<ms-timestamp>.csv` to the bucket root (per the docs). `io_gcs.py` lists `orders_clean_*`, parses the timestamp, and picks the object written within that run's `[start, start+duration+60s]` window (start and duration come from the execution record). `--object` overrides this.
- **No output** for a run is a valid, recorded result: `GCS impact = NOTHING-WRITTEN`.

### 6.4 CLI
```bash
# validate one run
python data-validation/validate.py \
  --case S2 \
  --input-version <s3-version-id>  --input-local datasets/schema/S2-rename-column.csv \
  --output gs://$GCS_BUCKET/orders_clean_1759900000000.csv \
  --reference data-validation/reference_profile.json \
  --baseline-output results/baseline/<run-id>/output.csv \
  --out results/S2/<run-id>/

# determinism over 3 runs of the same configuration
python data-validation/validate.py --case baseline --determinism \
  --output gs://…/orders_clean_A.csv gs://…/orders_clean_B.csv gs://…/orders_clean_C.csv

# everything in runs.yaml (used for the final results + dashboard)
python data-validation/run_all.py      # or: make validate-all
```
Outputs per run: `report.json` (machine), `report.md` (human, pasted into observations), `output.csv` (downloaded copy), `diff.html` (if any diff).

### 6.5 Testing the validator
`data-validation/tests/` builds tiny synthetic frames and asserts each check **fails** when it should: duplicated row → `CLN-01` FAIL, ×100 prices → `SEM-01/02` FAIL, swapped dates → `SEM-04` FAIL, the baseline oracle output → all PASS. This runs in CI with no cloud access. Mention it in the README, because it shows the checks are trustworthy and don't only pass.

---

## 7. Drift execution protocol and classification

### 7.1 Per-case runbook (identical for every case)

```
PRE   1. Confirm reset: pipeline definition == pipeline-baseline.json (scripts/snapshot_pipeline.py --diff)
         and the last run on the baseline file was green + validator PASS.
      2. Note: time, credits remaining, schedule card (Active, Next run).
DRIFT 3. ≥10 min before the next trigger: scripts/upload_drift.sh <case> → records S3 versionId in runs.yaml.
      4. (Only if §5.3 found it necessary) click Refresh access, and record that you did.
OBSERVE 5. Let the SCHEDULED run fire. Do not click Run.
      6. Capture: Schedule History row, run status, failed node, warning banners, duration (screenshots).
      7. Export CSV of the execution errors → evidence/<case>/logs.csv; quote the key lines.
      8. GCS: did a new object appear? If yes, run the validator → evidence/<case>/validator-drift.json.
      9. Failure email received? Screenshot it (redacted).
DIAGNOSE 10. Ask the chatbot, in this order:
         a) "Fix in Chat" on the failed node (built-in path), verbatim reply saved;
         b) a neutral Analysis question for silent cases: "Is there anything unusual about the latest
            pipeline output compared with previous runs?" (tests whether Rhombus notices on its own);
         c) only if needed: paste the raw log under /pipeline: "This scheduled run failed with: <error>.
            Diagnose the cause and fix the pipeline."
FIX   11. Apply the fix only through /pipeline. Snapshot pipeline-after-fix.json.
      12. Manual run on the drifted file → validator → "fix worked on drift?"
      13. Regression: restore the baseline file → manual run → validator → "fix kept baseline correct?"
SCHED 14. Observe the next scheduled trigger after the incident: fired? status? still Active? Next run?
RESET 15. Revert the pipeline to baseline via /pipeline ("Revert the pipeline to exactly this definition: …"
          or undo the specific change), confirm with snapshot diff == ∅ and a green validated run.
WRITE 16. Fill observations/<case>.md from the template (§12) while it's fresh; append to results/runs.csv.
```

> **Why reset between cases?** Without it, S3 would be tested against a pipeline that already has S2's fix, and the results couldn't be attributed. The cost is extra runs and credits. The benefit is that each case is reproducible on its own. Write this down as a trade-off in the README.
> If an exact revert via chat proves impossible, fall back to a **pristine baseline project** (a duplicate built from the same prompt log) plus a **fix-lab project** for applying fixes. Note that this costs a project slot.

### 7.2 Classification vocabulary (used in observations, README table, heat map)

| Dimension | Values |
|---|---|
| **Pipeline outcome** | `STOPPED-AT-INPUT` · `STOPPED-MID-PIPELINE` · `WARNED-AND-CONTINUED` · `CARRIED-ON-SILENTLY` · `CARRIED-ON-EMPTY` |
| **GCS impact** | `NOTHING-WRITTEN` · `CORRECT-OUTPUT` · `DEGRADED-OUTPUT` (plausible but wrong) · `EMPTY-OR-HEADER-ONLY` |
| **Log clarity (0–3)** | 0 = no or generic message · 1 = technical message without context · 2 = names the node **and** column · 3 = names the cause **and** suggests a fix |
| **Chatbot diagnosis** | `CORRECT` · `PARTIAL` · `WRONG` · `NONE` |
| **Chatbot fix** | `WORKED` (validated on drift **and** baseline) · `PARTIAL` (green but data wrong, or breaks baseline) · `FAILED` · `NOT-OFFERED` |
| **Schedule afterwards** | `CONTINUED` · `AUTO-DISABLED` · `SKIPPED-TRIGGER` · `RECOVERED-AFTER-RESET` |
| **Rhombus noticed? (semantic)** | `YES-BLOCKED` · `YES-WARNED` · `ONLY-WHEN-ASKED` · `NO` |
| **Our validation caught it?** | `YES (check IDs)` · `NO` |

### 7.3 Severity rubric

| Severity | Definition (customer impact) | Example |
|---|---|---|
| **Critical** | Wrong data reaches GCS **silently**: green run, no warning, values plausible. | Cents drift passes through and gets capped by outlier handling. |
| **High** | Failure with a missing or misleading explanation, **or** a chatbot fix that corrupts data or breaks the baseline. | "KeyError: 'country'" with no node named. A fix drops the column. |
| **Medium** | Clear failure, but recovery needs significant manual effort, or the fix only partly works. | Combined drift: chatbot fixes one of four causes per attempt. |
| **Low** | Handled gracefully or a cosmetic issue. | Added column passes through cleanly. |
| **Info** | Behaviour worth knowing, not a defect. | Column names with dots are rewritten to spaces. |

---

## 8. `/ui-tests/` design

### 8.1 Authentication
- `python ui-tests/scripts/save_auth.py` opens a **headed** Chromium at the login page. You log in by hand (works with SSO/OTP/CAPTCHA), and the script saves `context.storage_state()` to `.auth/state.json` (gitignored).
- `conftest.py` loads that state for every test. If it's missing or expired, the session test fails with a clear message ("run save_auth.py").
- Trade-off: login itself isn't automated. It's an honest choice that avoids bypassing bot protection, and the README says so.

### 8.2 Waiting strategy (no fixed sleeps)
- Only auto-waiting locators and web-first assertions: `expect(locator).to_be_visible()`, `.to_have_text()`, `.to_have_count()`, with explicit generous `timeout=` for long operations (e.g. a pipeline run of up to 5 minutes).
- Wait on **network truth**: `with page.expect_response(lambda r: <run-status endpoint> and r.ok) as resp:`, then assert on `resp.value.json()`.
- **GCS checks only happen after the UI or API reports the run finished**, and GCS listing is strongly consistent, so there's no polling loop at all.
- CI guard: `grep -RInE "time\.sleep|wait_for_timeout" ui-tests api-tests && exit 1`.

### 8.3 Selectors
- Discover them with `playwright codegen <app-url> --load-storage .auth/state.json`. Prefer `get_by_role`, `get_by_label`, `get_by_text`, and `data-testid` if the app has them. Avoid CSS and XPath chains.
- Keep every selector in **page objects** (`pages/*.py`) so a UI change means one edit in one place.

### 8.4 Test inventory

| Test | Journey step | Real-outcome assertions | Marker |
|---|---|---|---|
| `test_00_session::test_authenticated_landing` | session | Workflow/Projects page visible. Project `rhombus-qa-etl` listed. | default |
| `test_01_s3_source::test_source_connected` | **S3 connection** | Source `qa-source` shows as connected, bucket name matches env, `orders.csv` visible under `pipeline/` (via Search). | default |
| `test_01_s3_source::test_invalid_region_rejected` *(optional)* | S3 negative | In the scratch project, wrong Region → verification error shown, no source created. | `negative` |
| `test_02_ai_pipeline::test_baseline_pipeline_shape` | **AI-built pipeline** | Canvas has a Data Input bound to `orders.csv`, ≥ N transformation nodes, and a Data Output. Node count equals the snapshot. | default |
| `test_02_ai_pipeline::test_ai_builds_pipeline_from_prompt` | AI build, end-to-end | In the scratch project: send a `/pipeline` prompt → nodes appear (`to_have_count` ≥ 3) → Run → status "Succeeded" → Preview shows rows. | `e2e` (costs credits) |
| `test_03_gcs_destination::test_run_writes_to_gcs` | **GCS destination** | Data Output shows the GCS destination. Click **Run Pipeline**, wait for completion via the status/response, then assert a **new** `orders_clean_*` object exists with timestamp ≥ test start, header == contract, rows == manifest. | `slow` |
| `test_04_schedule::test_schedule_active` | **Schedule** | Card shows **Active**, the expected frequency, timezone `Australia/Adelaide`, and **Next run** within one interval of now. | default |
| `test_04_schedule::test_schedule_crud` | Schedule CRUD | In the scratch project: create a Daily schedule → card appears → toggle off → **Inactive** → delete → card gone (cleanup in `finally`). | default |

Commands:
```bash
pytest ui-tests                       # default: fast, read-only + scratch CRUD
pytest ui-tests -m slow               # runs the pipeline and checks GCS
pytest ui-tests -m e2e --headed       # AI-build end to end (uses credits)
pytest ui-tests --tracing retain-on-failure --video retain-on-failure --screenshot only-on-failure
```

### 8.5 Example (shape, not final code)
```python
# ui-tests/tests/test_03_gcs_destination.py
import time, pytest
from playwright.sync_api import Page, expect
from pages.canvas import CanvasPage
from helpers.gcs import objects_newer_than, read_csv_header

@pytest.mark.slow
def test_run_writes_to_gcs(page: Page, env, contract, manifest):
    started_ms = int(time.time() * 1000)
    canvas = CanvasPage(page).open(env.project_name)
    expect(canvas.output_destination_label).to_contain_text("Google Cloud Storage")

    canvas.run_pipeline()                                   # clicks the play icon "Run Pipeline"
    expect(canvas.run_status).to_have_text("Succeeded", timeout=300_000)   # web-first wait, no sleep

    new = objects_newer_than(env.gcs_bucket, prefix="orders_clean_", ts_ms=started_ms)
    assert len(new) == 1, f"expected exactly one new GCS object, got {[b.name for b in new]}"
    header, rows = read_csv_header(new[0])
    assert header == [c["name"] for c in contract["columns"]]
    assert rows == manifest["baseline/orders.csv"]["expected_rows_out"]
```

---

## 9. `/api-tests/` design

### 9.1 Discovering endpoints
1. Record a HAR during the UI journey: `browser.new_context(record_har_path="api-tests/har/journey.har", storage_state=...)`. Alternatively export from Chrome DevTools → Network → "Save all as HAR". **Keep the HAR out of git** (it contains tokens).
2. `python api-tests/scripts/har_summary.py api-tests/har/journey.har` prints the unique `(method, path-template, status, content-type)` rows.
3. Document them in `api-tests/ENDPOINTS.md`: purpose, auth mechanism (Bearer header? cookie?), request/response shape (redacted), and which UI action triggers each one.
4. Work out the auth mechanism: token in `localStorage`/cookie inside `.auth/state.json` → `client.py` extracts it, or `RHOMBUS_TOKEN` overrides.

### 9.2 Test inventory (endpoint paths filled in after discovery; ⚠ the names below are placeholders)

| Test | Type | Request | Assertions |
|---|---|---|---|
| `test_list_projects_ok` | positive | `GET /…/projects` | `200`, JSON, validates against `ProjectList` model, contains `rhombus-qa-etl` with the expected id. |
| `test_get_pipeline_definition_ok` | positive | `GET /…/projects/{id}/pipeline` (or workflow) | `200`. Node types include data input + data output. Node count == snapshot (also catches unintended pipeline changes). |
| `test_execution_history_ok` | positive | `GET /…/executions?project={id}` | `200`. Latest scheduled run has status `succeeded`, numeric duration, timestamp ≤ now. |
| `test_schedule_ok` | positive | `GET /…/schedules?project={id}` | `200`, enabled = true, timezone = `Australia/Adelaide`, frequency matches. |
| `test_no_token_rejected` | **negative** | any protected GET with no auth | `401` (or `403`). Error body has a message. **No** project data in the body. |
| `test_tampered_token_rejected` | **negative** | Bearer with one character flipped | `401`. Not `500`. |
| `test_unknown_project_404` | **negative** | `GET /…/projects/does-not-exist` | `404` (or `403`). Not `500`, no stack trace leaked. |
| `test_invalid_gcs_credentials_rejected` | **negative** | `POST` create-destination with a structurally valid but fake SA JSON | `4xx` with a meaningful message. No destination persisted (verify with a follow-up GET; clean up if one was). |
| `test_malformed_payload_400` *(optional)* | negative | `POST` with missing required fields | `400`/`422` validation error, not `500`. |

**Scope and ethics:** only our own account and resources, read-only or self-cleaning calls, no load or fuzzing, no attempts to get at other tenants' data. If a status code turns out *different* from what's expected (e.g. `500` for a missing token), the test is written against the **correct** behaviour and marked `xfail(strict=True, reason="FINDING: …")`. The finding goes into the README instead of the assertion being bent to match the bug.

### 9.3 Example
```python
# api-tests/tests/test_negative_auth.py
import requests, pytest

PROTECTED = "/projects"          # ⚠ replace with the discovered path

def test_no_token_rejected(api_base):
    r = requests.get(f"{api_base}{PROTECTED}", timeout=30)
    assert r.status_code in (401, 403), r.text[:300]
    body = r.json() if "json" in r.headers.get("content-type", "") else {}
    assert "rhombus-qa-etl" not in r.text            # no data leakage
    assert any(k in body for k in ("message", "detail", "error")), body
```

---

## 10. Timeline and run budget

### 10.1 Day plan (assuming receipt Sun 4 Oct 2026, due Sun 11 Oct 2026)

| Day | Focus | Exit criteria |
|---|---|---|
| **Sun 4 Oct** | Research (done). Sign up. **Check plan limits** (connections, scheduling, credits). AWS + GCP setup. Repo scaffold (structure, `.gitignore`, `.env.example`, Makefile, CI guard). | Blockers known. Recruiter emailed if needed (§11). |
| **Mon 5 Oct** | `generate.py` + data dictionary + manifest. Upload the baseline. Connect S3. AI-build the pipeline (prompt log). GCS destination. **S3 re-read smoke test (§5.3).** Validator skeleton + contract + oracle. | Manual run → validator PASS on the baseline. |
| **Tue 6 Oct** | Create the schedule. **First scheduled baseline run** → validate → `reference_profile.json`. Baseline consistency ×3. Start S1, S2. Save auth state and record the HAR. | R-07 done. Two observations drafted. |
| **Wed 7 Oct** | S3, S4. Build the UI test suite (page objects, 4 journey areas). | UI suite green locally. |
| **Thu 8 Oct** | S5 combined, M1 cents. Build the API test suite (≥ 2 positive, ≥ 3 negative). | API suite green (or xfail findings). |
| **Fri 9 Oct** | M2 date swap (+ M3 optional). `run_all.py` over every run. Finish all observation files. Rank the top 3 findings. | Every case has a filled observation + validator report. |
| **Sat 10 Oct** | README (all 4 sections + decisions/trade-offs). Dashboard + GitHub Pages. Record the demo video. **Fresh-clone test.** | Public dashboard URL works. Video link in README. |
| **Sun 11 Oct** | Buffer, QA gate (§16), secrets scan, submit **in the morning**, well before the deadline. | Submitted. |

### 10.2 Scheduled-run budget
If the plan caps scheduled runs (Personal = 5/day), use a **Custom cron** instead of Hourly, e.g. `5 9,13,17,21 * * *` (09:05, 13:05, 17:05, 21:05 Adelaide time). That gives 4 slots a day. Each drift case needs **one** scheduled slot. Fix verification, regression and reset runs are **manual**.

| Item | Scheduled runs | Manual runs |
|---|---|---|
| Baseline (+ smoke test) | 1–2 | 2 |
| Baseline consistency ×3 | 0–3 | 3 |
| S1–S5 (5 cases) | 5 | ~3 each = 15 |
| M1–M2 (+M3) | 2–3 | ~2 each = 6 |
| Post-incident schedule observation | covered by the next case's slot | — |
| **Total** | **≈ 10–13 over 5 days** | **≈ 26** |

Record **credits before and after** every chat and run in `results/runs.csv` (columns: `run_id, case, trigger(scheduled|manual), start_iso, duration_s, status, failed_node, gcs_object, credits_before, credits_after, validator_status`). This feeds the dashboard's resource panel.

---

## 11. Email template for blockers

Send this on day 1 only if plan limits block S3 + GCS + scheduling. Asking early and precisely is good judgement in itself.

```
Subject: Rhombus AI take-home: quick question on account limits

Hi <name>,

Thanks for the exercise; I've started on it today. On the Free plan I can see a limit of
<1 data connection / no scheduling / 50 credits>, while the scenario needs an S3 source, a GCS
destination and a recurring schedule with several drift runs.

Is there an assessment or trial tier you'd like candidates to use, or should I upgrade to <plan>
for the week? Until I hear back I'll keep building the datasets, validation and test framework.

Best regards,
Manas
```

---

## 12. `/observations/` template and evidence conventions

### 12.1 `observations/_TEMPLATE.md`
~~~markdown
# <Case ID>: <Title>  (e.g. S2: Schema drift, rename column)

| Field | Value |
|---|---|
| Case ID / file | S2 · `datasets/schema/S2-rename-column.csv` (S3 versionId `…`) |
| Date/time (ACDT) | 2026-10-06 13:05 (scheduled trigger) |
| Pipeline version | `evidence/S2/pipeline-before.json` (== baseline: ✅) |
| **Pipeline outcome** | STOPPED-MID-PIPELINE |
| **GCS impact** | NOTHING-WRITTEN |
| **Log clarity** | 2/3 |
| **Chatbot diagnosis / fix** | CORRECT / PARTIAL |
| **Schedule afterwards** | CONTINUED |
| **Severity** | High |

## 1. What I changed
Exact transform + header diff:
```diff
- order_id,customer_name,email,…
+ order_id,customer_full_name,email,…
```
Row count unchanged (525). Generated by `datasets/generate.py --case S2`.

## 2. What I expected (hypothesis)
…and why (which node references the column).

## 3. What happened
Timeline with timestamps: upload → trigger → status → failed node → email.
Screenshot: ![run failed](evidence/S2/01-run-failed.png)

## 4. What reached GCS
Object name / none. Validator summary (link `evidence/S2/validator-drift.json`).

## 5. What the logs said
> verbatim excerpt (from `evidence/S2/logs.csv`)
Clarity assessment: names node? names column? suggests fix?

## 6. What the chatbot said
- Prompt (verbatim, mode): …
- Reply (verbatim or excerpt + screenshot `evidence/S2/03-chatbot.png`)
- Diagnosis correct? Why/why not.

## 7. Did the fix work?
- Fix applied (pipeline diff `pipeline-before.json` → `pipeline-after-fix.json`)
- On drifted input: validator ✅/❌ (which checks)
- On baseline input (regression): validator ✅/❌
- Verdict: WORKED / PARTIAL / FAILED

## 8. What happened to the schedule
Next trigger at …: fired? status? card state (screenshot).

## 9. How to reproduce
1. Baseline pipeline (`evidence/pipeline-build/pipeline-baseline.json`) on a schedule.
2. `scripts/upload_drift.sh S2`
3. Wait for the next scheduled run … (each step, copy-pasteable)

## 10. Severity rationale & recommendation
Why this severity under the rubric; what Rhombus could do (e.g. schema-contract check at Data Input,
fail fast with column name, suggest rename mapping).
~~~

### 12.2 Evidence naming
```
observations/evidence/<case-id>/
  01-<what>.png … NN-<what>.png       # numbered in chronological order, redacted
  logs.csv                            # Export CSV from the execution record
  log-excerpt.txt                     # the lines quoted in the .md
  chatbot.md                          # full verbatim transcript(s) with mode and timestamps
  pipeline-before.json / pipeline-after-fix.json / pipeline-after-reset.json
  validator-drift.json / validator-fix.json / validator-regression.json
  gcs-objects.txt                     # gsutil ls -l output around the run
  email.png                           # failure notification (if any)
```

---

## 13. `README.md` template

```markdown
# Rhombus AI: Scheduled ETL Drift Testing (S3 → AI pipeline → GCS)

Take-home for Software Engineer Intern (LLM Observability & QA). The pipeline is built only with
Rhombus AI's AI builder, scheduled, then broken on purpose with schema and semantic drift.

**Live dashboard:** <https://isthismanas.github.io/Rhombus-AI-Test/> · **Demo video:** <link> (≈5 min)

## Top three findings
1. **<Critical>**: one sentence: what, impact, evidence link.
2. **<High>**: …
3. **<…>**: …

## 1. Setup and how to run
### Prerequisites
Python 3.11, AWS CLI, gcloud, a Rhombus account, buckets as in `.env.example`.
### Install
    make setup        # venv + pip install -r requirements.txt + playwright install chromium
    cp .env.example .env   # fill values
    python ui-tests/scripts/save_auth.py   # one-off manual login → .auth/state.json
### UI tests (Playwright)
    make ui           # pytest ui-tests            (fast, read-only + scratch CRUD)
    make ui-slow      # pytest ui-tests -m slow     (runs pipeline, asserts GCS object)
    make ui-e2e       # pytest ui-tests -m e2e      (AI build in scratch project; uses credits)
### API tests
    make api          # pytest api-tests
### Data validation
    make validate CASE=S2 RUN=<run-id>
    make validate-all # every run in data-validation/runs.yaml → results/
    pytest data-validation/tests   # unit tests for the validator itself (no cloud)
### Reproduce a drift case
    scripts/upload_drift.sh S2   # then wait for the scheduled run; see observations/schema-rename-column.md

## 2. Observations summary
| Case | Change | Pipeline stopped? | Chatbot fix worked? | Severity | Details |
|---|---|---|---|---|---|
| Baseline | — | No (succeeded) | n/a | — | [baseline.md](observations/baseline.md) |
| S1 | Drop `country` | … | … | … | [schema-drop-column.md](observations/schema-drop-column.md) |
| S2 | Rename `customer_name` | … | … | … | [schema-rename-column.md](observations/schema-rename-column.md) |
| S3 | `unit_price` → "$1,249.50" | … | … | … | [schema-change-data-type.md](observations/schema-change-data-type.md) |
| S4 | Add `discount_code` | … | … | … | [schema-add-column.md](observations/schema-add-column.md) |
| S5 | S1+S2+S3+S4 | … | … | … | [schema-combined.md](observations/schema-combined.md) |
| M1 | $ → cents | … (noticed?) | … | … | [semantic-dollars-to-cents.md](observations/semantic-dollars-to-cents.md) |
| M2 | MM/DD → DD/MM | … | … | … | [semantic-date-mmdd-to-ddmm.md](observations/semantic-date-mmdd-to-ddmm.md) |

Classification vocabulary and severity rubric: see [observations/_TEMPLATE.md](observations/_TEMPLATE.md).

## Decisions & trade-offs
- "AI builder only": what counted as configuration vs transformation.
- Reset between cases (isolation vs credits).
- Manual login via storage state (no bot-protection bypass).
- Oracle + production validation layers.
- e2e AI-build test is opt-in (credits, non-determinism).
- Small dataset (stays below Impute/Text Cleanup/sampling limits).

## 3. Usability feedback
Paragraph 1: most helpful/enjoyable (specific features, moments).
Paragraph 2: frustrating/difficult + concrete suggestions to make it more useful and efficient
(e.g. schema-contract checks on Data Input, "Last run/Failed" on schedule cards, error messages naming
column + node, a diff of pipeline changes proposed by the agent before applying).

## 4. Demo video
<link>: UI tests, API tests and data validation walkthrough.

## Repository map
(short tree with one line per folder)
```

---

## 14. Bonus: observability dashboard

### 14.1 Data model: `dashboard/data/dashboard.json` (built by `scripts/build_dashboard.py`)
```json
{
  "generated_at": "2026-10-10T12:00:00+10:30",
  "runs": [
    {"run_id": "…", "case": "S2", "config": "baseline-pipeline", "trigger": "scheduled",
     "start": "…", "duration_s": 41.2, "status": "failed", "failed_node": "Text Case",
     "gcs_object": null, "validator": "n/a", "credits_used": 1}
  ],
  "cases": [
    {"id": "S2", "title": "Rename column", "type": "schema",
     "outcome": "STOPPED-MID-PIPELINE", "gcs_impact": "NOTHING-WRITTEN", "log_clarity": 2,
     "diagnosis": "CORRECT", "fix": "PARTIAL", "schedule": "CONTINUED", "severity": "High",
     "rhombus_noticed": null, "validator_caught": ["SCH-01"], "observation": "observations/schema-rename-column.md"}
  ],
  "consistency": [
    {"config": "baseline-pipeline × baseline.csv", "hashes": ["a1…", "a1…", "a1…"], "identical": true, "diff_html": null}
  ]
}
```

### 14.2 Panels (single page, interactive)
1. **Header KPIs**: total runs, success rate, cases handled cleanly vs broken vs missed, deterministic configs (n/N).
2. **Pipeline health by scenario**: stacked bar (succeeded/failed per scenario: baseline, S1–S5, M1–M3). Click a bar to filter the run table.
3. **Capability heat map**: rows = scenarios, columns = *Stopped? · Logs clear · Diagnosis · Fix · Schedule OK · Rhombus noticed · Our validation caught*. Cells are colour-coded with the label as text too (accessible), and the tooltip gives the one-line evidence plus a link to the observation.
4. **Output consistency**: table of config × run 1/2/3 hash (short), ✅/❌. A ❌ expands to the side-by-side diff (`diff.html` in an iframe or rendered table).
5. **Time & resource tracking**: bar/box chart of execution duration per scenario vs baseline (Δ% annotated), plus credits used per scenario.
6. **Run timeline**: scatter over time (x = start, y = duration, colour = status), with schedule triggers marked.
7. **Run table**: filterable list of all runs with links to the validator report.

### 14.3 Hosting
- `.github/workflows/pages.yml`: on push to `main`, upload `dashboard/` as the Pages artifact and deploy. Repo Settings → Pages → Source: GitHub Actions.
- URL: `https://isthismanas.github.io/Rhombus-AI-Test/`, linked at the top of the README.
- Check: loads on mobile, works without errors in the console, and has no secrets in `dashboard.json`.

---

## 15. Demo video script (target ≈ 5 minutes, Loom or unlisted YouTube)

| t | Segment | Show |
|---|---|---|
| 0:00 | Intro (20 s) | Goal, architecture diagram S3 → Rhombus → GCS, schedule. |
| 0:20 | Pipeline + schedule (40 s) | Project canvas built by AI, prompt log, schedule card. |
| 1:00 | UI tests (70 s) | `make ui` running headed → passes. Open one trace. Point out the GCS assertion and that there are no sleeps. |
| 2:10 | API tests (50 s) | `make api` → show one positive and the negative tests (401s, and any xfail finding). |
| 3:00 | Data validation (70 s) | `make validate CASE=baseline` PASS → `CASE=M1` FAIL with SEM-01/SEM-02 explained → determinism report. |
| 4:10 | Findings + dashboard (40 s) | README table, top 3 findings, dashboard heat map. |
| 4:50 | Close (10 s) | Repo link. |

Record at 1080p with notifications off and secrets hidden (`.env` never on screen).

---

## 16. Final QA gate and submission

**Functional**
- [ ] Fresh clone in a new folder → `make setup` → `make api` and `pytest data-validation/tests` pass by following the README alone.
- [ ] `make ui` passes with a fresh `save_auth.py`.
- [ ] `make validate-all` regenerates `results/` and the dashboard data without manual steps.
- [ ] Every row in the README table links to a file that exists. Every evidence link resolves (run a link checker, e.g. `lychee`).
- [ ] Every observation has all 10 template sections filled. Nothing says "TBD".

**Brief compliance** → tick every R-01…R-35 in [`01-assessment-breakdown.md` §10](./01-assessment-breakdown.md#10-master-requirements-checklist).

**Quality**
- [ ] No `sleep`/`wait_for_timeout` (CI guard green).
- [ ] Assertions check outcomes, not clicks.
- [ ] Top three findings are specific and evidenced, one line each.
- [ ] Usability feedback is concrete and constructive (2 paragraphs).
- [ ] Spelling/grammar pass. Consistent case IDs everywhere.

**Security**
- [ ] `gitleaks detect` clean on the full history.
- [ ] Screenshots and video redacted.
- [ ] Keys rotated/deleted after submission (calendar reminder).

**Submit**
- [ ] Repo public (or reviewer access granted), default branch `main`.
- [ ] Dashboard URL and video link work from an incognito window.
- [ ] Reply to the recruiter with: repo link, dashboard link, video link, and a 3-line summary of the top findings.
