#!/usr/bin/env python3
"""Remove duplicate images from Shopify products, keeping one copy of each.

For a given product (by SKU), downloads all attached media images, hashes
their content, and deletes every extra copy of an image that appears more
than once — keeping the first (earliest-attached) copy. Run with --all to
sweep every product in the store.

Usage:
  python3 dedupe_images.py AKC-151 --dry-run   # show what would be removed
  python3 dedupe_images.py AKC-151             # dedupe this product
  python3 dedupe_images.py --all --dry-run     # sweep every product, preview
  python3 dedupe_images.py --all               # sweep every product
"""
import argparse
import hashlib
import sys
import urllib.request

from sheet_to_shopify import Shopify, load_env

PRODUCT_MEDIA_QUERY = """
query($id: ID!, $cursor: String) {
  product(id: $id) {
    title
    media(first: 250, after: $cursor) {
      edges {
        node {
          id
          mediaContentType
          ... on MediaImage { image { url } }
        }
      }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""

ALL_SKUS_QUERY = """
query($cursor: String) {
  productVariants(first: 250, after: $cursor) {
    edges { node { sku product { id } } }
    pageInfo { hasNextPage endCursor }
  }
}
"""

DELETE_MEDIA = """
mutation($productId: ID!, $mediaIds: [ID!]!) {
  productDeleteMedia(productId: $productId, mediaIds: $mediaIds) {
    deletedMediaIds
    mediaUserErrors { field message }
  }
}
"""


def fetch_media(shop, product_id):
    images = []
    cursor = None
    title = None
    while True:
        data = shop.gql(PRODUCT_MEDIA_QUERY, {"id": product_id, "cursor": cursor})
        product = data["product"]
        title = product["title"]
        for edge in product["media"]["edges"]:
            node = edge["node"]
            if node["mediaContentType"] == "IMAGE" and node.get("image"):
                images.append((node["id"], node["image"]["url"]))
        page = product["media"]["pageInfo"]
        if not page["hasNextPage"]:
            break
        cursor = page["endCursor"]
    return title, images


def hash_url(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return hashlib.md5(r.read()).hexdigest()


def find_duplicates(images):
    """images: list of (media_id, url) in attachment order.
    Returns list of media_ids to delete, keeping the first of each duplicate group."""
    seen = {}
    to_delete = []
    for media_id, url in images:
        digest = hash_url(url)
        if digest in seen:
            to_delete.append(media_id)
        else:
            seen[digest] = media_id
    return to_delete


def dedupe_product(shop, sku, product_id, dry_run):
    title, images = fetch_media(shop, product_id)
    if len(images) < 2:
        print(f"{sku}: {len(images)} image(s), nothing to check")
        return
    to_delete = find_duplicates(images)
    if not to_delete:
        print(f"{sku} ({title}): {len(images)} images, no duplicates")
        return
    print(f"{sku} ({title}): {len(images)} images, {len(to_delete)} duplicate(s)"
          + (" [dry-run]" if dry_run else ""))
    if dry_run:
        return
    data = shop.gql(DELETE_MEDIA, {"productId": product_id, "mediaIds": to_delete})
    errors = data["productDeleteMedia"]["mediaUserErrors"]
    if errors:
        raise RuntimeError(str(errors))
    deleted = data["productDeleteMedia"]["deletedMediaIds"]
    print(f"  removed {len(deleted)} duplicate image(s)")


def fetch_all_skus(shop):
    skus = []
    cursor = None
    while True:
        data = shop.gql(ALL_SKUS_QUERY, {"cursor": cursor})
        variants = data["productVariants"]
        for edge in variants["edges"]:
            node = edge["node"]
            if node["sku"]:
                skus.append((node["sku"], node["product"]["id"]))
        if not variants["pageInfo"]["hasNextPage"]:
            break
        cursor = variants["pageInfo"]["endCursor"]
    return skus


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sku", nargs="?", help="SKU to dedupe (omit with --all)")
    ap.add_argument("--all", action="store_true", help="sweep every product in the store")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.all and not args.sku:
        sys.exit("Provide a SKU, or pass --all to sweep every product.")

    env = load_env()
    shop = Shopify(env)

    if args.all:
        for sku, product_id in fetch_all_skus(shop):
            try:
                dedupe_product(shop, sku, product_id, args.dry_run)
            except Exception as e:
                print(f"{sku}: ERROR {e}")
    else:
        product_id, _ = shop.find_by_sku(args.sku)
        if not product_id:
            sys.exit(f"No Shopify product found with SKU '{args.sku}'.")
        dedupe_product(shop, args.sku, product_id, args.dry_run)


if __name__ == "__main__":
    main()
