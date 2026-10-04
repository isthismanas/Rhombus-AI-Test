"""Tests for the validator itself: each check must PASS on ground truth and FAIL on the defect it targets.

No cloud access needed. Run: pytest data-validation/tests -q
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from rhombus_qa import config, determinism, frames, oracle  # noqa: E402
from rhombus_qa.result import FAIL, PASS  # noqa: E402

spec = importlib.util.spec_from_file_location("validate", HERE.parent / "validate.py")
validate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate)


@pytest.fixture(autouse=True)
def _no_observed_reference(monkeypatch, tmp_path):
    """Use ground truth as the semantic reference, so tests don't depend on local run results."""
    monkeypatch.setattr(config, "REFERENCE_DIR", tmp_path / "no-reference")


@pytest.fixture()
def truth() -> pd.DataFrame:
    return frames.read_csv_str(config.expected_clean_path())


def by_id(checks):
    return {c.id: c for c in checks}


def run(case, out):
    return by_id(validate.validate_frame(case, out))


# ------------------------------------------------------------------ datasets & oracle
def test_dataset_files_match_manifest():
    for case, meta in config.manifest()["cases"].items():
        data = (config.REPO / meta["file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == meta["sha256"], f"{case} changed: re-run datasets/generate.py"


def test_generator_is_deterministic():
    sys.path.insert(0, str(config.DATASETS))
    import generate

    a, b = generate.generate(), generate.generate()
    assert a["rows"] == b["rows"] and a["expected"] == b["expected"]


def test_oracle_reproduces_ground_truth_exactly(truth):
    """Two independent implementations (generator truth table vs literal contract cleaner) must agree."""
    raw = frames.read_csv_str(config.case_input_path("baseline"))
    out = oracle.clean(raw, config.contract())
    assert out.to_csv(index=False) == truth.to_csv(index=False)
    assert len(out) == config.manifest()["baseline_defects"]["expected_rows_out"] == 480


def test_probe_has_exactly_one_extra_order():
    out = oracle.clean(frames.read_csv_str(config.case_input_path("probe-extra-row")), config.contract())
    assert len(out) == 481 and "1501" in set(out["order_id"])


# ------------------------------------------------------------------ the baseline passes everything
def test_ground_truth_passes_all_checks(truth):
    checks = validate.validate_frame("baseline", truth)
    failed = [f"{c.id}: {c.message}" for c in checks if c.status not in (PASS,)]
    assert not failed, failed


# ------------------------------------------------------------------ each check fires on its defect
def test_duplicate_row_detected(truth):
    c = run("baseline", pd.concat([truth, truth.iloc[[5]]], ignore_index=True).sort_values(
        "order_id", key=lambda s: s.astype(int), kind="mergesort"))
    assert c["CLN-01"].status == FAIL and c["ROW-01"].status == FAIL


def test_dropped_rows_detected(truth):
    c = run("baseline", truth.drop(index=[0, 1, 2]))
    assert c["ROW-01"].status == FAIL
    assert c["ROW-02"].details["missing_orders"] == 3


def test_renamed_column_detected_with_suggestion(truth):
    c = run("S2", truth.rename(columns={"customer_name": "customer_full_name"}))
    assert c["SCH-01"].status == FAIL
    assert c["SCH-01"].details["possible_renames"] == {"customer_name": "customer_full_name"}


def test_dropped_column_detected(truth):
    assert run("S1", truth.drop(columns=["country"]))["SCH-01"].status == FAIL


def test_text_type_detected(truth):
    t = truth.copy()
    t["unit_price"] = t["unit_price"].map(lambda v: f"${float(v):,.2f}")
    assert run("S3", t)["SCH-02"].status == FAIL


def test_untrimmed_and_wrong_case_detected(truth):
    t = truth.copy()
    t.loc[0, "customer_name"] = "  " + t.loc[0, "customer_name"].upper()
    t.loc[1, "status"] = t.loc[1, "status"].upper()
    c = run("baseline", t)
    assert c["CLN-03"].status == FAIL
    assert "customer_name:trimmed" in c["CLN-03"].details and "status:lower_case" in c["CLN-03"].details


def test_unmapped_country_detected(truth):
    t = truth.copy()
    t.loc[t["country"] == "United States", "country"] = "USA"
    assert run("baseline", t)["CLN-04"].status == FAIL


def test_wrong_imputation_detected(truth):
    raw = frames.read_csv_str(config.case_input_path("baseline"))
    missing_ids = set(raw.loc[raw["quantity"] == "", "order_id"])
    t = truth.copy()
    t.loc[t["order_id"].isin(missing_ids), "quantity"] = "4"  # mean-ish instead of median 3
    c = run("baseline", t)
    assert c["CLN-06"].status == FAIL and c["CLN-08"].status == FAIL


def test_unsorted_detected(truth):
    assert run("baseline", truth.iloc[::-1])["CLN-07"].status == FAIL


def test_timestamp_dates_only_warn(truth):
    t = truth.copy()
    t["order_date"] = t["order_date"] + " 00:00:00"
    c = run("baseline", t)
    assert c["CLN-09"].status == "WARN" and c["CLN-08"].status == PASS  # same dates, different format


# ------------------------------------------------------------------ semantic drift
def test_cents_drift_detected(truth):
    t = truth.copy()
    t["unit_price"] = t["unit_price"].map(lambda v: f"{float(v) * 100:.2f}")
    c = run("M1", t)
    assert c["SEM-01"].status == FAIL and "cents" in c["SEM-01"].message
    assert c["SEM-02"].status == FAIL and c["SEM-02"].details["median_ratio"] == pytest.approx(100, rel=0.01)


def test_day_month_swap_detected(truth):
    t = truth.copy()
    d = pd.to_datetime(t["order_date"])
    ok = d.dt.day <= 12
    t.loc[ok, "order_date"] = [f"2026-{x.day:02d}-{x.month:02d}" for x in d[ok]]  # silently transposed
    t = t[ok]                                                                      # day>12 rows lost
    c = run("M2", t)
    assert c["SEM-04"].status == FAIL and c["SEM-04"].details["day_month_transposed"] > 0
    assert c["SEM-03"].status == FAIL


def test_country_codes_detected(truth):
    t = truth.copy()
    t["country"] = t["country"].map({"Australia": "AU", "United States": "US", "United Kingdom": "GB",
                                     "India": "IN", "New Zealand": "NZ", "Unknown": "Unknown"})
    c = run("M3", t)
    assert c["SEM-05"].status == FAIL and c["CLN-04"].status == FAIL


# ------------------------------------------------------------------ determinism
def test_determinism_identical_and_formatting_only(tmp_path, truth):
    a, b, c = tmp_path / "a.csv", tmp_path / "b.csv", tmp_path / "c.csv"
    truth.to_csv(a, index=False)
    truth.to_csv(b, index=False)
    t = truth.copy()
    t["quantity"] = t["quantity"] + ".0"  # same values, different representation
    t.to_csv(c, index=False)
    r = determinism.compare([a, b, c], ["a", "b", "c"], tmp_path / "out")
    assert r.status == PASS and r.details["canonical_identical"] and not r.details["raw_identical"]


def test_determinism_detects_cell_difference(tmp_path, truth):
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    truth.to_csv(a, index=False)
    t = truth.copy()
    t.loc[3, "unit_price"] = "999.99"
    t.to_csv(b, index=False)
    r = determinism.compare([a, b], ["run1", "run2"], tmp_path / "out")
    assert r.status == FAIL
    cells = r.details["diffs"][0]["cells"]
    assert cells == [{"order_id": truth.loc[3, "order_id"], "column": "unit_price",
                      "a": truth.loc[3, "unit_price"], "b": "999.99"}]
    assert Path(r.details["diffs"][0]["html"]).exists()


def test_report_is_json_serialisable(truth, tmp_path):
    from rhombus_qa import report

    payload = report.write(tmp_path, validate.validate_frame("baseline", truth), {"case": "baseline"})
    json.dumps(payload, default=str)
    assert (tmp_path / "report.md").read_text().startswith("| Field |")
