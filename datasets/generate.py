#!/usr/bin/env python3
"""Seeded generator for the baseline messy dataset and every drifted version.

Run:  python datasets/generate.py

Every defect is injected deliberately, on known rows, in exact counts. Outputs:

  datasets/baseline/orders.csv            messy input uploaded to S3
  datasets/baseline/expected_clean.csv    ground truth: what a correct pipeline must output
                                          (built from the clean truth table, NOT from the oracle,
                                          so the two can cross-check each other)
  datasets/probe/orders-extra-row.csv     baseline + 1 valid row (does a run re-read S3?)
  datasets/schema/S1..S5-*.csv            schema drift files
  datasets/semantic/M1..M3-*.csv          semantic drift files
  datasets/manifest.json                  counts, hashes, descriptions for every file
  datasets/DATA_DICTIONARY.md             human-readable version of the above

Re-running produces byte-identical files (checked in CI).
"""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np

SEED = 42
N_ORDERS = 500
FIRST_ORDER_ID = 1001
ROOT = Path(__file__).resolve().parent

COLUMNS = [
    "order_id", "customer_name", "email", "country", "order_date",
    "product", "category", "quantity", "unit_price", "status",
]

FIRST_NAMES = [
    "Priya", "Arjun", "Olivia", "Liam", "Aanya", "Noah", "Mia", "Ethan", "Zara", "Lucas",
    "Isla", "Rohan", "Grace", "Kabir", "Chloe", "Ryan", "Meera", "Jack", "Sofia", "Daniel",
    "Ava", "Vikram", "Emily", "Samuel", "Ananya", "Harper", "Leo", "Nina", "Oscar", "Tara",
]
LAST_NAMES = [
    "Sharma", "Patel", "Smith", "Nguyen", "Brown", "Williams", "Jones", "Singh", "Taylor", "Wilson",
    "Kumar", "Martin", "Anderson", "Thomas", "White", "Harris", "Clark", "Lewis", "Walker", "Hall",
    "Allen", "Young", "King", "Wright", "Scott", "Green", "Baker", "Adams", "Nelson", "Carter",
]
DOMAINS = ["example.com", "mail.com", "shopper.net", "inbox.org"]

COUNTRIES = ["Australia", "United States", "United Kingdom", "India", "New Zealand"]
COUNTRY_WEIGHTS = [0.35, 0.25, 0.15, 0.15, 0.10]
COUNTRY_VARIANTS = {  # messy spellings, all covered by the cleaning prompt (case-insensitive, trimmed)
    "United States": ["USA", "usa", "U.S.", "US", " united states ", "United states"],
    "United Kingdom": ["UK", "u.k.", "U.K.", " united kingdom", "United kingdom"],
    "Australia": ["Aus", "AU", "australia", "AUSTRALIA "],
    "India": ["india ", "INDIA", " India"],
    "New Zealand": ["NZ", "nz", "new zealand"],
}
ISO2 = {"Australia": "AU", "United States": "US", "United Kingdom": "GB", "India": "IN", "New Zealand": "NZ"}

CATALOG = [  # (product, category, base price USD)
    ("Wireless Mouse", "Electronics", 24.99), ("Mechanical Keyboard", "Electronics", 89.00),
    ("USB-C Hub", "Electronics", 39.50), ("27in Monitor", "Electronics", 329.00),
    ("Noise Cancelling Headphones", "Electronics", 249.00), ("Laptop Stand", "Electronics", 45.00),
    ("Desk Lamp", "Home", 32.00), ("Ceramic Mug Set", "Home", 19.95), ("Throw Blanket", "Home", 54.00),
    ("Air Purifier", "Home", 189.00), ("Python Crash Course", "Books", 34.99),
    ("Data Science Handbook", "Books", 49.99), ("Sci-Fi Anthology", "Books", 18.50),
    ("Yoga Mat", "Sports", 29.00), ("Running Shoes", "Sports", 129.00), ("Tennis Racket", "Sports", 159.00),
    ("Dumbbell Set", "Sports", 99.00), ("Denim Jacket", "Fashion", 79.00), ("Leather Wallet", "Fashion", 45.00),
    ("Wool Scarf", "Fashion", 27.50), ("Sunglasses", "Fashion", 65.00), ("Smart Watch", "Electronics", 1299.00),
]
STATUSES = ["pending", "shipped", "delivered", "cancelled"]
STATUS_WEIGHTS = [0.15, 0.30, 0.45, 0.10]
DATE_START, DATE_END = date(2026, 1, 1), date(2026, 6, 30)

