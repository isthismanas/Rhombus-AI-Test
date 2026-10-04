"""CSV loading and type-aware parsing helpers shared by the oracle and the checks."""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

# tokens that tools commonly write for "missing". "" is the contract representation; the rest get flagged.
NULL_TOKENS = {"", "nan", "NaN", "NAN", "None", "none", "null", "NULL", "NaT", "<NA>"}
_WS = re.compile(r"\s+")


def read_csv_str(path: str | Path) -> pd.DataFrame:
    """Read every cell as a raw string so nothing is silently coerced."""
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_filter=False, encoding="utf-8-sig")


def is_null(s: pd.Series) -> pd.Series:
    return s.isin(NULL_TOKENS)


def norm_ws(v: str) -> str:
    return _WS.sub(" ", v).strip()


def to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.where(~is_null(s)), errors="coerce")


def to_date(s: pd.Series) -> pd.Series:
    """Parse ISO dates, also accepting an ISO timestamp suffix (e.g. '2026-03-14 00:00:00')."""
    cleaned = s.where(~is_null(s)).str.strip()
    return pd.to_datetime(cleaned, format="ISO8601", errors="coerce")


def parse_strict_date(v: str, formats: list[str]) -> pd.Timestamp | None:
    v = v.strip()
    for fmt in formats:
        try:
            return pd.to_datetime(v, format=fmt)
        except (ValueError, TypeError):
            continue
    return None


def canonical_csv(df: pd.DataFrame, key: str = "order_id") -> str:
    """Representation-insensitive canonical form used for determinism hashing.

    Rows are sorted by the key, null tokens become '', numbers are written at fixed precision and dates as ISO.
    Column order is kept, because a column-order change between runs IS a difference.
    """
    out = df.copy()
    for c in out.columns:
        s = out[c]
        nulls = is_null(s)
        num = pd.to_numeric(s.where(~nulls), errors="coerce")
        if num.notna().sum() == (~nulls).sum() and (~nulls).any():
            if (num.dropna() % 1 == 0).all():
                out[c] = num.map(lambda x: "" if pd.isna(x) else str(int(x)))
            else:
                out[c] = num.map(lambda x: "" if pd.isna(x) else f"{x:.2f}")
            continue
        dt = to_date(s)
        if dt.notna().sum() == (~nulls).sum() and (~nulls).any():
            out[c] = dt.dt.strftime("%Y-%m-%d").fillna("")
            continue
        out[c] = s.where(~nulls, "").map(lambda v: v.strip())
    if key in out.columns:
        k = pd.to_numeric(out[key], errors="coerce")
        out = out.assign(_k=k).sort_values(["_k", *out.columns.drop(key).tolist()], kind="mergesort")
        out = out.drop(columns="_k")
    return out.to_csv(index=False, lineterminator="\n")
