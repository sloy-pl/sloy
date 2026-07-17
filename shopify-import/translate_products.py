#!/usr/bin/env python3
"""Translate untranslated products (EN -> PL) and push via translationsRegister.

Two-step workflow, since the actual translation is done by a human/LLM
following pl-translation-style-guide.md, not by an API call:

  1. python3 translate_products.py --export
     Finds every PRODUCT translatableResource with no PL "title" translation
     yet, and writes data/to_translate.json with their EN content (title,
     body_html, handle) plus the product's option-name resource. Empty "pl"
     fields are left for a translator to fill in.

  2. Fill in the "pl" fields in data/to_translate.json (by hand, or by having
     an LLM translate per pl-translation-style-guide.md).

  3. python3 translate_products.py --push [file]
     Reads the filled-in file (default data/to_translate.json) and registers
     each pl value via translationsRegister.
"""
import argparse, json, os, sys

from sheet_to_shopify import Shopify, load_env

ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PATH = os.path.join(ROOT, "data", "to_translate.json")

UNTRANSLATED_QUERY = """
query($cursor: String) {
  translatableResources(first: 100, resourceType: PRODUCT, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    nodes {
      resourceId
      translatableContent { key value }
      translations(locale: "pl") { key value }
    }
  }
}
"""

OPTION_QUERY = """
query($productId: ID!) {
  product(id: $productId) {
    options { id name }
  }
}
"""


def export(shop):
    cursor = None
    items = []
    while True:
        data = shop.gql(UNTRANSLATED_QUERY, {"cursor": cursor})
        conn = data["translatableResources"]
        for node in conn["nodes"]:
            has_pl_title = any(t["key"] == "title" for t in node["translations"])
            if has_pl_title:
                continue
            content = {c["key"]: c["value"] for c in node["translatableContent"]}
            product_id = node["resourceId"]

            opt_data = shop.gql(OPTION_QUERY, {"productId": product_id})
            options = opt_data["product"]["options"]
            option = options[0] if options else None

            items.append({
                "resource_id": product_id,
                "en": {
                    "title": content.get("title", ""),
                    "body_html": content.get("body_html", ""),
                    "handle": content.get("handle", ""),
                },
                "pl": {
                    "title": "",
                    "body_html": "",
                    "handle": "",
                },
                "option": {
                    "resource_id": option["id"],
                    "en": option["name"],
                    "pl": "",
                } if option else None,
            })
        if not conn["pageInfo"]["hasNextPage"]:
            break
        cursor = conn["pageInfo"]["endCursor"]
    return items


def push(shop, items, locale="pl"):
    results = []
    for item in items:
        pl = item["pl"]
        fields = {k: v for k, v in pl.items() if v.strip()}
        try:
            if fields:
                shop.register_translations(item["resource_id"], locale, fields)
            option = item.get("option")
            if option and option["pl"].strip():
                shop.register_translations(option["resource_id"], locale, {"name": option["pl"]})
            results.append((item["resource_id"], "ok", ""))
            print(f"{item['resource_id']}: ok ({item['en']['title']})")
        except Exception as e:
            results.append((item["resource_id"], "ERROR", str(e)))
            print(f"{item['resource_id']}: ERROR {e}")
    bad = [r for r in results if r[1] == "ERROR"]
    print(f"\nDone. {len(results) - len(bad)} ok, {len(bad)} failed.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", action="store_true", help="write data/to_translate.json")
    ap.add_argument("--push", nargs="?", const=DEFAULT_PATH, help="push translations from file (default data/to_translate.json)")
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
        print(f"{len(items)} untranslated products -> {DEFAULT_PATH}", file=sys.stderr)

    if args.push:
        with open(args.push, encoding="utf-8") as f:
            items = json.load(f)
        push(shop, items, args.locale)


if __name__ == "__main__":
    main()
