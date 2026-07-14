#!/usr/bin/env python3
"""Export all product-related EN->PL translated strings from Shopify.

Walks every PRODUCT and PRODUCT_VARIANT translatable resource in the store
(title, body_html, handle, seo title/description, options, and any
translatable metafields) and pairs the English source content with its
Polish translation, for building a translation corpus.

Requires the app to have scope read_translations (plus read_products),
same credentials as sheet_to_shopify.py (shopify-import/.env).

Usage:
  python3 export_translations.py                 # writes data/translations_pl.json + .csv
  python3 export_translations.py --locale pl
  python3 export_translations.py --out-prefix data/corpus
"""
import argparse, csv, json, os, sys

from sheet_to_shopify import Shopify, load_env

ROOT = os.path.dirname(os.path.abspath(__file__))

RESOURCE_TYPES = ["PRODUCT", "PRODUCT_OPTION", "PRODUCT_OPTION_VALUE"]

RESOURCES_QUERY = """
query($type: TranslatableResourceType!, $locale: String!, $cursor: String) {
  translatableResources(first: 100, resourceType: $type, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    nodes {
      resourceId
      translatableContent { key value locale digest }
      translations(locale: $locale) { key value }
    }
  }
}
"""


def fetch_resources(shop, resource_type, locale):
    cursor = None
    while True:
        data = shop.gql(RESOURCES_QUERY, {"type": resource_type, "locale": locale, "cursor": cursor})
        conn = data["translatableResources"]
        for node in conn["nodes"]:
            yield node
        if not conn["pageInfo"]["hasNextPage"]:
            break
        cursor = conn["pageInfo"]["endCursor"]


def collect(shop, locale):
    rows = []
    for resource_type in RESOURCE_TYPES:
        count = 0
        try:
            for node in fetch_resources(shop, resource_type, locale):
                translated = {t["key"]: t["value"] for t in node["translations"]}
                for content in node["translatableContent"]:
                    key = content["key"]
                    source = content["value"]
                    target = translated.get(key)
                    if not source or not target:
                        continue
                    rows.append({
                        "resource_type": resource_type,
                        "resource_id": node["resourceId"],
                        "key": key,
                        "source_locale": content["locale"],
                        "en": source,
                        "pl": target,
                    })
                count += 1
        except RuntimeError as e:
            print(f"{resource_type}: skipped ({e})", file=sys.stderr)
            continue
        print(f"{resource_type}: scanned {count} resources", file=sys.stderr)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--locale", default="pl")
    parser.add_argument("--out-prefix", default=os.path.join(ROOT, "data", "translations"))
    args = parser.parse_args()

    env = load_env()
    shop = Shopify(env)
    rows = collect(shop, args.locale)

    os.makedirs(os.path.dirname(args.out_prefix), exist_ok=True)

    json_path = f"{args.out_prefix}_{args.locale}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    csv_path = f"{args.out_prefix}_{args.locale}.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["resource_type", "resource_id", "key", "source_locale", "en", "pl"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n{len(rows)} translated strings -> {json_path}, {csv_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
