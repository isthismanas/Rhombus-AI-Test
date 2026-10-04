"""Determinism (DET-01/DET-02): does the same pipeline + same input give the same output every run?"""
from __future__ import annotations

import difflib
import hashlib
from pathlib import Path

import pandas as pd

from .frames import canonical_csv, read_csv_str
from .result import FAIL, PASS, SKIP, Check


def sha(text: str | bytes) -> str:
    data = text.encode() if isinstance(text, str) else text
    return hashlib.sha256(data).hexdigest()


def cell_diff(a: pd.DataFrame, b: pd.DataFrame, key: str = "order_id", limit: int = 50) -> list[dict]:
    if key not in a.columns or key not in b.columns:
        return []
    m = a.merge(b, on=key, how="outer", suffixes=("_a", "_b"), indicator=True)
    diffs = []
    for row in m.to_dict("records"):
        if row["_merge"] != "both":
            diffs.append({key: row[key], "column": "<row>", "a": row["_merge"] != "right_only",
                          "b": row["_merge"] != "left_only"})
            continue
        for c in a.columns:
            if c == key or c not in b.columns:
                continue
            va, vb = row.get(f"{c}_a"), row.get(f"{c}_b")
            if va != vb:
                diffs.append({key: row[key], "column": c, "a": va, "b": vb})
        if len(diffs) >= limit:
            break
    return diffs[:limit]


def compare(paths: list[Path], labels: list[str], out_dir: Path, key: str = "order_id") -> Check:
    if len(paths) < 2:
        return Check("DET-01", "Same input → identical output", SKIP, f"need ≥2 outputs, have {len(paths)}", {})
    frames = [read_csv_str(p) for p in paths]
    raw = [sha(p.read_bytes()) for p in paths]
    canon_text = [canonical_csv(f, key) for f in frames]
    canon = [sha(t) for t in canon_text]
    runs = [{"label": lab, "raw_sha256": r[:12], "canonical_sha256": c[:12], "rows": len(f)}
            for lab, r, c, f in zip(labels, raw, canon, frames, strict=False)]
    details: dict = {"runs": runs, "raw_identical": len(set(raw)) == 1, "canonical_identical": len(set(canon)) == 1}
    if len(set(canon)) == 1:
        msg = f"{len(paths)} runs identical"
        msg += " (byte-identical)" if details["raw_identical"] else " (same content; byte formatting differs)"
        return Check("DET-01", "Same input → identical output", PASS, msg, details)

    out_dir.mkdir(parents=True, exist_ok=True)
    diffs = []
    for i in range(1, len(paths)):
        if canon[i] == canon[0]:
            continue
        html = difflib.HtmlDiff(wrapcolumn=80).make_file(
            canon_text[0].splitlines(), canon_text[i].splitlines(), labels[0], labels[i], context=True, numlines=1)
        target = out_dir / f"diff-{labels[0]}-vs-{labels[i]}.html"
        target.write_text(html, encoding="utf-8")
        diffs.append({"a": labels[0], "b": labels[i], "html": str(target),
                      "cells": cell_diff(frames[0], frames[i], key)})
    details["diffs"] = diffs
    n_cells = sum(len(d["cells"]) for d in diffs)
    return Check("DET-01", "Same input → identical output", FAIL,
                 f"{len(set(canon))} distinct outputs across {len(paths)} runs ({n_cells} differing cells shown)",
                 details)
