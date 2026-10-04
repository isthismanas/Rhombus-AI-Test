# Rhombus AI Take-Home: Detailed Breakdown of the Brief

> **Role:** Software Engineer Intern (LLM Observability & Quality Assurance), Rhombus AI
> **System under test:** Rhombus AI (web app at <https://rhombusai.com/>)
> **Deadline:** 1 week from receiving the exercise. If it arrived on Sun 4 Oct 2026, it's due **Sun 11 Oct 2026**. Confirm the exact date/time against the email.
> **Source of truth:** the four screenshots in [`images/`](./images/). A verbatim transcription is in [§1](#1-verbatim-transcription-of-the-brief).
> **Companion doc:** [`02-deliverables-execution-plan.md`](./02-deliverables-execution-plan.md) covers how each deliverable gets built and submitted.
> **Research date:** 4 Oct 2026. Platform facts below come from <https://doc.rhombusai.com/> on that date. Items marked **⚠ VERIFY** are inferred or undocumented and need checking in the live app.

---

## Table of contents

0. [TL;DR: what they actually want](#0-tldr-what-they-actually-want)
1. [Verbatim transcription of the brief](#1-verbatim-transcription-of-the-brief)
2. [Requirement-by-requirement decomposition](#2-requirement-by-requirement-decomposition)
3. [Rhombus AI platform primer (from the docs)](#3-rhombus-ai-platform-primer-from-the-docs)
4. [Detailed step-by-step instructions for the scenario](#4-detailed-step-by-step-instructions-for-the-scenario)
5. [Deliverables, explained one by one](#5-deliverables-explained-one-by-one)
6. [Optional bonus: observability dashboard](#6-optional-bonus-observability-dashboard)
7. [Hidden requirements, ambiguities and judgement calls](#7-hidden-requirements-ambiguities-and-judgement-calls)
8. [Risks and blockers to clear on day 1](#8-risks-and-blockers-to-clear-on-day-1)
9. [How we'll probably be evaluated](#9-how-well-probably-be-evaluated)
10. [Master requirements checklist](#10-master-requirements-checklist)
11. [Documentation index (sources)](#11-documentation-index-sources)

---

## 0. TL;DR: what they actually want

1. Act as a **real customer**. Build a **scheduled ETL pipeline**: **Amazon S3 → AI-built cleaning pipeline → Google Cloud Storage**, running on a schedule.
2. Get **one successful scheduled run** and treat it as the **baseline**.
3. **Break the input on purpose**:
   - **Schema drift**: drop a column, rename a column, change a data type, add a column. Test each one alone, then all four together.
   - **Semantic drift**: same structure, different meaning. At least two cases, e.g. dollars → cents, MM/DD → DD/MM.
4. For every break, record: did it **stop, warn, or carry on**? What **reached GCS**? Were the **logs** clear? Did the **chatbot** diagnose it and did its **fix work**? What happened to the **schedule**?
5. Back it up with engineering: **UI tests** (Playwright/Cypress), **API tests** (positive and negative), and a **data-validation script** (GCS output vs S3 input).
6. Write it up **reproducibly**: one Markdown file per drift case, evidence folder, README with a summary table, top 3 findings, usability feedback and a demo video.
7. **Bonus:** a hosted, interactive observability dashboard.
8. Grading is on **judgement, test quality and clarity of reporting**, not on whether the platform passes. "A clear, reproducible write-up of something that goes wrong is a strong result." "Quality over quantity."

---

## 1. Verbatim transcription of the brief

*(Transcribed from the screenshots so it can be searched and quoted. The images are canonical.)*

### Software Engineer Intern (LLM Observability & Quality Assurance) | Rhombus AI

#### Take-Home Exercise
- **Deadline:** 1 week from receiving the exercise
- **System Under Test:** Rhombus AI
- **Web Application:** https://rhombusai.com/

#### Purpose
Test Rhombus AI the way a customer uses it: as a scheduled ETL pipeline from a cloud source to a cloud destination. Build the pipeline, then break its input on purpose and find out how the platform responds.

We are evaluating your judgement, test quality and how clearly you report what you find. We are not grading the platform. A clear, reproducible write-up of something that goes wrong is a strong result.

#### The Scenario

**1. Build the pipeline**
- **Sign up** for Rhombus AI (https://rhombusai.com/).
- **Connect Amazon S3** as the source and upload a messy CSV of your choice (duplicates, missing values, inconsistent formatting, invalid entries).
- **Build a cleaning pipeline using the AI builder only.** No manual transformations.
- **Set Google Cloud Storage** as the destination.
- **Schedule the pipeline** at a regular interval. Wait for one successful scheduled run as your baseline.

**2. Schema drift**
A change to the structure of the data. Before the next scheduled run, change the source file to drop a column, rename a column, change a data type and add a new column. Test each change on its own, then all together, and find out:
- Does Rhombus AI stop the pipeline, warn, or carry on? If it carries on, what reaches GCS?
- Do the logs explain the problem clearly?
- When you give the error to the chatbot, does it diagnose it correctly, and does its fix actually work?
- What happens to the schedule afterwards?

**3. Semantic drift**
A change to the meaning of the data while the structure stays the same, for example dollars becoming cents or month/day dates becoming day/month. Introduce at least two cases. Does Rhombus AI notice? Does your data validation catch it?

#### Deliverables
One GitHub repository containing:
- **`/ui-tests/`**: Playwright or Cypress tests automating the pipeline journey (S3 connection, AI-built pipeline, GCS destination, schedule). Runnable from the command line, no fixed sleeps, with assertions on real outcomes.
- **`/api-tests/`**: at least two tests that call the backend directly (find the requests in the browser's network tab). At least one negative test, such as invalid credentials or an unauthenticated request. Assert on status codes and response contents.
- **`/data-validation/`**: a script comparing the GCS output with the S3 input. Check schema, row counts, that cleaning rules were applied, determinism, and your semantic drift cases. Run it on the baseline and every drifted run.
- **`/datasets/`**: the baseline file and every drifted version.
- **`/observations/`**: one Markdown file per drift case (e.g. `schema-rename-column.md`), covering what you changed, what you expected, what happened, what the logs and chatbot said, and whether the fix worked. Detailed enough to reproduce. Put screenshots and log excerpts in `/observations/evidence/` and link to them.
- **`README.md`**, with:
  1. **Setup and how to run** each test suite.
  2. **Observations summary:** a table with one row per drift case (change, pipeline stopped?, chatbot fix worked?, severity) linking to its file in `/observations/`, plus your top three findings in a few lines.
  3. **Usability feedback.** One or two paragraphs: what you found most helpful or enjoyable, what was frustrating or difficult, and how we could make the platform more useful and efficient for you.
  4. **Demo video link.** A short walkthrough of your UI tests, API tests and data validation.

#### Optional Bonus: Observability Dashboard
Build a live HTML dashboard and host it (GitHub Pages, Vercel, or similar). Track across all your test runs:
- **Pipeline health by scenario**: success/failure rate for baseline, each drift type, and combined drifts.
- **Output consistency**: For each pipeline configuration, run the same input 3 times. Does the output match every time, or does it vary? If variance, document it with side-by-side diffs.
- **Capability heat map**: Which drift types does Rhombus AI handle cleanly? Which break? (E.g. "column rename: handled; column drop: breaks; semantic drift: missed").
- **Time & resource tracking**: Pipeline execution time for baseline vs. each drift scenario.

Present it as a single-page interactive dashboard viewable in a browser at a public link (include the link in your README).

#### Final Notes
There is no expectation of perfection. We are looking at judgement, clarity and trade-offs. Quality over quantity.

#### Resources
- Platform documentation: https://doc.rhombusai.com/
- You can also ask the AI builder directly for help with the platform.

---

## 2. Requirement-by-requirement decomposition

Each line of the brief becomes one numbered requirement (**R-xx**) with an acceptance test. [§10](#10-master-requirements-checklist) and the execution plan refer back to these IDs.

### 2.1 Build the pipeline

| ID | Requirement (brief wording) | What "done" means (acceptance criterion) | Notes |
|---|---|---|---|
| R-01 | Sign up for Rhombus AI | Account exists. Login works headlessly for automation (storage state saved). | Record the plan tier you land on, because it sets limits (§8). |
| R-02 | Connect Amazon S3 as the source | An S3 source shows as connected in the project and the CSV is browsable/selectable from it. | Rhombus now uses a **bucket policy / CloudFormation grant**, not access keys, for S3 *sources* (§3.6). |
| R-03 | Upload a messy CSV of your choice with duplicates, missing values, inconsistent formatting and invalid entries | The CSV sits in S3 and is committed to `/datasets/`. Each of the four defect classes is present **deliberately and in known amounts**, documented in a data dictionary. | Known amounts make row-count checks possible. |
| R-04 | Build a cleaning pipeline **using the AI builder only**. No manual transformations | Every node came from `/pipeline` chat prompts. The exact prompts and the resulting node list are recorded. No node was hand-added or hand-edited. | Keep a prompt log as proof. Even a "small manual tweak" breaks this rule. |
| R-05 | Set Google Cloud Storage as the destination | Data Output node points at a GCS destination. After a run, a new object appears in the bucket. | GCS writes to the **bucket root** and appends a **millisecond timestamp** to the filename (§3.7). |
| R-06 | Schedule the pipeline at a regular interval | A schedule is enabled on the project, and the card shows frequency and next run. | Hourly is the smallest preset. Custom cron also exists. Plan limits on runs/day apply (§8). |
| R-07 | Wait for one successful **scheduled** run as your baseline | Schedule History / Pipeline Execution History has a *scheduled* (not manual) run with status *succeeded*. The GCS object exists and passes validation. | Has to be a scheduled run. A manual "Run Pipeline" doesn't count as the baseline. |

### 2.2 Schema drift

| ID | Requirement | Acceptance criterion |
|---|---|---|
| R-08 | Drop a column, **on its own** | Drifted file uploaded **before the next scheduled run**. Behaviour observed on that scheduled run. |
| R-09 | Rename a column, on its own | Same as above. |
| R-10 | Change a data type, on its own | Same as above. |
| R-11 | Add a new column, on its own | Same as above. |
| R-12 | All four together (combined) | One file with all four changes, run on schedule. |
| R-13 | For **each** of R-08…R-12: does it **stop / warn / carry on**? If it carries on, **what reaches GCS**? | Classified as STOP / WARN / CARRY-ON, with evidence. For CARRY-ON, the GCS object is downloaded, diffed and validated. |
| R-14 | For each: **do the logs explain the problem clearly?** | Log excerpt quoted, Export CSV saved, and a clarity rating with a reason (names the column? names the node? suggests a fix?). |
| R-15 | For each: **give the error to the chatbot**. Does it **diagnose correctly**, and does its **fix actually work**? | Exact prompt and verbatim reply saved. Diagnosis marked correct/partial/wrong. Fix applied, then the pipeline re-run and validated. "Works" means it passes data validation, not just that the run turns green. |
| R-16 | For each: **what happens to the schedule afterwards?** | Does it stay enabled? Do later runs fire? Is there a failure email? Does it recover once the file is fixed? Next-run timestamp captured. |

### 2.3 Semantic drift

| ID | Requirement | Acceptance criterion |
|---|---|---|
| R-17 | At least **two** semantic drift cases (same structure, different meaning) | Two or more drifted files, e.g. **dollars → cents** and **MM/DD → DD/MM**. Headers and column count identical to baseline. |
| R-18 | **Does Rhombus AI notice?** | Recorded: run status, any warnings, any chatbot/Analysis remarks when asked neutrally ("anything unusual about the latest output?"). |
| R-19 | **Does your data validation catch it?** | The validation script flags each semantic case with a specific, named check and fails (non-zero exit). The baseline passes. |

### 2.4 Deliverables and bonus

Covered in §5 and §6. R-20…R-35 are listed in the checklist (§10).

---

## 3. Rhombus AI platform primer (from the docs)

> All facts in this section are from <https://doc.rhombusai.com/>, read on 4 Oct 2026. Links are in §11.

### 3.1 What Rhombus AI is
- An AI-assisted data-prep / ETL platform. You describe transformations in plain English and an agent builds a node-based pipeline on a **canvas**.
- Three stages: **upload → build → export**.
- Inputs: CSV, XLS, XLSX; tables extracted from PDF/images and web URLs; cloud storage (**S3, Azure Blob, GCS**) and **Snowflake**.

### 3.2 Core objects

| Concept | Meaning | Gotchas |
|---|---|---|
| **Project** | Holds its datasets, transformations (pipeline) and results. | Plan limits: Free/Starter **3–5 projects**, Personal 10, Pro/Enterprise unlimited. **One pipeline per project.** |
| **Pipeline** | A linear chain of nodes. Each node feeds the next. | A **workflow** can contain several pipelines, branches and merges. |
| **Node / Transformer** | One step, e.g. Remove Duplicates or Impute. | Each node has a config panel. Double-click to edit (manual editing is off-limits for us). |
| **Data Input node** | Every runnable root must be a configured Data Input. | Bound to **exactly one dataset**. Samples **Head 100,000 rows** by default, with streaming always on. **Replaces `.` in column names with spaces.** |
| **Data Output node** | Terminal node with exactly one upstream connection. | Destinations: Download Locally (default), S3, Azure Blob, **GCS**, Snowflake. **Apply only saves settings. The file is written when the pipeline runs.** |
| **Schedule** | Runs the **whole** project pipeline on a recurrence. | Can't target a single node. Uses a **pipeline snapshot** taken at trigger time. |
| **Workspace** | Where Analysis-mode artifacts (files, tables, charts) appear. | Separate from the canvas. Analysis does **not** change nodes. |
| **Dataset Profile** | Schema, field types and statistics in the side panel. | Useful for checking inferred types after drift. |

### 3.3 Chat modes (critical for "AI builder only")

| Command | What it does | Use it for |
|---|---|---|
| *(no command)* = `/analysis` | **Default.** Analyses data and produces Workspace artifacts. **Never creates or modifies canvas nodes.** | Asking "did anything look wrong?" for R-18. Diagnosing errors. |
| `/pipeline` | **Builds, inspects or changes** the canvas pipeline. | **Building the cleaning pipeline (R-04)** and applying chatbot fixes (R-15). |
| `/agent` | Delegates complex parts of a task to sub-agents. | Optional comparison: is diagnosis better with `/agent`? |
| `/plan` | Plans the work and asks clarifying questions before changing anything. | Good first step to get a sound pipeline design before `/pipeline`. |

How to use one: open the project → **Chatbot** panel → type `/` → choose **Pipeline / Analysis / Agent / Plan** → describe the task → send. The command shows as a label above the message and applies **only to that message**.

> ⚠ **Trap:** a message sent without `/pipeline` stays in Analysis mode and **won't build anything**. If the agent "agrees" to fix something but the canvas doesn't change, check which mode the message went in.

**Running and previewing:** click the **play icon** beside **+** on the canvas toolbar (hover label "Run Pipeline") → wait → select a node → click **Preview** (appears beside **Workspace**). After any change, re-run before you preview again.

**Errors:** if a node reports an error, a **"Fix in Chat"** button sends it to the agent. This is the built-in way to "give the error to the chatbot" (R-15). Use it, and also try pasting the raw log text, then compare the two.

### 3.4 Transformers we're likely to see the AI choose
*(Categories: Combine & Shape, Clean & Format, Transform & Enhance, Detect & Manage, Organize, and Custom/LLM nodes.)*

| Transformer | Key behaviour from the docs | Why it matters for testing |
|---|---|---|
| **Remove Duplicates** | Requires **Columns to Consider** (≥1). Options: **Keep First / Keep Last / Remove All**. Exact match only. No fuzzy or case-insensitive matching. Depends on row order. | Near-duplicates ("John " vs "john") survive unless text is normalised **first**, so the order of nodes matters. If the AI picked specific columns and one gets **renamed or dropped**, expect breakage. |
| **Impute** | **Numeric columns only.** "Smart Imputation" on by default (picks a strategy automatically). 13 manual methods. KNN / Decision Tree / Random Forest reject **>10,000 rows or >20,000 total cells**. All-null columns are skipped with a warning. | Smart imputation could be **non-deterministic** (Random Forest uses a random state), which feeds the consistency test. **Keep the dataset under 20k cells** if a model-based method might get picked. |
| **Text Cleanup** | Strips punctuation, normalises whitespace, optional null replacement. Standard (pandas) mode **rejects ≥100,000 rows**. Pandas and PySpark modes behave differently (emojis, kept punctuation, null handling). | Keep the dataset small. A data-type drift (e.g. `$12.50` strings) may interact with punctuation stripping. |
| **Convert Column Type** (*change-data-type*) | Numeric / Text / DateTime / Categorical. Docs **don't say** what happens to unparseable values (likely NaN). | Central to **type drift** and **DD/MM drift**. The undocumented coercion is exactly what we're probing. |
| **Infer Schema Type** | Converts parseable strings to datetime, numeric strings to int/float, finds categoricals, downcasts numbers. Inconsistent dates won't be recognised. | Type drift may be silently "absorbed" or silently break things. |
| **Detect / Handle Outliers** | Handle reads the mask from Detect. Options **Cap & Floor** (Tukey/MAD/Min-Max) or **Remove** rows. | **Cents drift** inflates prices 100×. Outlier handling might **cap** them (silent corruption) or **remove** them (row loss). Either is a key finding. |
| **Text Case, Regex Filter, Drop Columns, Rename, Split Columns, Sort, Normalize, Encode** | Standard. | Rename and Drop are the obvious ways the AI might "fix" schema drift. |
| **LLM Transform (Custom)** | AI writes Python (pandas). 30–60 s timeout. **>50,000 rows get sampled down deterministically (`random_state=42`).** | If the AI uses LLM nodes, the code it generates could change between builds. Determinism is a test target. |

Changelog 6.21 (21 Jun 2026) mentions new "safeguards [that] validate sorting and type-conversion operations before running" and fixes for "datasets featuring dynamic column structures". Both are directly relevant to schema drift and worth quoting in the observations.

### 3.5 Scheduling (exact behaviour)
- Where: project → **Schedule** tab → **+ Add Schedule**. It targets that project's pipeline automatically (one pipeline per project).
- Types: **Hourly** (at minute M), **Daily** (time), **Weekly** (one weekday + time), **Monthly** (days **1–28 only**), **Custom** (5-field cron, e.g. `0 * * * *`).
- Timezone: **read-only, detected from the browser** (ours: `Australia/Adelaide`). **Don't convert times to UTC.** To change the timezone you have to delete and recreate the schedule.
- **Notify on failure:** on by default (bell icon on the card). Leave it on, because failure emails are evidence for R-16.
- Card shows: name, frequency, recurrence, **Active/Inactive**, **Next run**. The docs say it **doesn't** show "Last Run" or a "Failed" status, so you have to check history to see failures. That's worth mentioning in the usability feedback.
- Execution: runs "as if you clicked Run", using a **snapshot** of the pipeline at trigger time. **On failure, execution stops at the failed node and nothing downstream runs** (so nothing should reach GCS. Verify this).
- Failure info: the execution record names the failed node. **Export CSV** gives the backend error messages. Stack traces aren't shown.
- Monitoring: **Schedule History** (one schedule), **Pipeline Execution History** (manual + scheduled), **Dashboard Overview** (all projects).
- Limits: overlapping runs can delay or **skip** the next trigger. Maintenance can delay runs. Disabled schedules don't run.
- The docs' own advice for safe testing: *disable schedule → run manual test → re-enable*.

### 3.6 Amazon S3 source (read-only), current mechanism
- Where: **Data → Sources → Amazon S3**, or Chat **+** menu, or Data Input node → **Third Party Sources**.
- Fields: **Bucket** (no `s3://`), **Region**. Optional: **Folder/path** (prefix), **Source name**, **Source KMS key ARN** (only for customer-managed SSE-KMS).
- Access: expand **AWS access setup**, then either **(A)** merge the 3 generated bucket-policy statements (Sids start `RhomboManagedCompute…`) into the bucket policy, or **(B)** deploy the provided CloudFormation template `rhombo-s3-managed-compute-grant.yaml`. **Pick one, not both.**
- Grants read-only access: `s3:GetBucketLocation`, `s3:ListBucket`, `s3:GetObject` (scoped to the prefix if one is set).
- Click **Connect S3 source** to verify. It lists up to 100 keys and reads a small byte range.
- After changes in AWS (files added, renamed or deleted), go back to the source and click **Refresh access**. ⚠ **VERIFY:** whether a *scheduled* run re-reads the **current** object at the same key, or uses a synced snapshot. This decides whether drift reaches the pipeline at all (§7.1).
- Formats: CSV/TSV (plus gzip), Parquet, JSONL, XLSX. Legacy `.xls` isn't supported via S3. (The Data Input page says object-storage browsers accept "CSV and Excel only". **The two pages contradict each other**, which is a small documentation finding.)
- Third-party sources may need the `fivetran-3rd-party-data-integration` feature, a **free connector slot**, and **enough sync credits for the first import**.

### 3.7 Google Cloud Storage destination (write)
- In GCP: create the bucket. Create a **dedicated service account** with `storage.objects.create`, plus `storage.objects.delete` (recommended, for cleaning up the verification object). Avoid Storage Admin. Create a **JSON key**.
- In Rhombus: Data Output node → **Select Destination** → **Add New Destination** → **Google Cloud Storage** → paste the **entire JSON** → **Bucket Name** → **Create Destination** (verified automatically) → select it → format **CSV** or **Excel (XLSX)** → optional **Custom Filename** → **Apply** → **run the pipeline**.
- Output naming: **bucket root**, `<base>_<millisecond timestamp>.<ext>`. Default base is `RhombusAI_output`. Allowed characters: letters, digits, `-`, `_`. No spaces or dots. Must start and end alphanumeric. ≤255 characters.
- **Each run writes a new object.** Nothing gets overwritten, so the validator has to pick the object belonging to a given run (by timestamp).
- Credentials are encrypted at rest. Never commit the JSON key.

### 3.8 Plans and limits (from rhombusai.com/pricing, 4 Oct 2026)

| Plan | Price | Projects | Data connections | Credits/mo | Upload | Scheduling |
|---|---|---|---|---|---|---|
| Free | $0 | 3 | **1** | **50** | 20 MB | *not listed* |
| Starter | $29 | 5 | 3 | 500 | 100 MB | *not listed* |
| Personal | $59 | 10 | 10 | 1,500 | 1 GB | **5 scheduled runs/day** |
| Pro | $99 | Unlimited | Unlimited | 5,000 | 10 GB | Unlimited |
| Enterprise | Custom | Unlimited | Unlimited | Unlimited | Unlimited | Unlimited |

> ⚠ The **Free** tier lists **1 data connection**, while we need S3 *and* GCS. It also **doesn't mention scheduling**, which we must have. Check this on day 1 (§8).

---

## 4. Detailed step-by-step instructions for the scenario

These are the instructions themselves. [`02-deliverables-execution-plan.md`](./02-deliverables-execution-plan.md) turns them into a schedule and repo.

### Phase A: Accounts and cloud prerequisites (day 1)

**A1. Rhombus account**
1. Go to <https://rhombusai.com/> → **Sign In** → **Sign Up**. Use **email + password** if offered, because automation is much easier than with Google SSO (§7.4).
2. After login the Workflow page opens. Note the plan tier and remaining credits.
3. Check scheduling is available: create a throwaway project → **Schedule** tab → is **+ Add Schedule** enabled? Delete the project afterwards.
4. Check the connection allowance: can you add one source **and** one destination?
5. If anything is blocked, email the recruiter the same day (template in plan doc §11) and ask whether candidates get elevated access. That's a judgement signal in itself.

**A2. AWS (S3 source)**
1. AWS account (free tier is fine). Pick **one region**, e.g. `ap-southeast-2` (Sydney), and use it everywhere.
2. Create bucket `rhombus-qa-source-<suffix>`. Block all public access. Use default SSE-S3 encryption (avoids KMS complexity). **Turn on versioning** so every drift upload is preserved as evidence.
3. Make prefix `pipeline/`. The object key will be **`pipeline/orders.csv`**. We **overwrite this same key** for every drift case.
4. Make a local CLI profile for *your* uploads (an IAM user with `s3:PutObject/GetObject/ListBucket` on that bucket only). Rhombus itself gets access through the bucket policy it generates.

**A3. GCP (GCS destination)**
1. GCP project (free trial or always-free tier). Create bucket `rhombus-qa-dest-<suffix>`, single region near the S3 region (`australia-southeast1`), uniform bucket-level access.
2. Service account **`rhombus-writer`** with a bucket-scoped **custom role** containing `storage.objects.create` and `storage.objects.delete`. Alternatively `roles/storage.objectUser` on the bucket only. Create a **JSON key** and keep it outside the repo.
3. Second service account **`qa-reader`** with `roles/storage.objectViewer` on the bucket. **The validation script uses this one.** Least privilege means the tests can't write anything.

**A4. Local tooling**
- Python 3.11+, `pip install -r requirements.txt` (playwright, pytest, pandas, boto3, google-cloud-storage, requests, pydantic, jsonschema).
- `playwright install chromium`
- AWS CLI, `gcloud` CLI, `jq`, `git`.
- `.env` (gitignored) for all secrets and IDs.

### Phase B: Build the baseline pipeline (day 1–2)

**B1. Make the messy CSV**
- A small but realistic dataset, e.g. **e-commerce orders**, about **500 unique rows + about 25 duplicates**, about 10 columns. That keeps it under the 20k-cell limit for model-based imputation (§3.4).
- Generate it with a **seeded script** (`datasets/generate.py`, seed 42) so it can be rebuilt and every defect is **counted**. Exact schema and defect counts are in plan doc §4.
- Write `datasets/DATA_DICTIONARY.md` listing every column, its type, meaning and units, and every injected defect with its count.

**B2. Upload to S3**: `aws s3 cp datasets/baseline/orders.csv s3://<bucket>/pipeline/orders.csv`. Record the version ID and ETag.

**B3. Connect S3 in Rhombus**
1. Create project **`rhombus-qa-etl`**.
2. **Data → Sources → Amazon S3**. Bucket = `<bucket>`, Region = `ap-southeast-2`, Folder/path = `pipeline/`, Source name = `qa-source`.
3. Expand **AWS access setup**, copy the JSON, merge it into the bucket policy. Never replace the existing policy outright (the docs' CLI merge recipe is fine).
4. **Connect S3 source**. Confirm `orders.csv` is listed. Screenshot it with secrets redacted.

**B4. Build the cleaning pipeline with AI only**
1. Chatbot: `/plan` with something like: *"I have an orders CSV from S3 with duplicates, missing values, inconsistent formatting and invalid entries. Plan a cleaning pipeline that outputs to Google Cloud Storage. Ask me anything you need."* Answer its questions. Save the transcript.
2. Then `/pipeline` with an **explicit, rule-based** prompt (template in plan doc §5.2) that states each cleaning rule: trim/normalise text, canonical country values, standardise dates to ISO, numeric types, impute or drop missing values per column, remove invalid rows, dedupe on all columns *after* normalising, sort by `order_id`.
3. Review the nodes. If something is wrong, **correct it only through further `/pipeline` prompts**. Record each prompt and what changed in `observations/evidence/pipeline-build/`.
4. Ask `/pipeline` to *"add a Data Output node writing CSV to Google Cloud Storage."* Create the GCS destination when prompted. If the destination form needs manual credential entry, that's connector configuration, not a transformation, so it's allowed. Say so in the README (§7.2).
5. **Run Pipeline**. Preview the final node. Confirm a new object `orders_clean_<ts>.csv` is in GCS.
6. Freeze the cleaning-rule contract: the agreed rules become `data-validation/contract.yaml` (plan doc §6). The validator checks the pipeline against **this**, not against whatever the AI happened to do.

**B5. Schedule and wait for the baseline**
1. **Schedule** tab → **+ Add Schedule** → **Hourly** at minute `:05` (or a Custom cron if plan limits force fewer runs per day, §8). Timezone shows `Australia/Adelaide`. **Notify on failure: ON**. **Create**.
2. Wait for the first **scheduled** run. Confirm *succeeded* in Schedule History. Confirm a new GCS object with a matching timestamp.
3. Run the validator on it → **PASS**. That's the **baseline (R-07)**. Tag it in git: `baseline-ok`.
4. Consistency (bonus): collect 3 runs of the baseline input (scheduled or manual) and compare their hashes.

### Phase C: Schema drift (day 2–4)

Repeat this **drift loop** for each case S1 → S5, one case per scheduled slot:

| Step | Action | Evidence to capture |
|---|---|---|
| 1 | Make sure the previous case is closed: baseline file restored, pipeline back to its baseline definition, one green run since. | Run ID of the green "reset" run. |
| 2 | **Before** the next scheduled trigger, upload the drifted file to the **same key** `pipeline/orders.csv`. If needed, click **Refresh access** (⚠ VERIFY whether it's required, and if so record that as a finding). | S3 version ID, upload timestamp, header diff vs baseline. |
| 3 | Let the **scheduled** run fire. Don't trigger it manually. | Schedule History row (start, duration, status). |
| 4 | Classify **STOP / WARN / CARRY-ON**. | Screenshot of the run, the failed node and any warning banner. |
| 5 | If CARRY-ON: download the new GCS object and run the validator. | Validator JSON report + diff vs baseline output. |
| 6 | Logs: open the failed node error and **Export CSV**. Rate the clarity. | `evidence/<case>/logs.csv` + quoted excerpt. |
| 7 | Chatbot: (a) click **Fix in Chat**, and (b) separately paste the raw error under `/pipeline`. Record the diagnosis. | Verbatim prompt + reply + screenshot. |
| 8 | Apply the suggested fix **through chat**. Re-run (manual is fine for verification). Validate. | Pipeline definition before/after (API JSON or screenshots), validator result. |
| 9 | **Regression check:** put the baseline file back and run the *fixed* pipeline. Does it still pass? (A "fix" that only works on drifted data is a real finding.) | Validator result. |
| 10 | **Schedule afterwards:** still enabled? Did the next trigger fire? Failure email received? Next run timestamp? | Schedule card screenshot + email screenshot. |
| 11 | Reset to baseline (step 1 of the next case) and write `observations/<case>.md`. | |

Cases (concrete definitions are in plan doc §4.3):
- **S1** `schema-drop-column`: remove a column the pipeline **uses**, e.g. `country`.
- **S2** `schema-rename-column`: e.g. `customer_name` → `customer_full_name`.
- **S3** `schema-change-data-type`: e.g. `unit_price` numeric → string `"$12.50"`.
- **S4** `schema-add-column`: e.g. a new `discount_code` column.
- **S5** `schema-combined`: S1 + S2 + S3 + S4 in one file.

### Phase D: Semantic drift (day 4–5)
Same loop. Headers stay **identical**.
- **M1** `semantic-dollars-to-cents`: `unit_price` ×100 (12.50 → 1250).
- **M2** `semantic-date-mmdd-to-ddmm`: `order_date` written as DD/MM/YYYY instead of MM/DD/YYYY. Includes both days ≤12 (silent, still parseable but wrong) and days >12 (unparseable as MM/DD).
- **M3 (optional, extra credit)** `semantic-status-code-remap` or a units change (e.g. weight in g instead of kg).
- For each: did Rhombus notice (run status, warnings, neutral Analysis question)? Did **our** validator catch it, and with which check?

### Phase E: Engineering deliverables (built in parallel from day 1)
`/ui-tests`, `/api-tests`, `/data-validation`, README, video and dashboard, as described in §5 and §6 and planned in detail in the execution plan.

---

## 5. Deliverables, explained one by one

### 5.1 `/ui-tests/`: Playwright or Cypress
- **Scope (must cover all four):** ① S3 connection, ② AI-built pipeline, ③ GCS destination, ④ schedule.
- **Hard constraints:**
  - **Runnable from the command line**, e.g. `pytest ui-tests` or `npx playwright test`.
  - **No fixed sleeps.** No `time.sleep(30)` or `page.wait_for_timeout(5000)`. Use auto-waiting locators, `expect(...).to_be_visible()`, `wait_for_response`, and bounded polling of real state.
  - **Assertions on real outcomes.** Not "the button was clicked" but "the S3 source shows *Connected* and lists `orders.csv`", "the pipeline run finished with status *Succeeded*", "**a new object appeared in GCS** after the run", "the schedule shows *Active* with a *Next run* in the future".
- Good-practice signals: role/label-based selectors, page objects, storage-state auth, traces/videos on failure, secrets from env, a tagged split between fast and slow/credit-consuming tests.

### 5.2 `/api-tests/`
- **At least two tests** that call the backend directly. Endpoints come from the **browser network tab** (record a HAR while clicking through).
- **At least one negative test**: invalid credentials, unauthenticated request, etc. Doing several is better (no token, malformed token, wrong project ID, bad destination credentials).
- **Assert on status codes AND response contents**: JSON schema, specific fields, error messages, and that nothing leaks in error responses.

### 5.3 `/data-validation/`
A script that compares **GCS output** with **S3 input** and checks:
1. **Schema**: column names, order and dtypes against the contract.
2. **Row counts**: output = input − duplicates − invalid rows, matching the expected count from the data dictionary/oracle.
3. **Cleaning rules applied**: no duplicates, no unexpected nulls, trimmed/canonical text, ISO dates, valid ranges.
4. **Determinism**: the same input gives identical output across runs (canonical hash), with diffs if not.
5. **Semantic drift cases**: detected via statistical and row-level checks.
Must be **run on the baseline and every drifted run**, with the results saved.

### 5.4 `/datasets/`
The baseline file and **every** drifted version (S1–S5, M1–M2(+M3)), plus the generator script and data dictionary.

### 5.5 `/observations/`
- **One Markdown file per drift case**, named like `schema-rename-column.md`.
- Each covers: **what you changed, what you expected, what happened, what the logs said, what the chatbot said, whether the fix worked**, and is **detailed enough to reproduce**.
- Screenshots and log excerpts go in **`/observations/evidence/`**, linked from the case file.

### 5.6 `README.md`, four mandatory sections
1. **Setup and how to run** each test suite.
2. **Observations summary**: a table with one row per drift case (**change | pipeline stopped? | chatbot fix worked? | severity**) linking to each observation file, **plus the top three findings** in a few lines.
3. **Usability feedback**: 1–2 paragraphs covering helpful/enjoyable, frustrating/difficult, and how to make it more useful and efficient.
4. **Demo video link**: a short walkthrough of the UI tests, API tests and data validation.

---

## 6. Optional bonus: observability dashboard

| Panel | What to show | Data source |
|---|---|---|
| **Pipeline health by scenario** | Success/failure rate for baseline, each drift type and combined. | Execution records (Schedule History / Export CSV / API) → `results/*.json`. |
| **Output consistency** | Each pipeline configuration run **3×** on the same input. Match or vary? If it varies, **side-by-side diffs**. | Validator determinism hashes + diff HTML. |
| **Capability heat map** | Scenario × dimension grid: handled / warned / broke / missed. E.g. "rename: handled; drop: breaks; semantic: missed". | Classified observations. |
| **Time & resource tracking** | Execution time, baseline vs each drift scenario. Credits used if visible. | Execution record durations. |

Single page, interactive, **public link** (GitHub Pages), **linked in the README**. Optional, but it maps exactly onto the "LLM Observability" job title, so it's worth doing well if time allows.

---

## 7. Hidden requirements, ambiguities and judgement calls

These are the places where judgement gets graded. Each one needs a stated decision and its trade-off in the README.

1. **Does a scheduled run re-read S3?** The S3 source is a *connection*. It may read the object live at run time, or the Data Input may be bound to a dataset imported once (the docs mention "sync credits for the first import" and a **Refresh access** button). **Test this first** with a harmless change (e.g. add one row and watch the output row count). If drift doesn't propagate without a manual refresh, **that's the first major finding** and the drift protocol must say whether you refreshed.
2. **"AI builder only" vs configuration.** Transformations must come from the AI. Credentials, the destination form, and the schedule are configuration, not transformations. State this interpretation explicitly and keep a prompt log that proves every node came from chat.
3. **Test isolation between drift cases.** A chatbot fix changes the pipeline, and the next case would then test a modified pipeline. Decision: **reset to the baseline pipeline definition between cases**, either via a `/pipeline` "revert" prompt (then verify), or by keeping a pristine baseline project and a separate "fix-lab" project. Snapshot the pipeline definition (via the API) before and after each case to prove the reset.
4. **Automating login.** If sign-up uses Google SSO, email OTP or CAPTCHA, don't try to automate around it. Use a one-off **headed manual login** that saves Playwright `storageState`, and have all tests reuse it. Document this.
5. **What counts as a "fixed sleep".** Polling GCS until an object newer than the run start appears (with a timeout) is waiting on a real condition, not a fixed sleep. Say this in the README so a reviewer doesn't misread it.
6. **UI tests that cost credits and are non-deterministic.** Building a pipeline via AI in every test run burns credits and gives varying results. Split into ① **fast read-only journey checks** on the real project (default) and ② **an opt-in end-to-end AI-build test** in a scratch project (`-m e2e`). That's a deliberate trade-off.
7. **"Pipeline stopped?" may be more than yes/no.** It could fail at the input node, fail mid-pipeline, succeed with a warning, succeed silently, or succeed with **0 rows**. Use a fixed classification vocabulary (plan doc §7).
8. **"Fix worked"** means *validated output is correct*, not just a green run. A fix that makes the run green by dropping the problem column, or that breaks the baseline, is **partial** or **failed**.
9. **Data Input sampling.** The default is Head 100,000 rows. Our file is small, so it's irrelevant, but say so, because sampling would invalidate row-count checks on large files.
10. **Column names with dots** get rewritten (`.` → space). This is a small schema quirk worth one line, or an optional mini-case.
11. **Timezones.** The schedule uses Australia/Adelaide (UTC+10:30/+9:30, DST starts the first Sunday of October, which is **4 Oct 2026, today**). Record all timestamps in ISO 8601 with offset. GCS timestamps are probably epoch ms (UTC).
12. **Security hygiene.** No keys in the repo, screenshots or video. Redact. `.env.example` only. A reviewer **will** notice either way.

---

## 8. Risks and blockers to clear on day 1

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| 1 | Free plan allows **1 data connection** (we need S3 + GCS). | Can't build the scenario. | Check on day 1. Ask the recruiter for assessment access. Otherwise a 1-month Starter/Personal plan, or document the blocker. |
| 2 | Scheduling not on Free; Personal = **5 scheduled runs/day**. | Hourly schedule capped and few drift slots. | Budget runs (plan doc §10): ~8 cases × 1 scheduled run + resets ≈ 2/day over 5 days. Use custom cron at chosen times. Do verification re-runs **manually**. |
| 3 | **Credits** (50/mo on Free) used up by AI chat and runs. | Stuck mid-exercise. | Note the credit balance before and after each action (also useful for the "resource" panel). Avoid wasteful prompting. |
| 4 | Scheduled runs **don't re-read S3** (snapshot import). | Drift never reaches the pipeline. | Test first (§7.1). If so, document it, use Refresh access as part of the protocol, and record it as finding #1. |
| 5 | SSO/CAPTCHA blocks automated login. | UI/API tests can't authenticate. | `storageState` via a one-off manual login. Extract the bearer token for API tests from the saved state. |
| 6 | AI non-determinism: rebuilding gives a different pipeline. | Hard to reproduce. | Build once, snapshot the definition, never rebuild the baseline. Log prompts verbatim. |
| 7 | Cloud costs and leaked keys. | Money and security. | Free tiers, tiny files, budget alerts, delete keys after submission, never commit secrets. |
| 8 | Schedule overlap or skipped triggers. | Missing a scheduled run. | Keep runs short (small file). Leave ≥10 minutes before triggers when uploading drift. |

---

## 9. How we'll probably be evaluated

| Signal they're looking for | How we show it |
|---|---|
| **Judgement** | Explicit decisions and trade-offs (§7) in a "Decisions & trade-offs" README section. Smart case selection (drop a column the pipeline *uses*). A severity rubric. Resetting between cases. |
| **Test quality** | Real-outcome assertions that cross systems (UI → GCS). No sleeps. Negative API tests. Contract-based validation with an independent oracle. Deterministic dataset generation. CI-runnable. |
| **Clarity of reporting** | One consistent template per case. Evidence links. A summary table. Top 3 findings each in one sentence. Reproduction steps someone else can follow. |
| **Observability mindset** (role title) | Dashboard, execution timings, consistency/determinism analysis, log-quality ratings. |
| **Honesty** | Report what went wrong (including in our own setup) plainly. "Not grading the platform" means a well-documented failure is a win. |
| **Quality over quantity** | Fewer, sharper cases done properly beats many shallow ones. Extras clearly marked optional. |

---

## 10. Master requirements checklist

Tick these off before submitting. IDs refer back to §2.

**Scenario**
- [ ] R-01 Signed up, plan tier recorded
- [ ] R-02 S3 source connected (bucket policy merged, verified)
- [ ] R-03 Messy CSV with duplicates, missing values, inconsistent formatting and invalid entries, all counted
- [ ] R-04 Pipeline built via AI chat only, prompt log saved
- [ ] R-05 GCS destination, object written
- [ ] R-06 Schedule created at a regular interval
- [ ] R-07 One successful **scheduled** baseline run, validated
- [ ] R-08 Drop column (alone)
- [ ] R-09 Rename column (alone)
- [ ] R-10 Change data type (alone)
- [ ] R-11 Add column (alone)
- [ ] R-12 All four combined
- [ ] R-13 Stop/warn/carry-on classified, GCS contents inspected for each
- [ ] R-14 Log clarity assessed for each
- [ ] R-15 Chatbot diagnosis and fix tested for each, fix validated
- [ ] R-16 Schedule behaviour afterwards for each
- [ ] R-17 ≥2 semantic drift cases
- [ ] R-18 Did Rhombus notice? (each)
- [ ] R-19 Did our validation catch it? (each)

**Repository**
- [ ] R-20 `/ui-tests/` covers S3, AI pipeline, GCS and schedule. CLI-runnable, no fixed sleeps, real-outcome assertions
- [ ] R-21 `/api-tests/` has ≥2 backend tests, ≥1 negative, asserting on status **and** content
- [ ] R-22 `/data-validation/` checks schema, row counts, cleaning rules, determinism and semantic drift
- [ ] R-23 Validator run on the baseline **and every** drifted run, results committed
- [ ] R-24 `/datasets/` has the baseline + every drifted version
- [ ] R-25 `/observations/` has one `.md` per drift case, reproducible
- [ ] R-26 `/observations/evidence/` has screenshots and log excerpts, linked
- [ ] R-27 README §1 Setup & how to run (each suite)
- [ ] R-28 README §2 Observations table (change, stopped?, fix worked?, severity, link)
- [ ] R-29 README §2 Top three findings
- [ ] R-30 README §3 Usability feedback (1–2 paragraphs, three angles)
- [ ] R-31 README §4 Demo video link (UI + API + validation)
- [ ] R-32 *(Bonus)* Dashboard: health by scenario
- [ ] R-33 *(Bonus)* Dashboard: output consistency (3× runs, diffs)
- [ ] R-34 *(Bonus)* Dashboard: capability heat map
- [ ] R-35 *(Bonus)* Dashboard: time/resource tracking, public link in README

**Hygiene**
- [ ] No secrets anywhere (repo history, screenshots, video)
- [ ] Fresh-clone test: someone else can follow the README
- [ ] Submitted before the deadline

---

## 11. Documentation index (sources)

| Topic | URL |
|---|---|
| Docs home | <https://doc.rhombusai.com/> |
| Getting started | <https://doc.rhombusai.com/docs/getting-started/> |
| Pipeline quick start | <https://doc.rhombusai.com/docs/getting-started/pipeline-quickstart> |
| Usage modes (chat commands) | <https://doc.rhombusai.com/docs/getting-started/usage-modes> |
| Building a pipeline | <https://doc.rhombusai.com/docs/getting-started/building-a-pipeline> |
| Pipelines & workflows | <https://doc.rhombusai.com/docs/getting-started/basic-concepts/pipelines-and-workflows> |
| Transformers overview | <https://doc.rhombusai.com/docs/getting-started/basic-concepts/transformers> |
| Scheduling | <https://doc.rhombusai.com/docs/getting-started/basic-concepts/scheduling> |
| Amazon S3 connection | <https://doc.rhombusai.com/docs/Integrations/aws-s3-connection> |
| Google Cloud Storage connection | <https://doc.rhombusai.com/docs/Integrations/gcp-storage-connection> |
| Data Input node | <https://doc.rhombusai.com/docs/transformer-references/input-and-output/data-input> |
| Data Output node | <https://doc.rhombusai.com/docs/transformer-references/input-and-output/data-output> |
| Remove Duplicates | <https://doc.rhombusai.com/docs/transformer-references/clean-and-format/remove-duplicates-transform> |
| Text Cleanup | <https://doc.rhombusai.com/docs/transformer-references/clean-and-format/text-cleanup-transform> |
| Impute | <https://doc.rhombusai.com/docs/transformer-references/transform-and-enhance/impute-transform> |
| Convert Column Type | <https://doc.rhombusai.com/docs/transformer-references/detect-and-manage/change-data-type-transform> |
| Infer Schema Type | <https://doc.rhombusai.com/docs/transformer-references/detect-and-manage/infer-data-type-transform> |
| Handle Outliers | <https://doc.rhombusai.com/docs/transformer-references/detect-and-manage/handle-outliers-transform> |
| LLM Transform | <https://doc.rhombusai.com/docs/transformer-references/custom-nodes/llm-transform> |
| Changelog 6.21 (21 Jun 2026) | <https://doc.rhombusai.com/changelog/2026-06-21-changelog> |
| Changelog (19 Jan 2026) | <https://doc.rhombusai.com/changelog/2026-01-19-changelog> |
| Pricing | <https://www.rhombusai.com/pricing> |
| Full sitemap | <https://doc.rhombusai.com/sitemap.xml> |
