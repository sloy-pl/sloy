#!/usr/bin/env python3
"""Build a Shopify product-import CSV for the 21 new products that have
photos in Drive, from the Opisy descriptions CSV + sku_images.json
(produced by mapping gdrive/list_files.py output to SKUs).

Usage: python3 build_csv.py
"""
import csv
import json
import os
import re
import unicodedata

ROOT = os.path.dirname(os.path.abspath(__file__))
OPISY_CSV = "/Users/marcinwosinek/Downloads/Opisy produktów na www - Opisy EN.csv"
REFERENCE_CSV = "/Users/marcinwosinek/Downloads/products_export_1.csv"
PRICES_CSV = "/Users/marcinwosinek/Downloads/SLOY_ Ceny - Ceny.csv"
SKU_IMAGES_JSON = os.path.join(ROOT, "sku_images.json")
OUT_CSV = os.path.join(ROOT, "products_import.csv")

METAFIELD_MAP = {
    "Key features": "Key features (product.metafields.custom.key_features)",
    "Condition": "Condition (product.metafields.custom.condition)",
    "Dimensions": "Dimensions (product.metafields.custom.dimensions)",
    "Perfect for": "Perfect for (product.metafields.custom.perfect_for)",
    "Shipping & pickup": "Shipping & pickup (product.metafields.custom.shipping_pickup)",
    "SLOY quality standard": "SLOY quality standard (product.metafields.custom.sloy_quality_standard)",
    "Designer": "Designer (product.metafields.custom.designer)",
    "Manufacturer": "Manufacturer (product.metafields.custom.manufacturer)",
}


POLISH_MAP = str.maketrans({
    "ł": "l", "Ł": "L", "ż": "z", "Ż": "Z", "ź": "z", "Ź": "Z",
})


def slugify(title):
    text = title.translate(POLISH_MAP)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def drive_url(file_id):
    return f"https://drive.google.com/uc?export=view&id={file_id}"


def body_html(description, more_info):
    paras = [p.strip() for p in description.split("\n\n") if p.strip()]
    html = "".join(f"<p>{p}</p>" for p in paras)
    if more_info and more_info.strip():
        html += f"<p>{more_info.strip()}</p>"
    return html


def main():
    with open(REFERENCE_CSV, newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))

    with open(SKU_IMAGES_JSON, encoding="utf-8") as f:
        sku_images = json.load(f)

    with open(PRICES_CSV, newline="", encoding="utf-8") as f:
        price_rows = list(csv.reader(f))
    prices = {r[0].strip(): r[1].strip() for r in price_rows[1:] if r and r[0].strip()}

    with open(OPISY_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    products = []
    for row in rows[1:]:
        sku = row[0].strip()
        if not sku:
            continue  # skip the SKU-less example row
        (
            _sku, title, description, key_features, condition, dimensions,
            perfect_for, shipping_pickup, quality_standard, designer,
            manufacturer, more_info,
        ) = row
        products.append({
            "sku": sku,
            "title": title.strip(),
            "handle": slugify(title.strip()),
            "body_html": body_html(description, more_info),
            "key_features": key_features,
            "condition": condition,
            "dimensions": dimensions,
            "perfect_for": perfect_for,
            "shipping_pickup": shipping_pickup,
            "quality_standard": quality_standard,
            "designer": designer,
            "manufacturer": manufacturer,
            "images": sku_images.get(sku, [])[:1],
            "price": prices.get(sku, ""),
        })

    handles = [p["handle"] for p in products]
    assert len(handles) == len(set(handles)), "duplicate handles!"

    out_rows = []
    for p in products:
        base = {col: "" for col in header}
        base["Handle"] = p["handle"]
        base["Title"] = p["title"]
        base["Body (HTML)"] = p["body_html"]
        is_ready = bool(p["price"]) and bool(p["images"])
        base["Published"] = "true" if is_ready else "false"
        base["Option1 Name"] = "Title"
        base["Option1 Value"] = "Default Title"
        base["Variant SKU"] = p["sku"]
        base["Variant Grams"] = "0"
        base["Variant Inventory Tracker"] = "shopify"
        base["Variant Inventory Qty"] = "0"
        base["Variant Inventory Policy"] = "deny"
        base["Variant Fulfillment Service"] = "manual"
        base["Variant Price"] = p["price"]
        base["Variant Requires Shipping"] = "true"
        base["Variant Taxable"] = "true"
        base["Gift Card"] = "false"
        base["Status"] = "active" if is_ready else "draft"
        base[METAFIELD_MAP["Key features"]] = p["key_features"]
        base[METAFIELD_MAP["Condition"]] = p["condition"]
        base[METAFIELD_MAP["Dimensions"]] = p["dimensions"]
        base[METAFIELD_MAP["Perfect for"]] = p["perfect_for"]
        base[METAFIELD_MAP["Shipping & pickup"]] = p["shipping_pickup"]
        base[METAFIELD_MAP["SLOY quality standard"]] = p["quality_standard"]
        base[METAFIELD_MAP["Designer"]] = p["designer"]
        base[METAFIELD_MAP["Manufacturer"]] = p["manufacturer"]

        if not p["images"]:
            out_rows.append(base)
        for i, img in enumerate(p["images"], start=1):
            if i == 1:
                row = dict(base)
            else:
                row = {col: "" for col in header}
                row["Handle"] = p["handle"]
            row["Image Src"] = drive_url(img["id"])
            row["Image Position"] = str(i)
            out_rows.append(row)

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"Wrote {len(out_rows)} rows for {len(products)} products -> {OUT_CSV}")
    for p in products:
        price = p["price"] or "MISSING"
        imgs = "no image" if not p["images"] else "1 image "
        print(f"  {p['sku']:10s} {imgs}  {price:>8s} PLN  {p['title']}")


if __name__ == "__main__":
    main()
