"""Schema, row-count and cleaning-rule checks (SCH-*, ROW-*, CLN-*).

Every function takes raw-string DataFrames (as read by frames.read_csv_str) and returns a Check.
"""
from __future__ import annotations

import difflib

import pandas as pd

from .frames import is_null, to_date, to_num
from .result import FAIL, PASS, SKIP, WARN, Check


def _spec(contract: dict) -> dict:
    return {c["name"]: c for c in contract["columns"]}


def _sample(values, n: int = 5) -> list:
    return [str(v) for v in list(values)[:n]]


# ------------------------------------------------------------------ schema
def sch01_columns(out: pd.DataFrame, contract: dict) -> Check:
    exp = [c["name"] for c in contract["columns"]]
    got = list(out.columns)
    missing = [c for c in exp if c not in got]
    extra = [c for c in got if c not in exp]
    suggestions = {m: difflib.get_close_matches(m, extra, n=1, cutoff=0.7) for m in missing}
    suggestions = {k: v[0] for k, v in suggestions.items() if v}
    details = {"expected": exp, "actual": got, "missing": missing, "extra": extra,
               "possible_renames": suggestions}
    if not missing and not extra:
        if got == exp:
            return Check("SCH-01", "Output columns match contract", PASS, f"{len(got)} columns, correct order",
                         details)
        return Check("SCH-01", "Output columns match contract", WARN, "same columns, different order", details)
    parts = []
    if missing:
        parts.append(f"missing {missing}")
    if extra:
        parts.append(f"unexpected {extra}")
    if suggestions:
        parts.append("possible renames " + ", ".join(f"{k}→{v}" for k, v in suggestions.items()))
    return Check("SCH-01", "Output columns match contract", FAIL, "; ".join(parts), details)


def sch02_types(out: pd.DataFrame, contract: dict) -> Check:
    tol = contract["tolerances"]["castable_fraction"]
    bad = {}
    for name, spec in _spec(contract).items():
        if name not in out.columns or spec["dtype"] == "string":
            continue
        s = out[name]
        present = s[~is_null(s)]
        if present.empty:
            continue
        if spec["dtype"] in ("int", "float"):
            num = to_num(present)
            ok = num.notna()
            if spec["dtype"] == "int":
                ok &= (num % 1 == 0).fillna(False)
        else:  # date
            ok = to_date(present).notna()
        frac = float(ok.mean())
        if frac < tol:
            bad[name] = {"castable_fraction": round(frac, 4), "examples": _sample(present[~ok].unique())}
    if bad:
        msg = "; ".join(f"{k}: {v['castable_fraction']:.1%} parse as contract type (e.g. {v['examples'][:3]})"
                        for k, v in bad.items())
        return Check("SCH-02", "Values parse as contract types", FAIL, msg, bad)
    return Check("SCH-02", "Values parse as contract types", PASS, "all typed columns parse", {})


def sch03_input_header(inp: pd.DataFrame | None, baseline_columns: list[str]) -> Check:
    if inp is None:
        return Check("SCH-03", "Input header vs baseline input", SKIP, "no input file", {})
    got = list(inp.columns)
    if got == baseline_columns:
        return Check("SCH-03", "Input header vs baseline input", PASS, "input header unchanged", {})
    details = {"removed": [c for c in baseline_columns if c not in got],
               "added": [c for c in got if c not in baseline_columns], "input_header": got}
    return Check("SCH-03", "Input header vs baseline input", WARN,
                 f"drifted input: removed {details['removed']}, added {details['added']}", details)


# ------------------------------------------------------------------ rows
def row03_not_empty(out: pd.DataFrame) -> Check:
    if len(out) == 0:
        return Check("ROW-03", "Output not empty", FAIL, "output has no data rows (header only or empty)", {})
    return Check("ROW-03", "Output not empty", PASS, f"{len(out)} rows", {})


def row01_count(out: pd.DataFrame, expected_rows: int | None) -> Check:
    if expected_rows is None:
        return Check("ROW-01", "Row count matches expectation", SKIP, "no expected count", {})
    d = {"actual": len(out), "expected": expected_rows, "delta": len(out) - expected_rows}
    if len(out) == expected_rows:
        return Check("ROW-01", "Row count matches expectation", PASS, f"{len(out)} rows as expected", d)
    return Check("ROW-01", "Row count matches expectation", FAIL,
                 f"{len(out)} rows, expected {expected_rows} ({d['delta']:+d})", d)


