# <CASE ID>: <title>

| Field | Value |
|---|---|
| Case / input file | `<id>` · `datasets/...` (S3 version `…`, see `results/uploads.csv`) |
| Drift uploaded (ACDT) | |
| Scheduled run (ACDT) | start … · duration … s |
| Pipeline before | identical to baseline? (evidence) |
| **Pipeline outcome** | STOPPED-AT-INPUT · STOPPED-MID-PIPELINE · WARNED-AND-CONTINUED · CARRIED-ON-SILENTLY · CARRIED-ON-EMPTY |
| **GCS impact** | NOTHING-WRITTEN · CORRECT-OUTPUT · DEGRADED-OUTPUT · EMPTY-OR-HEADER-ONLY |
| **Log clarity** | 0–3 (0 none/generic · 1 technical, no context · 2 names node + column · 3 names cause + suggests fix) |
| **Chatbot diagnosis** | CORRECT · PARTIAL · WRONG · NONE |
| **Chatbot fix** | WORKED (drift + baseline validated) · PARTIAL · FAILED · NOT-OFFERED |
| **Schedule afterwards** | CONTINUED · AUTO-DISABLED · SKIPPED-TRIGGER · RECOVERED-AFTER-RESET |
| **Rhombus noticed?** (semantic) | YES-BLOCKED · YES-WARNED · ONLY-WHEN-ASKED · NO |
| **Our validation caught it?** | YES (check IDs) · NO |
| **Severity** | Critical · High · Medium · Low · Info |

## 1. What I changed
Exact transform and header diff (from `datasets/DATA_DICTIONARY.md`).

## 2. What I expected
Hypothesis and reason. Include `make predict CASE=<id>` (what a pipeline following the rules literally would output).

## 3. What happened
Timeline with timestamps → status → failed node → warning/email. Screenshots: `evidence/<id>/NN-*.png`.

## 4. What reached GCS
Object name or none. Validator summary (`results/<id>/<object>/report.md`).

## 5. What the logs said
> verbatim excerpt (`evidence/<id>/logs.csv`)

Clarity rating and why.

## 6. What the chatbot said
Prompt (mode, verbatim) → reply (verbatim / screenshot). Was the diagnosis correct?

## 7. Did the fix work?
Change made → validator on drifted input → validator on baseline (regression) → verdict.

## 8. What happened to the schedule
Next trigger: fired? status? card state?

## 9. How to reproduce
1. Baseline pipeline on an hourly schedule (see `observations/baseline.md`).
2. `make upload CASE=<id>` between :10 and :55.
3. Wait for the :05 run, then `make validate CASE=<id>`.

## 10. Severity rationale and recommendation
