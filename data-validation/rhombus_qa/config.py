"""Paths, environment and static configuration (contract, manifest)."""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

REPO = Path(__file__).resolve().parents[2]
DATASETS = REPO / "datasets"
VALIDATION = REPO / "data-validation"
RESULTS = REPO / "results"
REFERENCE_DIR = VALIDATION / "reference"
UPLOADS_LOG = RESULTS / "uploads.csv"
LOCAL_TZ = ZoneInfo("Australia/Adelaide")

try:  # .env is optional (unit tests don't need it)
    from dotenv import load_dotenv

    load_dotenv(REPO / ".env")
except ImportError:  # pragma: no cover
    pass


def env(name: str, default: str | None = None, required: bool = False) -> str | None:
    value = os.environ.get(name, default)
    if required and not value:
        raise SystemExit(f"Missing {name}. Set it in .env (see .env.example).")
    return value


@lru_cache
def contract() -> dict:
    return yaml.safe_load((VALIDATION / "contract.yaml").read_text(encoding="utf-8"))


@lru_cache
def manifest() -> dict:
    return json.loads((DATASETS / "manifest.json").read_text(encoding="utf-8"))


def case_meta(case: str) -> dict:
    cases = manifest()["cases"]
    if case not in cases:
        raise SystemExit(f"Unknown case '{case}'. Known: {', '.join(cases)}")
    return cases[case]


def case_input_path(case: str) -> Path:
    return REPO / case_meta(case)["file"]


def expected_clean_path() -> Path:
    return DATASETS / "baseline" / "expected_clean.csv"


def now_local() -> datetime:
    return datetime.now(UTC).astimezone(LOCAL_TZ)


def fmt_ms(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, UTC).astimezone(LOCAL_TZ).isoformat(timespec="seconds")