def row02_accounting(out: pd.DataFrame, expected: pd.DataFrame | None, key: str) -> Check:
    if expected is None or key not in out.columns:
        return Check("ROW-02", "Order-level accounting vs ground truth", SKIP, "no ground truth or key column", {})
    got = to_num(out[key])
    exp = set(to_num(expected[key]).dropna().astype(int))
    got_set = set(got.dropna().astype(int))
    missing = sorted(exp - got_set)
    unexpected = sorted(got_set - exp)
    dup_ids = int(got.dropna().duplicated().sum())
    d = {"missing_orders": len(missing), "unexpected_orders": len(unexpected), "duplicate_order_ids": dup_ids,
         "missing_examples": missing[:10], "unexpected_examples": unexpected[:10]}
    if not missing and not unexpected and dup_ids == 0:
        return Check("ROW-02", "Order-level accounting vs ground truth", PASS,
                     "exactly the expected set of orders", d)
    return Check("ROW-02", "Order-level accounting vs ground truth", FAIL,
                 f"{len(missing)} expected orders missing, {len(unexpected)} unexpected, "
                 f"{dup_ids} duplicated order_ids", d)


# ------------------------------------------------------------------ cleaning rules
def cln01_duplicates(out: pd.DataFrame, key: str) -> Check:
    full = int(out.duplicated().sum())
    keyd = int(out[key].duplicated().sum()) if key in out.columns else 0
    d = {"duplicate_rows": full, "duplicate_keys": keyd}
    if key in out.columns and keyd:
        d["examples"] = _sample(out.loc[out[key].duplicated(keep=False), key].unique())
    if full == 0 and keyd == 0:
        return Check("CLN-01", "No duplicate rows / keys", PASS, "no duplicates", d)
    return Check("CLN-01", "No duplicate rows / keys", FAIL,
                 f"{full} fully duplicated rows, {keyd} duplicated {key} values", d)


def cln02_nulls(out: pd.DataFrame, contract: dict) -> Check:
    bad = {}
    for name, spec in _spec(contract).items():
        if name in out.columns and not spec.get("nullable", False):
            n = int(is_null(out[name]).sum())
            if n:
                bad[name] = n
    if bad:
        return Check("CLN-02", "No nulls in non-nullable columns", FAIL,
                     ", ".join(f"{k}: {v} nulls" for k, v in bad.items()), bad)
    return Check("CLN-02", "No nulls in non-nullable columns", PASS, "no unexpected nulls", {})


_RULES = {
    "trimmed": lambda v: v == v.strip(),
    "single_spaced": lambda v: "  " not in v,
    "title_case": lambda v: v == v.title(),
    "lower_case": lambda v: v == v.lower(),
    "contains_at": lambda v: "@" in v,
}


def cln03_text_rules(out: pd.DataFrame, contract: dict) -> Check:
    bad = {}
    for name, spec in _spec(contract).items():
        if name not in out.columns:
            continue
        s = out[name][~is_null(out[name])]
        for rule in spec.get("rules", []):
            viol = s[~s.map(_RULES[rule])]
            if len(viol):
                bad[f"{name}:{rule}"] = {"count": int(len(viol)), "examples": _sample(viol.unique())}
    if bad:
        return Check("CLN-03", "Text normalisation rules applied", FAIL,
                     ", ".join(f"{k} ×{v['count']}" for k, v in bad.items()), bad)
    return Check("CLN-03", "Text normalisation rules applied", PASS, "trim/spacing/case rules hold", {})


def cln04_allowed(out: pd.DataFrame, contract: dict) -> Check:
    bad = {}
    for name, spec in _spec(contract).items():
        if name in out.columns and "allowed" in spec:
            s = out[name][~is_null(out[name])]
            viol = s[~s.isin(spec["allowed"])]
            if len(viol):
                bad[name] = {"count": int(len(viol)), "values": viol.value_counts().head(10).to_dict()}
    if bad:
        return Check("CLN-04", "Categorical values allowed", FAIL,
                     ", ".join(f"{k}: {v['count']} not allowed (e.g. {list(v['values'])[:4]})"
                               for k, v in bad.items()), bad)
    return Check("CLN-04", "Categorical values allowed", PASS, "all categorical values allowed", {})


