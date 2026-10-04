"""Console, JSON and Markdown rendering of check results."""
from __future__ import annotations

import json
from pathlib import Path

from .result import FAIL, PASS, SKIP, WARN, Check, overall

ICON = {PASS: "✅", FAIL: "❌", WARN: "⚠️ ", SKIP: "⏭️ "}
COLOR = {PASS: "\033[32m", FAIL: "\033[31m", WARN: "\033[33m", SKIP: "\033[90m"}
RESET = "\033[0m"


def console(checks: list[Check], header: dict, color: bool = True) -> str:
    lines = ["", "=" * 96]
    for k, v in header.items():
        lines.append(f"  {k:<18} {v}")
    lines.append("-" * 96)
    for c in checks:
        st = f"{COLOR[c.status]}{c.status:<4}{RESET}" if color else f"{c.status:<4}"
        lines.append(f"  {st}  {c.id:<7} {c.name:<42} {c.message}")
    res = overall(checks)
    counts = {s: sum(1 for c in checks if c.status == s) for s in (PASS, FAIL, WARN, SKIP)}
    tail = f"{COLOR[res]}{res}{RESET}" if color else res
    lines += ["-" * 96, f"  RESULT: {tail}   " + "  ".join(f"{k}={v}" for k, v in counts.items()), "=" * 96, ""]
    return "\n".join(lines)


def markdown(checks: list[Check], header: dict) -> str:
    lines = ["| Field | Value |", "|---|---|"] + [f"| {k} | {v} |" for k, v in header.items()]
    lines += ["", f"**Result: {overall(checks)}**", "", "| Status | Check | Name | Detail |", "|---|---|---|---|"]
    for c in checks:
        msg = c.message.replace("|", "\\|")
        lines.append(f"| {ICON[c.status]} {c.status} | {c.id} | {c.name} | {msg} |")
    return "\n".join(lines) + "\n"


def write(out_dir: Path, checks: list[Check], header: dict, extra: dict | None = None) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {**header, "result": overall(checks), "checks": [c.to_dict() for c in checks], **(extra or {})}
    (out_dir / "report.json").write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    (out_dir / "report.md").write_text(markdown(checks, header), encoding="utf-8")
    return payload
