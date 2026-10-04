"""Semantic drift checks (SEM-*): the structure is unchanged but the meaning has shifted.

Two layers:
* production layer (SEM-01, SEM-03, SEM-05): statistics vs a reference profile. A real customer could run these
  with no ground truth at all.
* row-level layer (SEM-02, SEM-04): join each order with the reference baseline output on order_id to diagnose
  *what* changed (x100 prices, transposed day/month).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .frames import is_null, to_date, to_num
from .result import FAIL, PASS, SKIP, Check

CATEGORICALS = ["country", "category", "status"]


def profile(df: pd.DataFrame) -> dict:
    """Reference profile of a (validated) baseline output."""
    p: dict = {"rows": len(df)}
    if "unit_price" in df.columns:
        v = to_num(df["unit_price"]).dropna()
        p["unit_price"] = {"median": float(v.median()), "p05": float(v.quantile(0.05)),
                           "p95": float(v.quantile(0.95))}
    if "quantity" in df.columns:
        p["quantity"] = {"median": float(to_num(df["quantity"]).median())}
    if "order_date" in df.columns:
        d = to_date(df["order_date"]).dropna()
        p["order_date"] = {"min": str(d.min().date()), "max": str(d.max().date()),
                           "month_share": {int(k): float(v) for k, v in
                                           d.dt.month.value_counts(normalize=True).sort_index().items()}}
    for c in CATEGORICALS:
        if c in df.columns:
            s = df[c][~is_null(df[c])]
            p[c] = {str(k): float(v) for k, v in s.value_counts(normalize=True).items()}
    return p


def js_distance(p: dict, q: dict) -> float:
    keys = sorted(set(p) | set(q), key=str)
    a = np.array([p.get(k, 0.0) for k in keys], dtype=float)
    b = np.array([q.get(k, 0.0) for k in keys], dtype=float)
    if a.sum() == 0 or b.sum() == 0:
        return 1.0
    a, b = a / a.sum(), b / b.sum()
    m = (a + b) / 2

    def kl(x, y):
        mask = x > 0
        return float(np.sum(x[mask] * np.log2(x[mask] / y[mask])))

    return float(np.sqrt(max(0.0, (kl(a, m) + kl(b, m)) / 2)))


def sem01_price_level(out: pd.DataFrame, ref: dict, th: dict) -> Check:
    if "unit_price" not in out.columns or "unit_price" not in ref:
        return Check("SEM-01", "unit_price level vs reference", SKIP, "column missing", {})
    med = float(to_num(out["unit_price"]).median())
    ratio = med / ref["unit_price"]["median"] if ref["unit_price"]["median"] else float("inf")
    lim = th["unit_price_median_ratio_max"]
    d = {"median": med, "reference_median": ref["unit_price"]["median"], "ratio": round(ratio, 3)}
    if np.isnan(ratio):
        return Check("SEM-01", "unit_price level vs reference", FAIL, "no numeric unit_price values", d)
    if 1 / lim <= ratio <= lim:
        return Check("SEM-01", "unit_price level vs reference", PASS, f"median {med:.2f} (ratio {ratio:.2f})", d)
    hint = " → looks like a unit change (dollars→cents)" if 80 <= ratio <= 120 else ""
    return Check("SEM-01", "unit_price level vs reference", FAIL,
                 f"median {med:.2f} vs reference {ref['unit_price']['median']:.2f} = ×{ratio:.1f}{hint}", d)


def _join(out: pd.DataFrame, base: pd.DataFrame, col: str, exclude: set[int] | None = None) -> pd.DataFrame:
    o = out.assign(_k=to_num(out["order_id"]))[["_k", col]].drop_duplicates("_k")
    b = base.assign(_k=to_num(base["order_id"]))[["_k", col]].drop_duplicates("_k")
    if exclude:  # orders whose value was missing in the input (imputed, so not a semantic signal)
        b = b[~b["_k"].isin(exclude)]
    return b.merge(o, on="_k", how="left", suffixes=("_ref", "_out"))


def imputed_ids(inp: pd.DataFrame | None, col: str) -> set[int]:
    if inp is None or col not in inp.columns or "order_id" not in inp.columns:
        return set()
    return set(to_num(inp.loc[is_null(inp[col]), "order_id"]).dropna().astype(int))


def sem02_price_per_order(out: pd.DataFrame, base: pd.DataFrame | None, th: dict,
                          exclude: set[int] | None = None) -> Check:
    if base is None or "unit_price" not in out.columns or "order_id" not in out.columns:
        return Check("SEM-02", "Per-order unit_price vs baseline", SKIP, "no baseline or column missing", {})
    j = _join(out, base, "unit_price", exclude)
    r = to_num(j["unit_price_out"]) / to_num(j["unit_price_ref"])
    r = r.replace([np.inf, -np.inf], np.nan).dropna()
    if r.empty:
        return Check("SEM-02", "Per-order unit_price vs baseline", SKIP, "no comparable orders", {})
    changed = float(((r - 1).abs() > th["per_order_ratio_tolerance"]).mean())
    med = float(r.median())
    d = {"compared_orders": int(len(r)), "changed_share": round(changed, 4), "median_ratio": round(med, 3),
         "excluded_imputed_orders": len(exclude or ())}
    if changed <= 0.01:
        return Check("SEM-02", "Per-order unit_price vs baseline", PASS, f"{len(r)} orders unchanged", d)
    hint = f"; consistent ×{med:.0f} (unit change)" if abs(med - round(med)) < 0.02 and med >= 10 else ""
    return Check("SEM-02", "Per-order unit_price vs baseline", FAIL,
                 f"{changed:.0%} of {len(r)} orders changed price, median ratio {med:.2f}{hint}", d)


def sem03_date_distribution(out: pd.DataFrame, ref: dict, contract: dict, th: dict) -> Check:
    if "order_date" not in out.columns or "order_date" not in ref:
        return Check("SEM-03", "order_date window & month distribution", SKIP, "column missing", {})
    spec = next(c for c in contract["columns"] if c["name"] == "order_date")
    d = to_date(out["order_date"]).dropna()
    if d.empty:
        return Check("SEM-03", "order_date window & month distribution", FAIL, "no parseable dates", {})
    oow = float(((d < pd.Timestamp(spec["min"])) | (d > pd.Timestamp(spec["max"]))).mean())
    share = {int(k): float(v) for k, v in d.dt.month.value_counts(normalize=True).items()}
    jsd = js_distance(share, ref["order_date"]["month_share"])
    det = {"out_of_window_share": round(oow, 4), "month_jsd": round(jsd, 4),
           "month_share": dict(sorted(share.items())), "reference_month_share": ref["order_date"]["month_share"]}
    if oow <= th["date_out_of_window_max_fraction"] and jsd <= th["month_distribution_jsd_max"]:
        return Check("SEM-03", "order_date window & month distribution", PASS,
                     f"all dates in window, month JSD {jsd:.3f}", det)
    return Check("SEM-03", "order_date window & month distribution", FAIL,
                 f"{oow:.0%} of dates outside {spec['min']}…{spec['max']}, month-distribution distance {jsd:.2f}",
                 det)


def sem04_date_per_order(out: pd.DataFrame, base: pd.DataFrame | None) -> Check:
    if base is None or "order_date" not in out.columns or "order_id" not in out.columns:
        return Check("SEM-04", "Per-order order_date vs baseline", SKIP, "no baseline or column missing", {})
    j = _join(out, base, "order_date")
    ref, got = to_date(j["order_date_ref"]), to_date(j["order_date_out"])
    present = got.notna()
    same = present & (got == ref)
    transposed = present & ~same & (got.dt.month == ref.dt.day) & (got.dt.day == ref.dt.month)
    other = present & ~same & ~transposed
    lost = ~present
    lost_day_gt12 = int((lost & (ref.dt.day > 12)).sum())
    d = {"compared_orders": int(len(j)), "unchanged": int(same.sum()), "day_month_transposed": int(transposed.sum()),
         "other_changes": int(other.sum()), "missing_or_unparseable": int(lost.sum()),
         "missing_with_reference_day_gt_12": lost_day_gt12}
    if transposed.sum() == 0 and other.sum() == 0 and lost.sum() == 0:
        return Check("SEM-04", "Per-order order_date vs baseline", PASS, f"{int(same.sum())} dates unchanged", d)
    msg = (f"{int(transposed.sum())} dates day/month-transposed, {int(other.sum())} otherwise changed, "
           f"{int(lost.sum())} orders lost/unparseable ({lost_day_gt12} of them have day > 12)")
    return Check("SEM-04", "Per-order order_date vs baseline", FAIL, msg, d)


def sem05_categoricals(out: pd.DataFrame, ref: dict, th: dict) -> Check:
    res, bad = {}, {}
    for c in CATEGORICALS:
        if c not in out.columns or c not in ref:
            continue
        s = out[c][~is_null(out[c])]
        share = {str(k): float(v) for k, v in s.value_counts(normalize=True).items()}
        jsd = js_distance(share, ref[c])
        res[c] = round(jsd, 4)
        if jsd > th["categorical_jsd_max"]:
            new = sorted(set(share) - set(ref[c]))[:8]
            bad[c] = {"jsd": round(jsd, 4), "new_values": new, "top": dict(list(share.items())[:6])}
    if not res:
        return Check("SEM-05", "Categorical distributions vs reference", SKIP, "no categorical columns", {})
    if bad:
        return Check("SEM-05", "Categorical distributions vs reference", FAIL,
                     ", ".join(f"{k}: distance {v['jsd']:.2f} (new values {v['new_values']})" for k, v in bad.items()),
                     {"distances": res, "shifted": bad})
    return Check("SEM-05", "Categorical distributions vs reference", PASS,
                 ", ".join(f"{k} {v:.3f}" for k, v in res.items()), {"distances": res})


def run_all(out: pd.DataFrame, *, ref_profile: dict, ref_df: pd.DataFrame | None, contract: dict,
            inp: pd.DataFrame | None = None) -> list[Check]:
    th = contract["semantic"]
    return [
        sem01_price_level(out, ref_profile, th),
        sem02_price_per_order(out, ref_df, th, imputed_ids(inp, "unit_price")),
        sem03_date_distribution(out, ref_profile, contract, th),
        sem04_date_per_order(out, ref_df),
        sem05_categoricals(out, ref_profile, th),
    ]
