#!/usr/bin/env python3
"""Update the 'Shipping & pickup' metafield for products with known InPost/courier
shipping costs (from the packing-data sheet), replacing the generic "contact us"
line with the actual computed price.

Sets the English metafield value and registers a Polish translation for it
(the current PL text on the storefront is Shopify's live machine translation —
this registers a real one so the wording is exact).

Usage:
  python3 update_shipping_pickup.py --dry-run     # show what would change
  python3 update_shipping_pickup.py                # apply
"""
import argparse, json, sys

from sheet_to_shopify import Shopify, load_env

PICKUP_LINE_EN = "Free local pickup available (Kraków, Poland)"
PICKUP_LINE_PL = "Bezpłatny odbiór osobisty w Krakowie"

# sku -> (label_en, label_pl, price) ; price kept as the PL-formatted string (comma decimal)
SHIPPING_DATA = {
    "SER-179": ("InPost A", "InPost A", "18,34"),
    "AKC-136": ("InPost B", "InPost B", "20,34"),
    "AKC-151": ("InPost B", "InPost B", "20,34"),
    "AKC-221": ("InPost B", "InPost B", "20,34"),
    "AKC-222": ("InPost B", "InPost B", "20,34"),
    "AKC-223": ("InPost B", "InPost B", "20,34"),
    "DEK-100": ("InPost B", "InPost B", "20,34"),
    "DEK-148": ("InPost B", "InPost B", "20,34"),
    "DEK-192": ("InPost B", "InPost B", "20,34"),
    "SER-202": ("InPost B", "InPost B", "20,34"),
    "SER-211": ("InPost B", "InPost B", "20,34"),
    "SER-219": ("InPost B", "InPost B", "20,34"),
    "AKC-197": ("InPost C", "InPost C", "22,34"),
    "AKC-201": ("InPost C", "InPost C", "22,34"),
    "DEK-133": ("InPost C", "InPost C", "22,34"),
    "LMP-037": ("InPost C", "InPost C", "22,34"),
    "LMP-072": ("InPost C", "InPost C", "22,34"),
    "LMP-086": ("InPost C", "InPost C", "22,34"),
    "LMP-123": ("InPost C", "InPost C", "22,34"),
    "LMP-146": ("InPost C", "InPost C", "22,34"),
    "LMP-182": ("InPost C", "InPost C", "22,34"),
    "LMP-029": ("Courier", "Kurier", "38,34"),
    "LMP-077": ("Courier", "Kurier", "38,34"),
    "LMP-078": ("Courier", "Kurier", "94,99"),
}


def build_values(label_en, label_pl, price):
    price_en = price.replace(",", ".")
    en = [PICKUP_LINE_EN, f"{label_en} {price_en} zł (Poland)"]
    pl = [PICKUP_LINE_PL, f"{label_pl} {price} zł (Polska)"]
    return json.dumps(en, ensure_ascii=False), json.dumps(pl, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    env = load_env()
    shop = Shopify(env)

    not_found = []
    for sku, (label_en, label_pl, price) in SHIPPING_DATA.items():
        product_id, variant_id = shop.find_by_sku(sku)
        if not product_id:
            not_found.append(sku)
            continue

        en_value, pl_value = build_values(label_en, label_pl, price)

        if args.dry_run:
            print(f"{sku}: {product_id}")
            print(f"  EN -> {en_value}")
            print(f"  PL -> {pl_value}")
            continue

        metafield_ids = shop.set_metafields(product_id, [{
            "namespace": "custom",
            "key": "shipping_pickup",
            "type": "list.single_line_text_field",
            "value": en_value,
        }])
        mf_id = metafield_ids["shipping_pickup"]
        shop.register_translations(mf_id, "pl", {"value": pl_value})
        print(f"{sku}: updated ({en_value})")

    if not_found:
        print(f"\nSKUs not found in Shopify, skipped: {not_found}", file=sys.stderr)


if __name__ == "__main__":
    main()
