#!/usr/bin/env python3
"""Import products from the SLOY Google Sheet into Shopify via the Admin API.

Reads the public CSV export of the sheet (SKU, Title, Description, ...) and
creates/updates a Shopify product per row, setting title, description
(Body HTML) and the variant SKU. Idempotent by SKU: an existing product with
that SKU is updated rather than duplicated. New products are created as
drafts, no price (fill those in later, e.g. via build_csv.py + Shopify's CSV
import for the fuller metafield/image workflow).

Usage:
  python3 sheet_to_shopify.py --dry-run     # show what would happen, no calls
  python3 sheet_to_shopify.py --limit 3     # do only the first 3 (test batch)
  python3 sheet_to_shopify.py                # full run
"""
import argparse, csv, io, json, os, sys, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.abspath(__file__))
SHEET_ID = "1x0J7ufFHrLUdTQ3WahUBdrYH_bl9nkb2yPvzFXpGmZ8"
SHEET_GID = "0"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}"


def load_env():
    env = {}
    p = os.path.join(ROOT, ".env")
    if not os.path.exists(p):
        sys.exit("Missing .env — copy .env.example to .env and fill it in.")
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    for k in ("SHOPIFY_STORE", "SHOPIFY_ACCESS_TOKEN"):
        if not env.get(k):
            sys.exit(f"Missing {k} in .env")
    env.setdefault("SHOPIFY_API_VERSION", "2024-10")
    return env


def fetch_rows():
    with urllib.request.urlopen(CSV_URL, timeout=60) as resp:
        text = resp.read().decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(text)))
    products = []
    for row in rows:
        sku = (row.get("SKU") or "").strip()
        title = (row.get("Title") or "").strip()
        if not sku or not title:
            continue
        products.append({
            "sku": sku,
            "title": title,
            "body_html": body_html(row.get("Description") or ""),
        })
    return products


def body_html(description):
    paras = [p.strip() for p in description.split("\n\n") if p.strip()]
    return "".join(f"<p>{p}</p>" for p in paras)


class Shopify:
    def __init__(self, env):
        self.url = f"https://{env['SHOPIFY_STORE']}/admin/api/{env['SHOPIFY_API_VERSION']}/graphql.json"
        self.token = env["SHOPIFY_ACCESS_TOKEN"]

    def gql(self, query, variables=None):
        payload = json.dumps({"query": query, "variables": variables or {}}).encode()
        req = urllib.request.Request(self.url, data=payload, method="POST", headers={
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.token,
        })
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')}")
        if "errors" in body:
            raise RuntimeError(str(body["errors"]))
        return body["data"]

    def find_by_sku(self, sku):
        query = """
        query($q: String!) {
          productVariants(first: 1, query: $q) {
            edges { node { id product { id } } }
          }
        }
        """
        safe_sku = sku.replace('"', '\\"')
        data = self.gql(query, {"q": f'sku:"{safe_sku}"'})
        edges = data["productVariants"]["edges"]
        if not edges:
            return None, None
        node = edges[0]["node"]
        return node["product"]["id"], node["id"]

    def create_product(self, title, body_html, sku):
        mutation = """
        mutation($input: ProductInput!) {
          productCreate(input: $input) {
            product { id variants(first: 1) { edges { node { id } } } }
            userErrors { field message }
          }
        }
        """
        data = self.gql(mutation, {"input": {
            "title": title, "descriptionHtml": body_html, "status": "DRAFT",
        }})
        result = data["productCreate"]
        if result["userErrors"]:
            raise RuntimeError(str(result["userErrors"]))
        product_id = result["product"]["id"]
        variant_id = result["product"]["variants"]["edges"][0]["node"]["id"]
        self.set_sku(product_id, variant_id, sku)
        return product_id

    def set_sku(self, product_id, variant_id, sku):
        mutation = """
        mutation($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
          productVariantsBulkUpdate(productId: $productId, variants: $variants) {
            userErrors { field message }
          }
        }
        """
        data = self.gql(mutation, {
            "productId": product_id,
            "variants": [{"id": variant_id, "inventoryItem": {"sku": sku}}],
        })
        errors = data["productVariantsBulkUpdate"]["userErrors"]
        if errors:
            raise RuntimeError(str(errors))

    def update_product(self, product_id, title, body_html):
        mutation = """
        mutation($input: ProductInput!) {
          productUpdate(input: $input) {
            userErrors { field message }
          }
        }
        """
        data = self.gql(mutation, {"input": {
            "id": product_id, "title": title, "descriptionHtml": body_html,
        }})
        errors = data["productUpdate"]["userErrors"]
        if errors:
            raise RuntimeError(str(errors))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    products = fetch_rows()
    if args.limit:
        products = products[:args.limit]

    if args.dry_run:
        for p in products:
            print(f"{p['sku']:>10}  {p['title']}")
        print(f"\n{len(products)} products would be imported.")
        return

    env = load_env()
    shop = Shopify(env)
    results = []

    for i, p in enumerate(products, 1):
        sku = p["sku"]
        try:
            product_id, _variant_id = shop.find_by_sku(sku)
            if product_id:
                shop.update_product(product_id, p["title"], p["body_html"])
                action = "updated"
            else:
                product_id = shop.create_product(p["title"], p["body_html"], sku)
                action = "created"
            results.append((sku, action, product_id, ""))
            print(f"[{i}/{len(products)}] {sku}: {action} ({product_id})")
        except Exception as e:
            results.append((sku, "ERROR", "", str(e)))
            print(f"[{i}/{len(products)}] {sku}: ERROR {e}")

    results_path = os.path.join(ROOT, "import_results.csv")
    with open(results_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sku", "action", "product_id", "error"])
        w.writerows(results)
    bad = [r for r in results if r[1] in ("FAIL", "ERROR")]
    print(f"\nDone. {len(results) - len(bad)} ok, {len(bad)} failed. Log: {results_path}")


if __name__ == "__main__":
    main()
