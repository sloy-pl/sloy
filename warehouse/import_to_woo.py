#!/usr/bin/env python3
"""Import products from data/products.json into WooCommerce.

- Idempotent by SKU: existing products are updated, not duplicated.
- Uploads each product's local image to the WP media library (cached so re-runs
  don't re-upload), then attaches it.
- Creates product categories on demand.

Usage:
  python3 import_to_woo.py --dry-run         # show what would happen, no calls
  python3 import_to_woo.py --limit 3         # do only the first 3 (test batch)
  python3 import_to_woo.py                    # full run
"""
import argparse, base64, json, mimetypes, os, sys
import urllib.request, urllib.error, urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(ROOT, "images")
STATE_PATH = os.path.join(ROOT, "data/upload_state.json")
RESULTS_PATH = os.path.join(ROOT, "data/import_results.csv")


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
    for k in ("WC_URL", "WC_KEY", "WC_SECRET", "WP_USER", "WP_APP_PASSWORD"):
        if not env.get(k):
            sys.exit(f"Missing {k} in .env")
    return env


def req(url, method="GET", data=None, headers=None, auth=None):
    h = dict(headers or {})
    if auth:
        tok = base64.b64encode(f"{auth[0]}:{auth[1]}".encode()).decode()
        h["Authorization"] = "Basic " + tok
    r = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            body = resp.read()
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"raw": body}


class Woo:
    def __init__(self, env):
        self.base = env["WC_URL"].rstrip("/")
        self.wc_auth = (env["WC_KEY"], env["WC_SECRET"])
        self.wp_auth = (env["WP_USER"], env["WP_APP_PASSWORD"].replace(" ", ""))
        self._cat = {}

    def _wc(self, path, method="GET", payload=None):
        url = f"{self.base}/wp-json/wc/v3/{path}"
        data = json.dumps(payload).encode() if payload is not None else None
        return req(url, method, data,
                   {"Content-Type": "application/json"}, self.wc_auth)

    def category_id(self, name):
        if name in self._cat:
            return self._cat[name]
        st, res = self._wc(f"products/categories?search={urllib.parse.quote(name)}&per_page=100")
        if st == 200:
            for c in res:
                if c["name"] == name:
                    self._cat[name] = c["id"]
                    return c["id"]
        st, res = self._wc("products/categories", "POST", {"name": name})
        if st in (200, 201):
            self._cat[name] = res["id"]
            return res["id"]
        raise RuntimeError(f"category {name!r}: {st} {res}")

    def find_by_sku(self, sku):
        st, res = self._wc(f"products?sku={urllib.parse.quote(sku)}")
        if st == 200 and res:
            return res[0]["id"]
        return None

    def upload_media(self, filename):
        path = os.path.join(IMG_DIR, filename)
        ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        with open(path, "rb") as f:
            data = f.read()
        url = f"{self.base}/wp-json/wp/v2/media"
        st, res = req(url, "POST", data, {
            "Content-Type": ctype,
            "Content-Disposition": f'attachment; filename="{filename}"',
        }, self.wp_auth)
        if st in (200, 201):
            return res["id"]
        raise RuntimeError(f"media upload {filename}: {st} {res}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    products = json.load(open(os.path.join(ROOT, "data/products.json"), encoding="utf-8"))
    if args.limit:
        products = products[:args.limit]

    if args.dry_run:
        for p in products:
            print(f"{p['sku']:>10}  img={'Y' if p['image_file'] else '-'}  "
                  f"{p['stock_status']:>10}  {p['category']:<22}  {p['name']}")
        print(f"\n{len(products)} products would be imported.")
        return

    env = load_env()
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    woo = Woo(env)
    state = json.load(open(STATE_PATH)) if os.path.exists(STATE_PATH) else {}
    results = []

    for i, p in enumerate(products, 1):
        sku = p["sku"]
        try:
            cat_id = woo.category_id(p["category"])
            media_id = state.get(sku)
            if p["image_file"] and not media_id:
                media_id = woo.upload_media(p["image_file"])
                state[sku] = media_id
                json.dump(state, open(STATE_PATH, "w"))
            payload = {
                "name": p["name"], "sku": sku, "type": "simple",
                "status": p["status"], "catalog_visibility": p["catalog_visibility"],
                "regular_price": p["regular_price"], "manage_stock": p["manage_stock"],
                "stock_status": p["stock_status"], "description": p["description"],
                "categories": [{"id": cat_id}], "meta_data": p["meta_data"],
            }
            if media_id:
                payload["images"] = [{"id": media_id}]
            existing = woo.find_by_sku(sku)
            if existing:
                st, res = woo._wc(f"products/{existing}", "PUT", payload)
                action = "updated"
            else:
                st, res = woo._wc("products", "POST", payload)
                action = "created"
            ok = st in (200, 201)
            pid = res.get("id") if ok else ""
            results.append((sku, action if ok else "FAIL", pid, "" if ok else f"{st} {res.get('message', res)}"))
            print(f"[{i}/{len(products)}] {sku}: {action if ok else 'FAIL ' + str(st)} (id={pid})")
        except Exception as e:
            results.append((sku, "ERROR", "", str(e)))
            print(f"[{i}/{len(products)}] {sku}: ERROR {e}")

    import csv
    with open(RESULTS_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sku", "action", "product_id", "error"])
        w.writerows(results)
    bad = [r for r in results if r[1] in ("FAIL", "ERROR")]
    print(f"\nDone. {len(results) - len(bad)} ok, {len(bad)} failed. Log: data/import_results.csv")


if __name__ == "__main__":
    main()
