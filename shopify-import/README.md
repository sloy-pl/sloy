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
(SKU, Title, Description, plus the metafield columns: Key features,
Condition, Dimensions, Perfect for, Shipping & pickup, SLOY quality
standard, Designer, Manufacturer). Idempotent by SKU — creates new
products as drafts, updates existing ones by title/description, and sets
`product.metafields.custom.*` to match the store's existing metafield
definitions (types: list.single_line_text_field, multi_line_text_field,
single_line_text_field).

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

### `upload_images.py`

Uploads a SKU's photos from the shared Google Drive folder (subfoldered by
SKU) to its Shopify product, via Shopify's staged-upload flow. Needs the
Google API client, so run it with the `gdrive/` venv (it reuses
`../gdrive/.env` for Drive access):

```bash
source ../gdrive/.venv/bin/activate
python3 upload_images.py AKC-151 --dry-run   # list images, no upload
python3 upload_images.py AKC-151             # upload to Shopify
```

### `build_csv.py`

Builds a Shopify product-import CSV (`products_import.csv`) for new
products with photos, from local Downloads CSVs + `sku_images.json`.

```bash
python3 build_csv.py
```
