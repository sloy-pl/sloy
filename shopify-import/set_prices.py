#!/usr/bin/env python3
"""Set variant prices in Shopify from the SLOY pricing Google Sheet.

Reads the public CSV export (columns: SKU, Cena PLN (wliczony VAT)) and sets
the variant price for the matching product, looked up by SKU via the Admin
API. Products not found in Shopify are reported and skipped.

Usage:
  python3 set_prices.py --dry-run     # show what would happen, no calls
  python3 set_prices.py --limit 3     # do only the first 3 (test batch)
  python3 set_prices.py                # full run
"""
import argparse, csv, io, json, os, sys, urllib.request, urllib.error, urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
SHEET_ID = "1zxD64SVtoZtRJ4qKJU0iYhFYPKLG2BMkCtTk808BPV4"
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
    for k in ("SHOPIFY_STORE", "SHOPIFY_CLIENT_ID", "SHOPIFY_CLIENT_SECRET"):
        if not env.get(k):
            sys.exit(f"Missing {k} in .env")
    env.setdefault("SHOPIFY_API_VERSION", "2024-10")
    return env


def fetch_access_token(env):
    url = f"https://{env['SHOPIFY_STORE']}/admin/oauth/access_token"
    data = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": env["SHOPIFY_CLIENT_ID"],
        "client_secret": env["SHOPIFY_CLIENT_SECRET"],
    }).encode()
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "Content-Type": "application/x-www-form-urlencoded",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"Failed to get access token — HTTP {e.code}: {e.read().decode('utf-8', 'replace')}")
    return body["access_token"]


def fetch_rows():
    with urllib.request.urlopen(CSV_URL, timeout=60) as resp:
        text = resp.read().decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(text)))
    price_col = next(c for c in rows[0].keys() if c != "SKU")
    prices = []
    for row in rows:
        sku = (row.get("SKU") or "").strip()
        price_raw = (row.get(price_col) or "").strip()
        if not sku or not price_raw:
            continue
        try:
            price = float(price_raw.replace(",", "."))
        except ValueError:
            print(f"skip {sku}: unparsable price {price_raw!r}", file=sys.stderr)
            continue
        prices.append({"sku": sku, "price": price})
    return prices


class Shopify:
    def __init__(self, env):
        self.url = f"https://{env['SHOPIFY_STORE']}/admin/api/{env['SHOPIFY_API_VERSION']}/graphql.json"
        self.token = fetch_access_token(env)

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

    def set_price(self, product_id, variant_id, price):
        mutation = """
        mutation($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
          productVariantsBulkUpdate(productId: $productId, variants: $variants) {
            userErrors { field message }
          }
        }
        """
        data = self.gql(mutation, {
            "productId": product_id,
            "variants": [{"id": variant_id, "price": f"{price:.2f}"}],
        })
        errors = data["productVariantsBulkUpdate"]["userErrors"]
        if errors:
            raise RuntimeError(str(errors))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    rows = fetch_rows()
    if args.limit:
        rows = rows[:args.limit]

    if args.dry_run:
        for r in rows:
            print(f"{r['sku']:>10}  {r['price']:.2f} PLN")
        print(f"\n{len(rows)} prices would be set.")
        return

    env = load_env()
    shop = Shopify(env)
    results = []

    for i, r in enumerate(rows, 1):
        sku = r["sku"]
        try:
            product_id, variant_id = shop.find_by_sku(sku)
            if not product_id:
                results.append((sku, "NOT_FOUND", "", ""))
                print(f"[{i}/{len(rows)}] {sku}: NOT FOUND")
                continue
            shop.set_price(product_id, variant_id, r["price"])
            results.append((sku, "updated", product_id, ""))
            print(f"[{i}/{len(rows)}] {sku}: updated to {r['price']:.2f} PLN")
        except Exception as e:
            results.append((sku, "ERROR", "", str(e)))
            print(f"[{i}/{len(rows)}] {sku}: ERROR {e}")

    results_path = os.path.join(ROOT, "price_update_results.csv")
    with open(results_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sku", "action", "product_id", "error"])
        w.writerows(results)
    bad = [r for r in results if r[1] in ("NOT_FOUND", "ERROR")]
    print(f"\nDone. {len(results) - len(bad)} ok, {len(bad)} failed. Log: {results_path}")


if __name__ == "__main__":
    main()
