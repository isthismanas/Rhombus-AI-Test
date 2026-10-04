#!/usr/bin/env python3
"""Upload a case's dataset to the single S3 key the Rhombus pipeline reads, and log it.

  python scripts/upload.py --case S2        (or: make upload CASE=S2)

Every drift case overwrites the same key (S3_KEY, default pipeline/orders.csv). Bucket versioning keeps each
version, and results/uploads.csv records which case was in S3 when. The validator uses that log to prove which
input a given GCS output was produced from (check INP-01).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data-validation"))

from rhombus_qa import config  # noqa: E402
from rhombus_qa.io_cloud import upload_case  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--case", required=True, help=f"one of: {', '.join(config.manifest()['cases'])}")
    a = p.parse_args()
    path = config.case_input_path(a.case)
    row = upload_case(a.case, path)
    print(f"\n✅ Uploaded {row['file']}  →  {row['s3_uri']}")
    print(f"   case:        {a.case}  ({config.case_meta(a.case)['description']})")
    print(f"   time:        {row['uploaded_at_local']}")
    print(f"   version id:  {row['s3_version_id'] or '(versioning is OFF: enable it on the bucket)'}")
    print(f"   integrity:   {'ETag matches local MD5' if row['etag_matches_md5'] else 'ETag differs (check!)'}")
    print("   logged in:   results/uploads.csv\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