# defect counts (rows are disjoint per defect so counts stay exact)
INVALID = {"quantity_le_zero": 8, "unit_price_negative": 5, "order_date_impossible": 3, "status_not_allowed": 4}
MISSING = {"quantity": 20, "unit_price": 21, "email": 15, "country": 10, "customer_name": 5}
MALFORMED_EMAIL = 8
ISO_DATES = 20
FORMATTING = {"country_variant": 60, "customer_name_messy": 40, "status_case": 30, "email_upper": 15,
              "product_whitespace": 10}
EXACT_DUPLICATES = 15
NEAR_DUPLICATES = 10

BAD_DATES = ["02/30/2026", "13/45/2026", "00/12/2026"]
BAD_STATUSES = ["unknown", "???", "on hold", "lost"]
BAD_QUANTITIES = ["0", "0", "0", "0", "-1", "-2", "-3", "-5"]


def _mdy(d: date) -> str:
    return f"{d.month:02d}/{d.day:02d}/{d.year}"


def _dmy(d: date) -> str:
    return f"{d.day:02d}/{d.month:02d}/{d.year}"


def _messy_name(rng: np.random.Generator, name: str) -> str:
    first, last = name.split(" ")
    style = int(rng.integers(0, 5))
    if style == 0:
        return name.upper()
    if style == 1:
        return name.lower()
    if style == 2:
        return f"  {first}   {last} "
    if style == 3:
        return f"{first.lower()}  {last.upper()}"
    return f" {first} {last}  "


def build_truth(rng: np.random.Generator) -> list[dict]:
    """Clean, typed ground-truth orders."""
    days = (DATE_END - DATE_START).days
    rows = []
    for i in range(N_ORDERS):
        first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
        product, category, base = CATALOG[int(rng.integers(0, len(CATALOG)))]
        price = round(float(base) * float(rng.uniform(0.9, 1.1)), 2)
        rows.append({
            "order_id": FIRST_ORDER_ID + i,
            "customer_name": f"{first} {last}",
            "email": f"{first.lower()}.{last.lower()}{int(rng.integers(1, 100))}@{rng.choice(DOMAINS)}",
            "country": str(rng.choice(COUNTRIES, p=COUNTRY_WEIGHTS)),
            "order_date": DATE_START + timedelta(days=int(rng.integers(0, days + 1))),
            "product": product,
            "category": category,
            "quantity": int(rng.choice([1, 1, 1, 2, 2, 2, 3, 3, 4, 5, 6, 8, 10, 12, 20])),
            "unit_price": min(max(price, 1.00), 1999.99),
            "status": str(rng.choice(STATUSES, p=STATUS_WEIGHTS)),
        })
    return rows


def to_messy_strings(t: dict) -> dict:
    return {
        "order_id": str(t["order_id"]),
        "customer_name": t["customer_name"],
        "email": t["email"],
        "country": t["country"],
        "order_date": _mdy(t["order_date"]),
        "product": t["product"],
        "category": t["category"],
        "quantity": str(t["quantity"]),
        "unit_price": f"{t['unit_price']:.2f}",
        "status": t["status"],
    }


