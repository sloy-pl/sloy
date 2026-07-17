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

**Translations (Polish):** if a row has "<Column> (PL)" companions (e.g.
`Title (PL)`, `Description (PL)`, `Key features (PL)`) filled in, those get
pushed as `pl` translations of the product/metafield content via
`translationsRegister`. This is not active yet:

- The sheet currently has no PL columns/content.
- The app's Dev Dashboard scopes need `read_translations` +
  `write_translations` added (confirmed missing — currently only product/
  media scopes). Re-run the client_credentials exchange after adding them.
- Polish is already enabled as a shop language in Settings → Languages, so
  no store-side setup is needed once the scope and sheet content exist.

Once those are in place, `python3 sheet_to_shopify.py --locale pl` (the
default) will translate any row with PL columns filled in; rows without PL
content are imported normally and skipped for translation.

```bash
python3 sheet_to_shopify.py --dry-run     # show what would happen, no calls
python3 sheet_to_shopify.py --limit 3     # test batch
python3 sheet_to_shopify.py               # full run
```

### `export_translations.py`

Exports an EN→PL corpus of every translated product string in the store —
product title/body_html/handle/seo, plus product options and option values
(and any translatable metafields, if metafield definitions have translation
enabled) — via `translatableResources`. Writes
`data/translations_pl.json` and `data/translations_pl.csv`
(`resource_type, resource_id, key, en, pl`).

Needs the same `read_translations` scope gap noted above fixed first (the
app currently only has product/media scopes); until then every resource
type is skipped with an `ACCESS_DENIED` message and the output is empty.

```bash
python3 export_translations.py                # data/translations_pl.{json,csv}
python3 export_translations.py --locale pl
python3 export_translations.py --out-prefix data/corpus
```

### `translate_products.py`

Translates newly-imported products (EN -> PL) and pushes the result via
`translationsRegister`. The actual translation is done by hand (or by an
LLM) following `pl-translation-style-guide.md` — this script only handles
the Shopify side (finding what's untranslated, and writing translations
back).

```bash
python3 translate_products.py --export        # -> data/to_translate.json
#   ... fill in the "pl" fields for each product, per the style guide ...
python3 translate_products.py --push           # reads data/to_translate.json
```

`--export` finds every product with no PL `title` translation yet (so it's
safe to re-run — already-translated products are skipped) and writes their
EN title/body_html/handle plus the "Title" product-option resource to
`data/to_translate.json` with empty `pl` fields. Fill those in, then
`--push` registers them. Re-run `--export` any time new products are
imported to pick up the next batch.

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
