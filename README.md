# Rhombus AI: scheduled ETL drift testing (S3 → AI-built pipeline → GCS)

Take-home for **Software Engineer Intern (LLM Observability & QA)** at Rhombus AI.

> 🚧 **Work in progress.** The final README will have the four required sections: setup and how to run,
> observations summary, usability feedback and demo video. Until then, the working plan is in
> [`prereq_research/`](prereq_research/), mainly the [step-by-step runbook](prereq_research/03-step-by-step-runbook.md).

## What's here so far

| Path | What it is |
|---|---|
| [`datasets/`](datasets/) | Seeded generator plus the messy baseline and every drift file. Exact defect counts are in [`DATA_DICTIONARY.md`](datasets/DATA_DICTIONARY.md). Ground truth is in [`baseline/expected_clean.csv`](datasets/baseline/expected_clean.csv). |
| [`data-validation/`](data-validation/) | `validate.py` compares the GCS output with the S3 input against [`contract.yaml`](data-validation/contract.yaml): schema, row counts, cleaning rules, determinism and semantic drift (21 checks). Includes unit tests proving each check fires. |
| [`scripts/upload.py`](scripts/upload.py) | Uploads a case to the S3 key the pipeline reads, and logs its version ID. |
| `ui-tests/`, `api-tests/` | Playwright UI tests and backend API tests (being built). |
| [`observations/`](observations/) | One write-up per drift case, plus evidence. |

## Quick start
```bash
make setup              # .venv + dependencies + Playwright Chromium (needs python3.11)
cp .env.example .env    # fill in bucket names etc.
make test-validator     # offline: 21 unit tests
make help               # every command
```
