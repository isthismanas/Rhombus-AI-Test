"""S3 (input) and GCS (output) access. Cloud SDKs are imported lazily so offline use needs neither."""
from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from .config import REPO, UPLOADS_LOG, env, fmt_ms, now_local

TS_RE = re.compile(r"(\d{13})")


# ------------------------------------------------------------------ GCS
@dataclass
class OutputObject:
    name: str
    ts_ms: int          # timestamp Rhombus appended to the name (ms), else object creation time
    size: int
    created_ms: int

    @property
    def local_time(self) -> str:
        return fmt_ms(self.ts_ms)


def _gcs_bucket():
    from google.cloud import storage  # lazy

    client = storage.Client(project=env("GCP_PROJECT_ID"))
    return client.bucket(env("GCS_BUCKET", required=True))


def list_outputs(prefix: str | None = None) -> list[OutputObject]:
    prefix = prefix if prefix is not None else env("GCS_OUTPUT_PREFIX", "orders_clean")
    objs = []
    for b in _gcs_bucket().client.list_blobs(env("GCS_BUCKET", required=True)):
        if prefix and not b.name.startswith(prefix):
            continue
        created = int(b.time_created.timestamp() * 1000)
        m = TS_RE.search(b.name)
        objs.append(OutputObject(b.name, int(m.group(1)) if m else created, int(b.size or 0), created))
    return sorted(objs, key=lambda o: o.ts_ms, reverse=True)


def list_all_names() -> list[str]:
    return [b.name for b in _gcs_bucket().client.list_blobs(env("GCS_BUCKET", required=True))]


def download_output(name: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    _gcs_bucket().blob(name).download_to_filename(str(dest))
    return dest


# ------------------------------------------------------------------ S3
def _s3():
    import boto3  # lazy

    session = boto3.Session(profile_name=env("AWS_PROFILE") or None, region_name=env("AWS_REGION"))
    return session.client("s3")


def upload_case(case: str, local: Path) -> dict:
    bucket, key = env("S3_BUCKET", required=True), env("S3_KEY", "pipeline/orders.csv")
    body = local.read_bytes()
    resp = _s3().put_object(Bucket=bucket, Key=key, Body=body, ContentType="text/csv")
    md5 = hashlib.md5(body).hexdigest()
    etag = resp.get("ETag", "").strip('"')
    now = now_local()
    row = {
        "uploaded_at_local": now.isoformat(timespec="seconds"),
        "uploaded_at_ms": int(now.timestamp() * 1000),
        "case": case,
        "file": str(local.resolve().relative_to(REPO)),
        "sha256": hashlib.sha256(body).hexdigest(),
        "s3_uri": f"s3://{bucket}/{key}",
        "s3_version_id": resp.get("VersionId", ""),
        "etag_matches_md5": etag == md5,
    }
    log_upload(row)
    return row


def head_input() -> dict:
    bucket, key = env("S3_BUCKET", required=True), env("S3_KEY", "pipeline/orders.csv")
    h = _s3().head_object(Bucket=bucket, Key=key)
    return {"etag": h["ETag"].strip('"'), "version_id": h.get("VersionId", ""),
            "last_modified": h["LastModified"].isoformat()}


# ------------------------------------------------------------------ uploads log
FIELDS = ["uploaded_at_local", "uploaded_at_ms", "case", "file", "sha256", "s3_uri", "s3_version_id",
          "etag_matches_md5"]


def log_upload(row: dict) -> None:
    UPLOADS_LOG.parent.mkdir(parents=True, exist_ok=True)
    new = not UPLOADS_LOG.exists()
    with UPLOADS_LOG.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)


def uploads() -> list[dict]:
    if not UPLOADS_LOG.exists():
        return []
    with UPLOADS_LOG.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def last_upload(before_ms: int | None = None) -> dict | None:
    rows = [r for r in uploads() if before_ms is None or int(r["uploaded_at_ms"]) <= before_ms]
    return rows[-1] if rows else None