def generate() -> dict:
    rng = np.random.default_rng(SEED)
    truth = build_truth(rng)
    messy = [to_messy_strings(t) for t in truth]

    # ---- allocate disjoint row slices for row-affecting defects ----
    perm = [int(x) for x in rng.permutation(N_ORDERS)]
    cursor = 0

    def take(n: int) -> list[int]:
        nonlocal cursor
        out = perm[cursor:cursor + n]
        cursor += n
        return out

    slices = {}
    for k, n in INVALID.items():
        slices[f"invalid:{k}"] = take(n)
    for k, n in MISSING.items():
        slices[f"missing:{k}"] = take(n)
    slices["malformed_email"] = take(MALFORMED_EMAIL)
    slices["iso_date"] = take(ISO_DATES)
    clean_pool = perm[cursor:]  # rows with no row-level defect

    invalid_rows = set()
    for i, v in zip(slices["invalid:quantity_le_zero"], BAD_QUANTITIES, strict=False):
        messy[i]["quantity"] = v
        invalid_rows.add(i)
    for i in slices["invalid:unit_price_negative"]:
        messy[i]["unit_price"] = f"-{truth[i]['unit_price']:.2f}"
        invalid_rows.add(i)
    for i, v in zip(slices["invalid:order_date_impossible"], BAD_DATES, strict=False):
        messy[i]["order_date"] = v
        invalid_rows.add(i)
    for i, v in zip(slices["invalid:status_not_allowed"], BAD_STATUSES, strict=False):
        messy[i]["status"] = v
        invalid_rows.add(i)
    for col in MISSING:
        for i in slices[f"missing:{col}"]:
            messy[i][col] = ""
    for i in slices["malformed_email"]:
        messy[i]["email"] = truth[i]["email"].replace("@", "")
    for i in slices["iso_date"]:
        messy[i]["order_date"] = truth[i]["order_date"].isoformat()

    # ---- formatting defects (do not change row counts) ----
    def pick(n: int) -> list[int]:
        return [int(x) for x in rng.choice(clean_pool, size=n, replace=False)]

    for i in pick(FORMATTING["country_variant"]):
        messy[i]["country"] = str(rng.choice(COUNTRY_VARIANTS[truth[i]["country"]]))
    for i in pick(FORMATTING["customer_name_messy"]):
        messy[i]["customer_name"] = _messy_name(rng, truth[i]["customer_name"])
    for i in pick(FORMATTING["status_case"]):
        s = truth[i]["status"]
        messy[i]["status"] = s.upper() if rng.random() < 0.5 else s.capitalize()
    for i in pick(FORMATTING["email_upper"]):
        messy[i]["email"] = truth[i]["email"].upper()
    for i in pick(FORMATTING["product_whitespace"]):
        messy[i]["product"] = f" {truth[i]['product']}  "

    # ---- shuffle row order (so the Sort rule matters), then insert duplicates ----
    order = [int(x) for x in rng.permutation(N_ORDERS)]
    rows = [dict(messy[i]) for i in order]
    pos_of = {order[p]: p for p in range(N_ORDERS)}

    dup_sources = [int(x) for x in rng.choice(clean_pool, size=EXACT_DUPLICATES + NEAR_DUPLICATES, replace=False)]
    exact_src, near_src = dup_sources[:EXACT_DUPLICATES], dup_sources[EXACT_DUPLICATES:]
    inserts = []  # (insert_after_position, row)
    for i in exact_src:
        inserts.append((pos_of[i], dict(messy[i])))
    for i in near_src:
        r = dict(messy[i])
        r["customer_name"] = _messy_name(rng, truth[i]["customer_name"])
        r["status"] = truth[i]["status"].upper()
        r["country"] = str(rng.choice(COUNTRY_VARIANTS[truth[i]["country"]]))
        inserts.append((pos_of[i], r))
    # place each duplicate somewhere AFTER its original (so "keep first" keeps the original)
    placed = []
    for after, r in inserts:
        at = int(rng.integers(after + 1, N_ORDERS + 1))
        placed.append((at, r))
    for at, r in sorted(placed, key=lambda x: x[0], reverse=True):
        rows.insert(at, r)

    # ---- ground truth expected output ----
    expected = build_expected(truth, invalid_rows, slices)

    return {"rows": rows, "expected": expected, "truth": truth, "slices": slices,
            "invalid_rows": invalid_rows}


def build_expected(truth: list[dict], invalid_rows: set[int], slices: dict) -> list[dict]:
    keep = [i for i in range(N_ORDERS) if i not in invalid_rows]
    miss_q, miss_p = set(slices["missing:quantity"]), set(slices["missing:unit_price"])
    med_q = float(np.median([truth[i]["quantity"] for i in keep if i not in miss_q]))
    med_p = round(float(np.median([truth[i]["unit_price"] for i in keep if i not in miss_p])), 2)
    out = []
    for i in keep:
        t = dict(truth[i])
        if i in miss_q:
            t["quantity"] = int(round(med_q))
        if i in miss_p:
            t["unit_price"] = med_p
        if i in set(slices["missing:email"]) or i in set(slices["malformed_email"]):
            t["email"] = ""
        if i in set(slices["missing:country"]):
            t["country"] = "Unknown"
        if i in set(slices["missing:customer_name"]):
            t["customer_name"] = "Unknown"
        out.append(t)
    out.sort(key=lambda t: t["order_id"])
    build_expected.medians = {"quantity": med_q, "unit_price": med_p}
    return [{
        "order_id": str(t["order_id"]), "customer_name": t["customer_name"], "email": t["email"],
        "country": t["country"], "order_date": t["order_date"].isoformat(), "product": t["product"],
        "category": t["category"], "quantity": str(t["quantity"]), "unit_price": f"{t['unit_price']:.2f}",
        "status": t["status"],
    } for t in out]


