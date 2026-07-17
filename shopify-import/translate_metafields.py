#!/usr/bin/env python3
"""Translate draft products' metafields (EN -> PL) and push via translationsRegister.

Same two-step workflow as translate_products.py, but for the custom
metafields (Key features, Condition, Dimensions, Perfect for, Shipping &
pickup, SLOY quality standard, Designer, Manufacturer) instead of
title/body_html/handle, and scoped to products still in DRAFT status
(the recently-imported batch).

  1. python3 translate_metafields.py --export
     Finds every DRAFT product, reads its "custom" metafields, and for each
     metafield with no PL "value" translation yet, writes its EN value to
     data/to_translate_metafields.json. Empty "pl" fields are left for a
     translator to fill in.

  2. Fill in the "pl" fields (by hand, or by having an LLM translate per
     pl-translation-style-guide.md). List-type metafield values are JSON
     arrays of strings — translate each item, keep the JSON array shape.

  3. python3 translate_metafields.py --push [file]
     Reads the filled-in file (default data/to_translate_metafields.json)
     and registers each pl value via translationsRegister.
"""
import argparse, json, os, sys

from sheet_to_shopify import Shopify, load_env, METAFIELD_COLUMNS

ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PATH = os.path.join(ROOT, "data", "to_translate_metafields.json")

METAFIELD_KEYS = [key for (_ns, key, _type) in METAFIELD_COLUMNS.values()]

DRAFT_PRODUCTS_QUERY = """
query($cursor: String) {
  products(first: 50, query: "status:draft", after: $cursor) {
    pageInfo { hasNextPage endCursor }
    nodes {
      id
      title
      metafields(first: 20, namespace: "custom") {
        nodes { id key value }
      }
    }
  }
}
"""

METAFIELD_TRANSLATION_QUERY = """
query($id: ID!) {
  translatableResource(resourceId: $id) {
    translations(locale: "pl") { key value }
  }
}
"""


def export(shop):
    cursor = None
    items = []
    while True:
        data = shop.gql(DRAFT_PRODUCTS_QUERY, {"cursor": cursor})
        conn = data["products"]
        for product in conn["nodes"]:
            for mf in product["metafields"]["nodes"]:
                if mf["key"] not in METAFIELD_KEYS:
                    continue
                tr_data = shop.gql(METAFIELD_TRANSLATION_QUERY, {"id": mf["id"]})
                res = tr_data["translatableResource"]
                has_pl = res and any(t["key"] == "value" for t in res["translations"])
                if has_pl:
                    continue
                items.append({
                    "resource_id": mf["id"],
                    "product_title": product["title"],
                    "key": mf["key"],
                    "en": mf["value"],
                    "pl": "",
                })
        if not conn["pageInfo"]["hasNextPage"]:
            break
        cursor = conn["pageInfo"]["endCursor"]
    return items


def push(shop, items, locale="pl"):
    results = []
    for item in items:
        pl = item["pl"].strip()
        if not pl:
            continue
        try:
            shop.register_translations(item["resource_id"], locale, {"value": pl})
            results.append((item["resource_id"], "ok", ""))
            print(f"{item['resource_id']}: ok ({item['product_title']} / {item['key']})")
        except Exception as e:
            results.append((item["resource_id"], "ERROR", str(e)))
            print(f"{item['resource_id']}: ERROR {e}")
    bad = [r for r in results if r[1] == "ERROR"]
    print(f"\nDone. {len(results) - len(bad)} ok, {len(bad)} failed.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", action="store_true", help="write data/to_translate_metafields.json")
    ap.add_argument("--push", nargs="?", const=DEFAULT_PATH, help="push translations from file (default data/to_translate_metafields.json)")
    ap.add_argument("--locale", default="pl")
    args = ap.parse_args()

    if not args.export and not args.push:
        sys.exit("Specify --export or --push")

    env = load_env()
    shop = Shopify(env)

    if args.export:
        items = export(shop)
        os.makedirs(os.path.dirname(DEFAULT_PATH), exist_ok=True)
        with open(DEFAULT_PATH, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        print(f"{len(items)} untranslated metafields -> {DEFAULT_PATH}", file=sys.stderr)

    if args.push:
        with open(args.push, encoding="utf-8") as f:
            items = json.load(f)
        push(shop, items, args.locale)


if __name__ == "__main__":
    main()
