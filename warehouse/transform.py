#!/usr/bin/env python3
"""Transform the Airtable sales ledger into WooCommerce product payloads.
Output: data/products.json  (one object per row, ready for the WC REST API)."""
import csv, json, os, re

ROOT = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
COST_COL = "Suma kosztów (zakup + transport)"

CATEGORIES = {
    "SER": "Zastawa i serwowanie",
    "LMP": "Lampy i oświetlenie",
    "MEB": "Meble",
    "AKC": "Akcesoria",
    "DEK": "Dekoracje",
}

def clean(v):
    v = (v or "").strip()
    return "" if v.upper() in ("", "N/A", "NA") else v

def parse_cost(v):
    v = (v or "").strip()
    m = re.search(r"([\d ]+,\d+|\d+)", v.replace("PLN", ""))
    if not m:
        return ""
    return m.group(1).replace(" ", "").replace(",", ".")

def stock_status(s):
    return "instock" if s.strip() == "Dostępne" else "outofstock"

def build_name(row):
    parts = [clean(row["Producent"]), clean(row["Model"])]
    typ = clean(row["Typ produktu"])
    prefix = " ".join(p for p in parts if p)
    if prefix and typ and typ.lower() not in prefix.lower():
        return f"{prefix} – {typ}"
    return prefix or typ or row["SKU"]

# image map: SKU -> filename
img_map = {}
imap_path = os.path.join(ROOT, "data/image_map.csv")
if os.path.exists(imap_path):
    with open(imap_path, encoding="utf-8") as f:
        for x in csv.DictReader(f):
            if x["status"] == "ok":
                img_map[x["SKU"]] = x["filename"]

products = []
with open(os.path.join(ROOT, "data/sales.csv"), encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        sku = row["SKU"].strip()
        if not sku:
            continue
        prefix = sku.split("-")[0]
        cost = parse_cost(row[COST_COL])
        meta = {
            "_warehouse_cost_pln": cost,
            "_warehouse_origin": clean(row["Pochodzenie"]),
            "_warehouse_airtable_status": row["Status"].strip(),
            "_warehouse_typ": clean(row["Typ produktu"]),
            "_warehouse_producent": clean(row["Producent"]),
            "_warehouse_model": clean(row["Model"]),
        }
        products.append({
            "sku": sku,
            "name": build_name(row),
            "status": "draft",
            "catalog_visibility": "hidden",
            "regular_price": "",
            "manage_stock": False,
            "stock_status": stock_status(row["Status"]),
            "category": CATEGORIES.get(prefix, "Pozostałe"),
            "description": clean(row["Typ produktu"]),
            "image_file": img_map.get(sku, ""),
            "meta_data": [{"key": k, "value": v} for k, v in meta.items() if v],
        })

with open(os.path.join(ROOT, "data/products.json"), "w", encoding="utf-8") as f:
    json.dump(products, f, ensure_ascii=False, indent=2)

with_img = sum(1 for p in products if p["image_file"])
instock = sum(1 for p in products if p["stock_status"] == "instock")
print(f"{len(products)} products -> data/products.json")
print(f"  with image: {with_img} | instock: {instock} | draft: all")
from collections import Counter
print("  categories:", dict(Counter(p["category"] for p in products)))
