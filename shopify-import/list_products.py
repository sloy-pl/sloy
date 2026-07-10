#!/usr/bin/env python3
"""List the titles of all products currently in the Shopify store.

Usage:
  python3 list_products.py
"""
import sys

from sheet_to_shopify import Shopify, load_env


def fetch_all_titles(shop):
    query = """
    query($cursor: String) {
      products(first: 250, after: $cursor) {
        edges { node { title } }
        pageInfo { hasNextPage endCursor }
      }
    }
    """
    titles = []
    cursor = None
    while True:
        data = shop.gql(query, {"cursor": cursor})
        products = data["products"]
        titles.extend(edge["node"]["title"] for edge in products["edges"])
        if not products["pageInfo"]["hasNextPage"]:
            break
        cursor = products["pageInfo"]["endCursor"]
    return titles


def main():
    env = load_env()
    shop = Shopify(env)
    titles = fetch_all_titles(shop)
    for title in titles:
        print(title)
    print(f"\n{len(titles)} products.", file=sys.stderr)


if __name__ == "__main__":
    main()
