#!/usr/bin/env python3
"""Compare the Rhombus AI pipeline's GCS output with the S3 input, against the cleaning contract.

Usage (normally through `make`):
  python data-validation/validate.py run --case baseline          # newest GCS output, all checks
  python data-validation/validate.py run --case S2 --object orders_clean_1759900000000.csv
  python data-validation/validate.py run --case M1 --file some/local/output.csv
  python data-validation/validate.py latest                        # list newest GCS outputs
  python data-validation/validate.py reference                     # freeze validated baseline as reference
  python data-validation/validate.py determinism --case baseline --n 3
  python data-validation/validate.py predict --case M2             # what a literal rule-follower would output
  python data-validation/validate.py all                           # re-check every saved output → results/summary.json

Exit codes: 0 = PASS/WARN, 1 = at least one FAIL, 2 = usage/infrastructure error, 3 = no new output in GCS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rhombus_qa import checks, config, determinism, frames, oracle, report, semantic  # noqa: E402
from rhombus_qa.result import FAIL, PASS, SKIP, Check, overall  # noqa: E402

RESULTS = config.RESULTS


# ------------------------------------------------------------------ core (also used by unit tests)
def expected_for(case: str):
    if case == "probe-extra-row":
        return oracle.clean(frames.read_csv_str(config.case_input_path(case)), config.contract())
    return frames.read_csv_str(config.expected_clean_path())


def reference():
    """(profile, dataframe, source-label) used by the semantic checks."""
    observed = config.REFERENCE_DIR / "baseline_output.csv"
    if observed.exists():
        df = frames.read_csv_str(observed)
        return semantic.profile(df), df, "observed baseline run (data-validation/reference/)"
    df = frames.read_csv_str(config.expected_clean_path())
    return semantic.profile(df), df, "ground truth (run `make reference` after the baseline passes)"


def validate_frame(case: str, out, inp=None) -> list[Check]:
    c, m = config.contract(), config.manifest()
    if inp is None:
        inp = frames.read_csv_str(config.case_input_path(case))
    ref_profile, ref_df, _ = reference()
    result = checks.run_all(
        out, inp=inp, expected=expected_for(case), expected_rows=config.case_meta(case)["expected_rows_out"],
        contract=c, baseline_columns=m["cases"]["baseline"]["columns"],
        medians=m["baseline_defects"]["imputation_medians"],
    )
    result += semantic.run_all(out, ref_profile=ref_profile, ref_df=ref_df, contract=c, inp=inp)
    return result


def inp01_input_provenance(case: str, output_ts_ms: int | None) -> Check:
    """Which file was in S3 when this output was produced (from results/uploads.csv)?"""
    from rhombus_qa.io_cloud import last_upload

    if output_ts_ms is None:
        return Check("INP-01", "Input in S3 at run time = this case", SKIP, "local file, no run timestamp", {})
    up = last_upload(before_ms=output_ts_ms)
    if up is None:
        return Check("INP-01", "Input in S3 at run time = this case", SKIP, "no upload logged before this output", {})
    local_sha = hashlib.sha256(config.case_input_path(case).read_bytes()).hexdigest()
    d = {"upload": up}
    if up["case"] == case and up["sha256"] == local_sha:
        return Check("INP-01", "Input in S3 at run time = this case", PASS,
                     f"{case} uploaded {up['uploaded_at_local']} (S3 version {up['s3_version_id'][:12]}…)", d)
    return Check("INP-01", "Input in S3 at run time = this case", FAIL,
                 f"S3 held '{up['case']}' (uploaded {up['uploaded_at_local']}) when this output was written", d)


# ------------------------------------------------------------------ commands
def cmd_run(a) -> int:
    case = a.case
    config.case_meta(case)  # validates the name
    obj = None
    if a.file:
        src = Path(a.file).resolve()
        run_dir = RESULTS / case / f"file-{src.stem}-{config.now_local():%Y%m%d-%H%M%S}"
        run_dir.mkdir(parents=True, exist_ok=True)
        out_path = run_dir / "output.csv"
        shutil.copyfile(src, out_path)
        ts_ms = None
    else:
        from rhombus_qa import io_cloud

        objs = io_cloud.list_outputs()
        if not objs:
            print("No output objects found in GCS with prefix "
                  f"'{config.env('GCS_OUTPUT_PREFIX', 'orders_clean')}'. Objects in bucket:")
            for n in io_cloud.list_all_names()[:20]:
                print("   ", n)
            return 2
        if a.object:
            match = [o for o in objs if o.name == a.object]
            if not match:
                print(f"Object '{a.object}' not found. Newest: {[o.name for o in objs[:5]]}")
                return 2
            obj = match[0]
        else:
            obj = objs[0]
            up = io_cloud.last_upload()
            if up and up["case"] != case:
                print(f"⚠️  The latest upload to S3 was case '{up['case']}' ({up['uploaded_at_local']}), "
                      f"but you are validating as '{case}'.")
            if up and up["case"] == case and int(up["uploaded_at_ms"]) > obj.ts_ms:
                rec = {"case": case, "result": "NO-OUTPUT", "checked_at": config.now_local().isoformat(),
                       "upload": up, "newest_object": obj.name, "newest_object_time": obj.local_time,
                       "meaning": "No new file reached GCS after this drift upload: the run stopped before "
                                  "the Data Output node, or hasn't run yet."}
                d = RESULTS / case / f"no-output-{config.now_local():%Y%m%d-%H%M%S}"
                d.mkdir(parents=True, exist_ok=True)
                (d / "report.json").write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
                print(f"\n🛑 NO NEW OUTPUT for {case}: uploaded {up['uploaded_at_local']}, but the newest GCS "
                      f"object is {obj.name} ({obj.local_time}), which is older.\n"
                      f"   If the scheduled run already happened, GCS impact = NOTHING-WRITTEN. Recorded in {d}.\n")
                return 3
        run_dir = RESULTS / case / Path(obj.name).stem
        out_path = run_dir / "output.csv"
        if not out_path.exists():
            io_cloud.download_output(obj.name, out_path)
        ts_ms = obj.ts_ms

    out = frames.read_csv_str(out_path)
    result = [inp01_input_provenance(case, ts_ms)] + validate_frame(case, out)
    _, _, ref_src = reference()
    header = {
        "case": case,
        "description": config.case_meta(case)["description"],
        "output": obj.name if obj else str(a.file),
        "output_written": obj.local_time if obj else "n/a (local file)",
        "input_file": config.case_meta(case)["file"],
        "rows_out": len(out),
        "reference": ref_src,
        "validated_at": config.now_local().isoformat(timespec="seconds"),
    }
    report.write(run_dir, result, header)
    print(report.console(result, header, color=sys.stdout.isatty()))
    print(f"Saved: {run_dir.relative_to(config.REPO)}/report.md (paste into the observation file)")
    return 1 if overall(result) == FAIL else 0


def cmd_latest(a) -> int:
    from rhombus_qa import io_cloud

    objs = io_cloud.list_outputs()
    print(f"\nNewest outputs in gs://{config.env('GCS_BUCKET')} (Adelaide time):")
    for o in objs[: a.n]:
        print(f"  {o.local_time}   {o.size:>8} B   {o.name}")
    if not objs:
        print("  (none)")
    up = io_cloud.last_upload()
    if up:
        print(f"\nLast S3 upload: case '{up['case']}' at {up['uploaded_at_local']}  "
              f"(version {up['s3_version_id'][:16]}…)")
    print()
    return 0


def _runs(case: str) -> list[Path]:
    base = RESULTS / case
    if not base.exists():
        return []
    return sorted((p for p in base.iterdir() if (p / "output.csv").exists() and p.name != "prediction"),
                  key=lambda p: p.name)


def cmd_reference(a) -> int:
    runs = _runs("baseline")
    if a.run:
        runs = [p for p in runs if p.name == a.run]
    ok = []
    for p in runs:
        rep = json.loads((p / "report.json").read_text()) if (p / "report.json").exists() else {}
        if rep.get("result") != FAIL or a.force:
            ok.append(p)
    if not ok:
        print("No validated baseline run without FAILs found (use --force to override).")
        return 2
    src = ok[-1]
    config.REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src / "output.csv", config.REFERENCE_DIR / "baseline_output.csv")
    prof = semantic.profile(frames.read_csv_str(src / "output.csv"))
    prof["source_run"] = str(src.relative_to(config.REPO))
    (config.REFERENCE_DIR / "reference_profile.json").write_text(json.dumps(prof, indent=2) + "\n")
    print(f"Reference frozen from {src.relative_to(config.REPO)} → data-validation/reference/")
    return 0


def cmd_determinism(a) -> int:
    runs = _runs(a.case)[-a.n:]
    if a.runs:
        runs = [RESULTS / a.case / r for r in a.runs]
    out_dir = RESULTS / a.case / f"determinism-{config.now_local():%Y%m%d-%H%M%S}"
    chk = determinism.compare([p / "output.csv" for p in runs], [p.name for p in runs], out_dir)
    header = {"case": a.case, "runs_compared": ", ".join(p.name for p in runs),
              "checked_at": config.now_local().isoformat(timespec="seconds")}
    report.write(out_dir, [chk], header)
    print(report.console([chk], header, color=sys.stdout.isatty()))
    for d in chk.details.get("diffs", []):
        print(f"  side-by-side diff: {Path(d['html']).relative_to(config.REPO)}")
    return 1 if chk.status == FAIL else 0


def cmd_predict(a) -> int:
    inp = frames.read_csv_str(config.case_input_path(a.case))
    pred = oracle.clean(inp, config.contract())
    run_dir = RESULTS / a.case / "prediction"
    run_dir.mkdir(parents=True, exist_ok=True)
    pred.to_csv(run_dir / "output.csv", index=False)
    result = validate_frame(a.case, frames.read_csv_str(run_dir / "output.csv"), inp)
    header = {"case": a.case, "what": "Output a pipeline that follows the 10 rules LITERALLY would produce "
                                      "(hypothesis, not a Rhombus run)", "rows_out": len(pred)}
    report.write(run_dir, result, header)
    print(report.console(result, header, color=sys.stdout.isatty()))
    return 0


def cmd_all(a) -> int:
    summary = []
    for case_dir in sorted(p for p in RESULTS.iterdir() if p.is_dir()) if RESULTS.exists() else []:
        case = case_dir.name
        if case not in config.manifest()["cases"]:
            continue
        for run in sorted(case_dir.iterdir()):
            rep_path = run / "report.json"
            if run.name.startswith("no-output") and rep_path.exists():
                rep = json.loads(rep_path.read_text())
                summary.append({"case": case, "run": run.name, "kind": "no-output", "result": "NO-OUTPUT",
                                "upload": rep.get("upload", {}).get("uploaded_at_local")})
                continue
            if run.name.startswith("determinism") and rep_path.exists():
                rep = json.loads(rep_path.read_text())
                summary.append({"case": case, "run": run.name, "kind": "determinism", "result": rep["result"],
                                "details": rep["checks"][0]["details"]})
                continue
            if not (run / "output.csv").exists():
                continue
            out = frames.read_csv_str(run / "output.csv")
            ts = None
            m = __import__("re").search(r"(\d{13})", run.name)
            if m:
                ts = int(m.group(1))
            res = [inp01_input_provenance(case, ts)] + validate_frame(case, out)
            prev = json.loads(rep_path.read_text()) if rep_path.exists() else {}
            header = {k: prev.get(k) for k in ("case", "description", "output", "output_written", "input_file")}
            header.update({"case": case, "rows_out": len(out), "revalidated_at":
                           config.now_local().isoformat(timespec="seconds")})
            report.write(run, res, header)
            summary.append({"case": case, "run": run.name, "kind": "prediction" if run.name == "prediction" else
                            "run", "result": overall(res), "rows_out": len(out), "output_written":
                            header.get("output_written"),
                            "checks": {c.id: c.status for c in res},
                            "failed": [f"{c.id}: {c.message}" for c in res if c.status == FAIL]})
            print(f"  {overall(res):<4}  {case:<16} {run.name}")
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"\n{len(summary)} records → results/summary.json")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="validate one output")
    r.add_argument("--case", required=True)
    g = r.add_mutually_exclusive_group()
    g.add_argument("--object", help="GCS object name (default: newest)")
    g.add_argument("--file", help="local CSV instead of GCS")
    lt = sub.add_parser("latest", help="list newest GCS outputs")
    lt.add_argument("--n", type=int, default=10)
    rf = sub.add_parser("reference", help="freeze the newest passing baseline output as the reference")
    rf.add_argument("--run")
    rf.add_argument("--force", action="store_true")
    d = sub.add_parser("determinism", help="compare the last N outputs of a case")
    d.add_argument("--case", required=True)
    d.add_argument("--n", type=int, default=3)
    d.add_argument("--runs", nargs="*")
    pr = sub.add_parser("predict", help="literal-rule prediction for a case's input")
    pr.add_argument("--case", required=True)
    sub.add_parser("all", help="re-validate all saved outputs and write results/summary.json")
    a = p.parse_args(argv)
    return {"run": cmd_run, "latest": cmd_latest, "reference": cmd_reference, "determinism": cmd_determinism,
            "predict": cmd_predict, "all": cmd_all}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