def cln05_ranges(out: pd.DataFrame, contract: dict) -> Check:
    bad = {}
    for name, spec in _spec(contract).items():
        if name not in out.columns or ("min" not in spec and "max" not in spec):
            continue
        s = out[name]
        if spec["dtype"] == "date":
            v = to_date(s)
            lo, hi = pd.Timestamp(spec["min"]), pd.Timestamp(spec["max"])
        else:
            v = to_num(s)
            lo, hi = spec.get("min", float("-inf")), spec.get("max", float("inf"))
        viol = v[(v < lo) | (v > hi)]
        if len(viol):
            show = (lambda x: str(x.date())) if spec["dtype"] == "date" else (lambda x: f"{x:g}")
            bad[name] = {"count": int(len(viol)), "min_seen": show(v.min()), "max_seen": show(v.max()),
                         "allowed": [show(lo), show(hi)]}
    if bad:
        return Check("CLN-05", "Values within valid ranges", FAIL,
                     ", ".join(f"{k}: {v['count']} outside [{v['allowed'][0]}, {v['allowed'][1]}] "
                               f"(seen {v['min_seen']}…{v['max_seen']})" for k, v in bad.items()), bad)
    return Check("CLN-05", "Values within valid ranges", PASS, "all values in range", {})


def cln06_imputation(out: pd.DataFrame, inp: pd.DataFrame | None, contract: dict, medians: dict,
                     expected: pd.DataFrame | None = None) -> Check:
    """Imputed cells must equal the contract value. For medians, the target comes from this case's ground truth
    when available (the median depends on the case's rows), else from the manifest."""
    if inp is None:
        return Check("CLN-06", "Missing values imputed per contract", SKIP, "no input file", {})
    key = contract["key"]
    tol = contract["tolerances"]["imputed_abs"]
    results, bad = {}, {}
    if key not in out.columns or key not in inp.columns:
        return Check("CLN-06", "Missing values imputed per contract", SKIP, "key column missing", {})
    o = out.assign(_k=to_num(out[key])).dropna(subset=["_k"])
    out_by_key = o.drop_duplicates("_k").set_index(o.drop_duplicates("_k")["_k"].astype(int))
    inp_keys = to_num(inp[key])
    for col, spec in contract["imputation"].items():
        if col not in inp.columns or col not in out.columns:
            results[col] = "skipped (column not in input/output)"
            continue
        ids = inp_keys[is_null(inp[col])].dropna().astype(int).unique()
        ids = [i for i in ids if i in out_by_key.index]
        if not ids:
            continue
        vals = out_by_key.loc[ids, col]
        if spec["method"] == "median":
            target = medians.get(col)
            if expected is not None and col in expected.columns and key in expected.columns:
                exp_vals = to_num(expected.loc[to_num(expected[key]).isin(ids), col]).dropna().unique()
                if len(exp_vals) == 1:
                    target = float(exp_vals[0])
            num = to_num(vals)
            wrong = vals[(num.isna()) | ((num - target).abs() > tol)]
        else:
            target = spec["value"]
            wrong = vals[vals != target]
        results[col] = {"imputed_rows": len(ids), "target": target}
        if len(wrong):
            bad[col] = {"wrong": int(len(wrong)), "of": len(ids), "target": target,
                        "examples": _sample(wrong.unique())}
    if bad:
        return Check("CLN-06", "Missing values imputed per contract", FAIL,
                     ", ".join(f"{k}: {v['wrong']}/{v['of']} imputed cells ≠ {v['target']} (e.g. {v['examples'][:3]})"
                               for k, v in bad.items()), {"checked": results, "wrong": bad})
    return Check("CLN-06", "Missing values imputed per contract", PASS,
                 ", ".join(f"{k}={v['target']}×{v['imputed_rows']}" for k, v in results.items()
                           if isinstance(v, dict)) or "nothing to impute", {"checked": results})


def cln07_sorted(out: pd.DataFrame, key: str) -> Check:
    if key not in out.columns:
        return Check("CLN-07", f"Sorted by {key}", SKIP, "key column missing", {})
    k = to_num(out[key])
    if k.is_monotonic_increasing:
        return Check("CLN-07", f"Sorted by {key}", PASS, "ascending", {})
    first_bad = int((k.diff() < 0).idxmax())
    return Check("CLN-07", f"Sorted by {key}", FAIL, f"not ascending (first break at row {first_bad + 2})",
                 {"first_break_row": first_bad + 2})


