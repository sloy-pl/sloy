# CLAUDE.md

Playwright visual-regression suite for the **sloy.pl** Shopify storefront (Dawn
theme). Captures one full-page screenshot per template (desktop + mobile),
commits them as baselines, and diffs later runs to catch regressions.

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
