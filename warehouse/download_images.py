#!/usr/bin/env python3
"""Download all Airtable product images locally, named by SKU.
Writes images/<SKU><ext> and data/image_map.csv (SKU,filename,url,status)."""
import csv, re, os, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(ROOT, "images")
os.makedirs(IMG, exist_ok=True)
os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)

url_re = re.compile(r'https://v5\.airtableusercontent\.com/[^\s)]+')
fname_re = re.compile(r'^\s*"*\s*(.+?)\s*\(https://', re.S)

rows = []
with open(os.path.join(ROOT, "data/sales.csv"), encoding="utf-8-sig") as f:
    for x in csv.DictReader(f):
        z = x["Zdjęcie"]
        m = url_re.search(z)
        if not m:
            continue
        url = m.group(0)
        orig = fname_re.match(z)
        orig = orig.group(1).strip().strip('"') if orig else ""
        ext = ".png" if ".png" in orig.lower() else ".jpg"
        sku = x["SKU"].strip() or f"row{len(rows)}"
        rows.append((sku, orig, url, ext))

print(f"{len(rows)} images to fetch")
out = []
for i, (sku, orig, url, ext) in enumerate(rows, 1):
    dest_name = f"{sku}{ext}"
    dest = os.path.join(IMG, dest_name)
    status = "ok"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        with open(dest, "wb") as fo:
            fo.write(data)
        if len(data) < 1000:
            status = f"suspect-small({len(data)}b)"
    except urllib.error.HTTPError as e:
        status = f"HTTP {e.code}"
    except Exception as e:
        status = f"ERR {type(e).__name__}"
    out.append((sku, dest_name, url, status))
    print(f"[{i}/{len(rows)}] {sku} -> {status}")

with open(os.path.join(ROOT, "data/image_map.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["SKU", "filename", "url", "status"])
    w.writerows(out)

bad = [r for r in out if r[3] != "ok"]
print(f"\nDone. {len(out)-len(bad)} ok, {len(bad)} problems.")
for r in bad:
    print("  FAIL", r[0], r[3])