# ---------------------------------------------------------------- drift transforms
def drift_s1(rows):  # drop a column the pipeline uses
    return [{k: v for k, v in r.items() if k != "country"} for r in rows]


def drift_s2(rows):  # rename a column
    return [{("customer_full_name" if k == "customer_name" else k): v for k, v in r.items()} for r in rows]


def _currency(v: str) -> str:
    if v == "":
        return ""
    x = float(v)
    s = f"${abs(x):,.2f}"
    return f"-{s}" if x < 0 else s


def drift_s3(rows):  # numeric -> currency-formatted text
    return [{**r, "unit_price": _currency(r["unit_price"])} for r in rows]


def drift_s4(rows, rng):  # add a column mid-row
    codes = ["SAVE10", "WELCOME5", "SPRING15", "VIP20"]
    per_order: dict[str, str] = {}  # one code per order, so duplicate rows stay duplicates (as in a real export)
    out = []
    for r in rows:
        oid = r["order_id"]
        if oid not in per_order:
            per_order[oid] = str(rng.choice(codes)) if rng.random() < 0.3 else ""
        new = {}
        for k, v in r.items():
            new[k] = v
            if k == "product":
                new["discount_code"] = per_order[oid]
        out.append(new)
    return out


def drift_s5(rows, rng):
    return drift_s4(drift_s3(drift_s2(drift_s1(rows))), rng)


def drift_m1(rows):  # dollars -> integer cents, same column, still numeric
    def cents(v):
        return "" if v == "" else str(int(round(float(v) * 100)))
    return [{**r, "unit_price": cents(r["unit_price"])} for r in rows]


def drift_m2(rows):  # MM/DD/YYYY -> DD/MM/YYYY (ISO rows and impossible dates untouched)
    out = []
    for r in rows:
        v = r["order_date"]
        parts = v.split("/")
        if len(parts) == 3 and v not in BAD_DATES:
            m, d, y = (int(p) for p in parts)
            v = _dmy(date(y, m, d))
        out.append({**r, "order_date": v})
    return out


def drift_m3(rows):  # canonical/messy country names -> ISO-3166 alpha-2 codes
    lookup = {}
    for canon, variants in COUNTRY_VARIANTS.items():
        for v in variants + [canon]:
            lookup[v.strip().lower()] = ISO2[canon]
    return [{**r, "country": (lookup[r["country"].strip().lower()] if r["country"] else "")} for r in rows]


