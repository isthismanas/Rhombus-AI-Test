"""Independent reference cleaner that implements contract.yaml literally.

Two uses:
1. Unit tests prove that oracle(baseline input) == datasets/baseline/expected_clean.csv. The expected file is
   built by the generator from its typed truth table, so the two implementations cross-check each other, and
   the contract is shown to be achievable from the input.
2. `validate.py predict --case X` shows what a pipeline that follows the rules *literally* would output for a
   drifted file. That's the "what I expected" hypothesis for each observation.

Columns that are missing (drift) are skipped. Unknown columns pass through untouched.
"""
from __future__ import annotations

import pandas as pd

from .frames import norm_ws, parse_strict_date

TEXT_COLS = ["customer_name", "email", "country", "product", "category", "status"]


def clean(raw: pd.DataFrame, contract: dict) -> pd.DataFrame:
    df = raw.copy()
    cols = set(df.columns)
    allowed_status = next(c["allowed"] for c in contract["columns"] if c["name"] == "status")
    cmap = {k.lower(): v for k, v in contract["country_map"].items()}

    # rules 1-3: text normalisation, casing, country mapping
    for c in TEXT_COLS:
        if c in cols:
            df[c] = df[c].map(norm_ws)
    if "customer_name" in cols:
        df["customer_name"] = df["customer_name"].map(lambda v: v.title() if v else v)
    for c in ("email", "status"):
        if c in cols:
            df[c] = df[c].str.lower()
    if "country" in cols:
        df["country"] = df["country"].map(lambda v: cmap.get(v.lower(), v) if v else v)

    # rule 4: dates
    invalid = pd.Series(False, index=df.index)
    if "order_date" in cols:
        fmts = contract["input_date_formats"]
        iso = df["order_date"].map(lambda v: (d.strftime("%Y-%m-%d") if (d := parse_strict_date(v, fmts))
                                             is not None else ""))
        invalid |= iso == ""
        df["order_date"] = iso

    # numeric parsing (empty or unparseable -> NaN -> imputed later)
    for c in ("quantity", "unit_price"):
        if c in cols:
            df[c] = pd.to_numeric(df[c].replace("", pd.NA), errors="coerce")

    # rule 5: invalid rows
    if "quantity" in cols:
        invalid |= df["quantity"].notna() & (df["quantity"] <= contract["invalid_when"]["quantity_le"])
    if "unit_price" in cols:
        invalid |= df["unit_price"].notna() & (df["unit_price"] < contract["invalid_when"]["unit_price_lt"])
    if "status" in cols:
        invalid |= ~df["status"].isin(allowed_status)
    df = df[~invalid]

    # rule 6: malformed email -> empty
    if "email" in cols:
        df["email"] = df["email"].map(lambda v: v if "@" in v else "")

    # rule 7: dedupe on ALL columns, keep first
    df = df.drop_duplicates(keep="first")

    # rule 8: imputation
    imp = contract["imputation"]
    for c, spec in imp.items():
        if c not in cols:
            continue
        if spec["method"] == "median":
            med = df[c].median() if df[c].notna().any() else float("nan")
            if pd.notna(med):
                med = round(float(med), spec["round"])
            df[c] = df[c].fillna(med)
        elif spec["method"] == "constant":
            fill = spec["value"]
            df[c] = df[c].map(lambda v, fill=fill: v if v else fill)

    # rule 9: types / formatting
    if "order_id" in cols:
        df["order_id"] = pd.to_numeric(df["order_id"], errors="coerce").astype("Int64")
    if "quantity" in cols:
        df["quantity"] = df["quantity"].map(lambda x: "" if pd.isna(x) else str(int(round(x))))
    if "unit_price" in cols:
        df["unit_price"] = df["unit_price"].map(lambda x: "" if pd.isna(x) else f"{x:.2f}")

    # rule 10: sort
    if "order_id" in cols:
        df = df.sort_values("order_id", kind="mergesort")
        df["order_id"] = df["order_id"].astype(str)
    return df.reset_index(drop=True)