def _eq(a: pd.Series, b: pd.Series, dtype: str, tol: float) -> pd.Series:
    an, bn = is_null(a), is_null(b)
    both_null = an & bn
    if dtype in ("int", "float"):
        x, y = to_num(a), to_num(b)
        return both_null | ((x - y).abs() <= tol)
    if dtype == "date":
        x, y = to_date(a), to_date(b)
        return both_null | (x == y)
    return both_null | ((a.str.strip() == b.str.strip()) & ~an & ~bn)


def cln08_vs_ground_truth(out: pd.DataFrame, expected: pd.DataFrame | None, contract: dict) -> Check:
    key = contract["key"]
    if expected is None or key not in out.columns:
        return Check("CLN-08", "Cell-level match with ground truth", SKIP, "no ground truth or key column", {})
    spec = _spec(contract)
    o = out.drop_duplicates(key).copy()
    e = expected.copy()
    o["_k"], e["_k"] = to_num(o[key]), to_num(e[key])
    m = e.merge(o, on="_k", how="inner", suffixes=("_exp", "_out"))
    shared = [c for c in expected.columns if c in out.columns and c != key]
    tol = contract["tolerances"]["numeric_abs"]
    bad = {}
    for c in shared:
        ok = _eq(m[f"{c}_out"], m[f"{c}_exp"], spec.get(c, {}).get("dtype", "string"), tol)
        if (~ok).any():
            rows = m.loc[~ok, [f"{key}_exp", f"{c}_exp", f"{c}_out"]].head(5).values.tolist()
            bad[c] = {"mismatches": int((~ok).sum()), "of": len(m),
                      "examples": [{"order_id": r[0], "expected": r[1], "actual": r[2]} for r in rows]}
    d = {"compared_orders": len(m), "compared_columns": shared, "mismatches": bad}
    if bad:
        return Check("CLN-08", "Cell-level match with ground truth", FAIL,
                     ", ".join(f"{k}: {v['mismatches']}/{v['of']}" for k, v in bad.items()), d)
    return Check("CLN-08", "Cell-level match with ground truth", PASS,
                 f"{len(m)} orders × {len(shared)} columns identical", d)


def cln09_representation(out: pd.DataFrame, contract: dict) -> Check:
    notes = {}
    for name, spec in _spec(contract).items():
        if name not in out.columns:
            continue
        s = out[name]
        tokens = s[is_null(s) & (s != "")]
        if len(tokens):
            notes[f"{name}:null_token"] = {"count": int(len(tokens)), "tokens": _sample(tokens.unique())}
        present = s[~is_null(s)]
        if spec["dtype"] == "date":
            v = present[~present.str.fullmatch(r"\d{4}-\d{2}-\d{2}")]
            if len(v):
                notes[f"{name}:not_YYYY-MM-DD"] = {"count": int(len(v)), "examples": _sample(v.unique())}
        if spec["dtype"] == "float" and spec.get("decimals"):
            v = present[~present.str.fullmatch(rf"-?\d+\.\d{{{spec['decimals']}}}")]
            if len(v):
                notes[f"{name}:not_{spec['decimals']}dp"] = {"count": int(len(v)), "examples": _sample(v.unique())}
        if spec["dtype"] == "int":
            v = present[~present.str.fullmatch(r"-?\d+")]
            if len(v):
                notes[f"{name}:not_integer_literal"] = {"count": int(len(v)), "examples": _sample(v.unique())}
    if notes:
        return Check("CLN-09", "Output formatting as specified", WARN,
                     ", ".join(f"{k} ×{v['count']}" for k, v in notes.items()), notes)
    return Check("CLN-09", "Output formatting as specified", PASS, "dates ISO, prices 2 dp, ints literal", {})


def run_all(out, *, inp, expected, expected_rows, contract, baseline_columns, medians) -> list[Check]:
    key = contract["key"]
    return [
        sch01_columns(out, contract),
        sch02_types(out, contract),
        sch03_input_header(inp, baseline_columns),
        row03_not_empty(out),
        row01_count(out, expected_rows),
        row02_accounting(out, expected, key),
        cln01_duplicates(out, key),
        cln02_nulls(out, contract),
        cln03_text_rules(out, contract),
        cln04_allowed(out, contract),
        cln05_ranges(out, contract),
        cln06_imputation(out, inp, contract, medians, expected),
        cln07_sorted(out, key),
        cln08_vs_ground_truth(out, expected, contract),
        cln09_representation(out, contract),
    ]