# ---------------------------------------------------------------- writing
def write_csv(path: Path, rows: list[dict]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    g = generate()
    rows, expected = g["rows"], g["expected"]
    rng = np.random.default_rng(SEED + 1)  # separate stream for drift randomness

    probe_extra = {
        "order_id": "1501", "customer_name": "Probe Tester", "email": "probe.tester1@example.com",
        "country": "Australia", "order_date": "06/15/2026", "product": "Desk Lamp", "category": "Home",
        "quantity": "1", "unit_price": "32.00", "status": "delivered",
    }
    files = {
        "baseline": ("baseline/orders.csv", rows, "Messy baseline uploaded to S3."),
        "probe-extra-row": ("probe/orders-extra-row.csv", rows + [probe_extra],
                            "Baseline + one valid order (1501). Used to prove a run re-reads the S3 object."),
        "S1": ("schema/S1-drop-column.csv", drift_s1(rows), "Schema drift: column `country` removed."),
        "S2": ("schema/S2-rename-column.csv", drift_s2(rows),
               "Schema drift: `customer_name` renamed to `customer_full_name`."),
        "S3": ("schema/S3-change-data-type.csv", drift_s3(rows),
               "Schema drift: `unit_price` numeric → currency text like `$1,249.50`."),
        "S4": ("schema/S4-add-column.csv", drift_s4(rows, rng),
               "Schema drift: new column `discount_code` inserted between `product` and `category`."),
        "S5": ("schema/S5-combined.csv", drift_s5(rows, rng), "Schema drift: S1 + S2 + S3 + S4 combined."),
        "M1": ("semantic/M1-dollars-to-cents.csv", drift_m1(rows),
               "Semantic drift: `unit_price` in integer cents instead of dollars (×100)."),
        "M2": ("semantic/M2-date-mmdd-to-ddmm.csv", drift_m2(rows),
               "Semantic drift: `order_date` written DD/MM/YYYY instead of MM/DD/YYYY (ISO rows unchanged)."),
        "M3": ("semantic/M3-country-iso-codes.csv", drift_m3(rows),
               "Semantic drift (optional): `country` as ISO-3166 alpha-2 codes (AU, US, GB, IN, NZ)."),
    }

    manifest = {"seed": SEED, "generated_by": "datasets/generate.py", "cases": {}}
    exp_sha = write_csv(ROOT / "baseline/expected_clean.csv", expected)
    n_expected = len(expected)
    for case, (rel, data, desc) in files.items():
        sha = write_csv(ROOT / rel, data)
        manifest["cases"][case] = {
            "file": f"datasets/{rel}",
            "description": desc,
            "rows_in": len(data),
            "columns": list(data[0].keys()),
            "sha256": sha,
            # what a pipeline that handled the drift correctly would output
            "expected_rows_out": n_expected + (1 if case == "probe-extra-row" else 0),
        }

    # M2: how many valid orders have day > 12 (impossible as MM/DD) vs day <= 12 (silently wrong)
    keep = [t for i, t in enumerate(g["truth"]) if i not in g["invalid_rows"]
            and i not in set(g["slices"]["iso_date"])]
    manifest["cases"]["M2"]["valid_mmdd_rows_day_gt_12"] = sum(1 for t in keep if t["order_date"].day > 12)
    manifest["cases"]["M2"]["valid_mmdd_rows_day_le_12"] = sum(1 for t in keep if t["order_date"].day <= 12)

    manifest["baseline_defects"] = {
        "rows_in": len(rows),
        "unique_orders": N_ORDERS,
        "duplicates": {"exact": EXACT_DUPLICATES, "near_after_normalisation": NEAR_DUPLICATES},
        "invalid_rows_dropped": INVALID,
        "missing_values": MISSING,
        "malformed_email_set_null": MALFORMED_EMAIL,
        "iso_formatted_dates": ISO_DATES,
        "formatting_defects": FORMATTING,
        "expected_rows_out": n_expected,
        "expected_rows_formula": f"{len(rows)} rows - {EXACT_DUPLICATES + NEAR_DUPLICATES} duplicates "
                                 f"- {sum(INVALID.values())} invalid = {n_expected}",
        "imputation_medians": build_expected.medians,
        "expected_clean_sha256": exp_sha,
    }
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    write_dictionary(manifest)
    print(f"baseline: {len(rows)} rows in -> {n_expected} expected out "
          f"(medians: quantity={build_expected.medians['quantity']}, "
          f"unit_price={build_expected.medians['unit_price']})")
    for case, meta in manifest["cases"].items():
        print(f"  {case:16s} {meta['rows_in']:4d} rows  {meta['file']}")


def write_dictionary(m: dict) -> None:
    d = m["baseline_defects"]
    lines = [
        "# Data dictionary",
        "",
        "> Generated by `datasets/generate.py` (seed 42). Do not edit by hand: re-run the generator.",
        "",
        "## Baseline schema (`baseline/orders.csv`)",
        "",
        "| Column | Meaning | Clean type / format | Units / allowed values |",
        "|---|---|---|---|",
        "| `order_id` | Business key, unique per order | integer | 1001–1500 |",
        "| `customer_name` | Customer full name | text, Title Case | — |",
        "| `email` | Customer email | text, lower case, nullable | must contain `@` |",
        "| `country` | Shipping country | categorical | Australia, United States, United Kingdom, India, "
        "New Zealand (`Unknown` if missing) |",
        "| `order_date` | Order date | date; **input MM/DD/YYYY** (some ISO), output YYYY-MM-DD | "
        "2026-01-01 … 2026-06-30 |",
        "| `product` | Product name | text | 22 products |",
        "| `category` | Product category | categorical | Electronics, Home, Books, Sports, Fashion |",
        "| `quantity` | Units ordered | integer | 1–20 |",
        "| `unit_price` | Price per unit | decimal (2 dp) | **US dollars**, 1.00–1999.99 |",
        "| `status` | Order status | categorical, lower case | pending, shipped, delivered, cancelled |",
        "",
        "## Injected defects (baseline)",
        "",
        "Row-affecting defects sit on **disjoint rows**, so every count below is exact.",
        "",
        "| Class | Defect | Count | Expected cleaning action |",
        "|---|---|---|---|",
        f"| Duplicates | exact duplicate rows | {d['duplicates']['exact']} | remove (keep first) |",
        f"| Duplicates | near-duplicates (case/whitespace/country spelling only) | "
        f"{d['duplicates']['near_after_normalisation']} | identical after normalisation → remove |",
    ]
    for col, n in d["missing_values"].items():
        action = {"quantity": "impute median (integer)", "unit_price": "impute median (2 dp)",
                  "email": "leave empty", "country": "fill `Unknown`",
                  "customer_name": "fill `Unknown`"}[col]
        lines.append(f"| Missing values | `{col}` empty | {n} | {action} |")
    fm = d["formatting_defects"]
    lines += [
        f"| Inconsistent formatting | `country` spelling variants (USA, U.K., Aus, …) | "
        f"{fm['country_variant']} | map to canonical name |",
        f"| Inconsistent formatting | `customer_name` casing / extra spaces | {fm['customer_name_messy']} | "
        f"trim, collapse spaces, Title Case |",
        f"| Inconsistent formatting | `status` casing | {fm['status_case']} | lower case |",
        f"| Inconsistent formatting | `email` upper case | {fm['email_upper']} | lower case |",
        f"| Inconsistent formatting | `product` leading/trailing spaces | {fm['product_whitespace']} | trim |",
        f"| Inconsistent formatting | `order_date` in ISO `YYYY-MM-DD` | {d['iso_formatted_dates']} | parse, output ISO |",
    ]
    inv = d["invalid_rows_dropped"]
    lines += [
        f"| Invalid entries | `quantity` ≤ 0 | {inv['quantity_le_zero']} | drop row |",
        f"| Invalid entries | `unit_price` < 0 | {inv['unit_price_negative']} | drop row |",
        f"| Invalid entries | impossible `order_date` ({', '.join(BAD_DATES)}) | "
        f"{inv['order_date_impossible']} | drop row |",
        f"| Invalid entries | `status` not allowed ({', '.join(BAD_STATUSES)}) | {inv['status_not_allowed']} | drop row |",
        f"| Invalid entries | `email` without `@` | {d['malformed_email_set_null']} | set empty, keep row |",
        "",
        f"**Expected output rows:** {d['expected_rows_formula']}.",
        f"Imputation medians: quantity = {d['imputation_medians']['quantity']}, "
        f"unit_price = {d['imputation_medians']['unit_price']}.",
        "Ground truth: [`baseline/expected_clean.csv`](baseline/expected_clean.csv).",
        "",
        "## Drift files",
        "",
        "| Case | File | Change | Rows |",
        "|---|---|---|---|",
    ]
    for case, meta in m["cases"].items():
        if case == "baseline":
            continue
        lines.append(f"| {case} | [`{meta['file'].removeprefix('datasets/')}`]"
                     f"({meta['file'].removeprefix('datasets/')}) | {meta['description']} | {meta['rows_in']} |")
    m2 = m["cases"]["M2"]
    lines += [
        "",
        f"M2 detail: {m2['valid_mmdd_rows_day_gt_12']} valid MM/DD rows have day > 12 (impossible as a month "
        f"after the swap, so a loud failure), and {m2['valid_mmdd_rows_day_le_12']} have day ≤ 12 "
        f"(parse fine but give the wrong date, so a silent failure).",
        "",
    ]
    (ROOT / "DATA_DICTIONARY.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
