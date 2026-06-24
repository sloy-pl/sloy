# CLAUDE.md

**Keep all work inside this folder.** Everything for sloy — the visual-regression
suite, the theme, and the WooCommerce warehouse tooling — lives under
`/Users/marcinwosinek/workspace/sloy`. Do not create sibling project directories
(e.g. `../sloy-shop`); add new work as a subfolder here instead.

This repo holds a Playwright visual-regression suite for the **sloy.pl** Shopify
storefront (Dawn theme). It captures one full-page screenshot per template
(desktop + mobile), commits them as baselines, and diffs later runs to catch
regressions.

## Commands

```bash
npm run snapshot   # capture / refresh baselines (writes tests/__screenshots__/)
npm test           # compare the site against committed baselines
npm run report     # open the HTML report locally
```

`BASE_URL` overrides the target (defaults to `https://sloy.pl`).

## Layout

- `tests/pages.ts` — the pages under test (one per template) + per-page `mask` selectors.
- `tests/helpers.ts` — `preparePage()`: dismiss cookie bar, freeze animations, load lazy images.
- `tests/visual.spec.ts` — loops over pages, asserts `toHaveScreenshot`.
- `tests/__screenshots__/<project>/` — committed baselines (the source of truth).
- `.github/workflows/` — `update-baselines.yml` (regenerate on Linux), `visual-report.yml` (compare + publish report to GitHub Pages).

## Gotchas

- **Baselines are OS-specific.** Generate and compare on the same platform. CI baselines are made on `mcr.microsoft.com/playwright:v1.60.0-noble`; bump that tag in lockstep with the `@playwright/test` version.
- The cookie consent bar must be **dismissed** (button "Akceptuj"), never masked — fixed-position masks misplace in full-page shots.
- Don't use `networkidle`; it never settles on the analytics-heavy store. Use fixed settles.
- Lazy-image waits must be time-capped or the product page hangs.
- For dynamic regions (e.g. search `#product-grid`), add a CSS selector to that page's `mask` rather than raising global tolerance.

## warehouse/ — WooCommerce import

Tooling to load the warehouse/inventory into the WordPress + WooCommerce shop at
`https://navajowhite-wren-889557.hostingersite.com`. Self-contained; scripts
resolve paths relative to themselves, so run them from anywhere.

```bash
cd warehouse
python3 download_images.py     # fetch Airtable photos -> images/ (expiring URLs; do first)
python3 transform.py           # data/sales.csv -> data/products.json
python3 import_to_woo.py --dry-run     # preview
python3 import_to_woo.py --limit 3     # test batch, then drop --limit for all 252
```

- `data/sales.csv` — Airtable sales-ledger export (source of truth, 252 rows).
- Importer is idempotent by SKU; needs `warehouse/.env` (copy from `.env.example`):
  WooCommerce REST keys for products + a WP Application Password for media upload.
- All products import as **draft**, no price; categories come from the SKU prefix.
