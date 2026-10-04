#!/usr/bin/env python3
"""Open a logged-in browser that records all network traffic to api-tests/har/journey.har (gitignored).

  make har

Click through the whole journey (project → canvas → Run Pipeline → Schedule tab → Data → Sources), then press
Enter in the Terminal. Then run `make endpoints` to list the backend calls it captured.
The HAR contains auth tokens, so it is never committed.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "data-validation"))
from rhombus_qa import config  # noqa: E402,F401  (loads .env)

STATE = REPO / os.environ.get("RHOMBUS_STORAGE_STATE", ".auth/state.json")
BASE = os.environ.get("RHOMBUS_BASE_URL", "https://rhombusai.com/")
HAR = REPO / "api-tests" / "har" / "journey.har"


def main() -> None:
    if not STATE.exists():
        sys.exit("No login state. Run `make auth` first.")
    HAR.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=str(STATE), viewport={"width": 1440, "height": 900},
                                      record_har_path=str(HAR), record_har_content="embed")
        page = context.new_page()
        page.goto(BASE)
        print("\n👉 Recording. In the browser: open project rhombus-qa-etl → look at the canvas → click a node →")
        print("   Run Pipeline (wait for it to finish) → Schedule tab → Data → Sources → open the S3 source.")
        input("   When done, press Enter here (don't close the browser yourself)… ")
        context.close()  # flushes the HAR
        browser.close()
    print(f"\n✅ Saved {HAR.relative_to(REPO)}. Now run: make endpoints\n")


if __name__ == "__main__":
    main()
