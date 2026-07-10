# shopify-import

Scripts to import/inspect SLOY products in Shopify via the Admin GraphQL API.

## Setup

```bash
cp .env.example .env
# fill in SHOPIFY_STORE, SHOPIFY_CLIENT_ID, SHOPIFY_CLIENT_SECRET
```

## Scripts

### `sheet_to_shopify.py`

Imports products from the public CSV export of the SLOY Google Sheet
(SKU, Title, Description). Idempotent by SKU — creates new products as
drafts, updates existing ones by title/description.

```bash
python3 sheet_to_shopify.py --dry-run     # show what would happen, no calls
python3 sheet_to_shopify.py --limit 3     # test batch
python3 sheet_to_shopify.py               # full run
```

### `list_products.py`

Lists the titles of every product currently in the store (paginates
through all of them).

```bash
python3 list_products.py
```

### `build_csv.py`

Builds a Shopify product-import CSV (`products_import.csv`) for new
products with photos, from local Downloads CSVs + `sku_images.json`.

```bash
python3 build_csv.py
```
