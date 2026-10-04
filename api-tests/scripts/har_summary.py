#!/usr/bin/env python3
"""Summarise backend API calls in a HAR file without printing any secrets.

  python api-tests/scripts/har_summary.py api-tests/har/journey.har     (or: make endpoints)

Groups XHR/fetch calls by METHOD + host + path template (ids replaced by {id}), and shows status codes, how auth
was sent (header *names* only, never values), and the top-level keys of JSON responses.
Writes api-tests/ENDPOINTS.generated.md (safe to commit: no tokens, no values).
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit

NOISE = ("google", "gstatic", "sentry", "segment", "intercom", "hotjar", "posthog", "mixpanel", "clarity",
         "doubleclick", "facebook", "fonts.", "cloudflareinsights", "stripe", "hubspot", "linkedin")
ID_RE = re.compile(r"^(\d+|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|[0-9a-f]{24}|"
                   r"[A-Za-z0-9_-]{20,})$")
AUTH_HEADERS = {"authorization", "x-api-key", "x-auth-token", "cookie", "x-access-token"}


def template(path: str) -> str:
    return "/".join("{id}" if ID_RE.match(seg) else seg for seg in path.split("/"))


def shape(text: str | None) -> str:
    if not text:
        return ""
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return "(non-JSON)"
    if isinstance(data, dict):
        return "{" + ", ".join(list(data.keys())[:8]) + ("…" if len(data) > 8 else "") + "}"
    if isinstance(data, list):
        inner = shape(json.dumps(data[0])) if data else ""
        return f"[{len(data)} × {inner}]"
    return type(data).__name__


def main(path: str) -> None:
    har = json.loads(Path(path).read_text(encoding="utf-8"))
    groups: dict = defaultdict(lambda: {"statuses": defaultdict(int), "auth": set(), "shape": "", "count": 0})
    for e in har["log"]["entries"]:
        req, res = e["request"], e["response"]
        mime = (res.get("content", {}).get("mimeType") or "").lower()
        rtype = e.get("_resourceType", "")
        u = urlsplit(req["url"])
        if any(n in u.netloc for n in NOISE):
            continue
        if rtype not in ("xhr", "fetch") and "json" not in mime:
            continue
        key = (req["method"], u.netloc, template(u.path))
        g = groups[key]
        g["count"] += 1
        g["statuses"][res["status"]] += 1
        g["auth"] |= {h["name"].lower() for h in req["headers"] if h["name"].lower() in AUTH_HEADERS}
        if not g["shape"] and res["status"] < 400:
            g["shape"] = shape(res.get("content", {}).get("text"))
    rows = sorted(groups.items(), key=lambda kv: (kv[0][1], kv[0][2], kv[0][0]))
    lines = ["# Endpoints observed in the browser (generated)", "",
             f"Source: `{Path(path).name}`, {len(rows)} distinct calls. Header names only, no values.", "",
             "| Method | Host | Path | Statuses | Auth sent via | Response shape | Calls |", "|---|---|---|---|---|---|---|"]
    for (method, host, p), g in rows:
        st = ", ".join(f"{k}×{v}" for k, v in sorted(g["statuses"].items()))
        lines.append(f"| {method} | {host} | `{p}` | {st} | {', '.join(sorted(g['auth'])) or '—'} | "
                     f"{g['shape'].replace('|', '/')} | {g['count']} |")
    out = Path(__file__).resolve().parents[1] / "ENDPOINTS.generated.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\n→ written to {out.name}. Paste this table to Claude.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "api-tests/har/journey.har")
