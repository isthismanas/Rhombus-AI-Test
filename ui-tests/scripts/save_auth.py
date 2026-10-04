#!/usr/bin/env python3
"""One-off manual login → saves Playwright storage state to .auth/state.json (gitignored).

  make auth

Login isn't automated on purpose: it may involve SSO, email codes or bot protection, and the tests shouldn't
try to get around those. Every UI and API test then reuses this saved, authenticated state.
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


def main() -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.goto(BASE)
        print("\n👉 A browser opened. Log in to Rhombus AI and wait until you see your projects.")
        input("   Then come back here and press Enter… ")
        context.storage_state(path=str(STATE))
        print(f"\n✅ Saved login state to {STATE.relative_to(REPO)}. Logged-in URL was: {page.url}")
        print("   Put that host in RHOMBUS_BASE_URL in .env if it differs from the current value.\n")
        browser.close()


if __name__ == "__main__":
    main()
