# sloy.pl visual regression

Screenshot-based regression tests for the [sloy.pl](https://sloy.pl) Shopify
storefront. Captures one screenshot per template (desktop + mobile), commits
them as baselines, and fails when a later run renders differently — so you can
verify the theme still looks right after big changes (e.g. the migration to
GitHub).

## How it works

[Playwright](https://playwright.dev) drives a real browser over a fixed list of
pages, normalises each page (dismisses the cookie bar, disables animations,
loads lazy images, waits for fonts), and compares a full-page screenshot to a
committed baseline. Baselines live in `tests/__screenshots__/<viewport>/` and
are part of the repo.

- **Pages captured:** `tests/pages.ts` — one representative page per template
  (home, collection, product, content page, contact, blog, cart, search, login,
  404).
- **Viewports:** `desktop` (1366×900, Chromium) and `mobile` (iPhone 13,
  WebKit), configured in `playwright.config.ts`.
- **Target site:** `BASE_URL`, defaults to `https://sloy.pl`.

## Usage

```bash
npm install
npx playwright install chromium webkit   # one-time browser download

npm run snapshot   # capture / refresh baselines from the target site
npm test           # compare the target site against committed baselines
npm run report     # open the HTML diff report after a failing run
```

### Verifying after a theme change

The chosen workflow is **snapshot production over time**:

1. Baselines are captured from live `sloy.pl` (already committed).
2. After the new theme goes live, run `npm test`. Any visual change from the
   committed baselines fails the matching test.
3. Open `npm run report` to see expected / actual / diff side by side.
4. If a change is intentional, refresh the baseline with `npm run snapshot`
   (or a single page, see below) and commit the new images.

You can also point the suite at any other URL — e.g. a Shopify theme preview or
a local `shopify theme dev` server — without touching the baselines:

```bash
BASE_URL=http://127.0.0.1:9292 npm test
```

### Working with a single page

```bash
npm test -- -g "product"              # compare just the product template
npm run snapshot -- -g "search"       # refresh just the search baselines
npm test -- --project=desktop         # one viewport only
```

## Adding pages

Append to the array in `tests/pages.ts`:

```ts
{ name: "lookbook", path: "/pages/lookbook", template: "page.lookbook" }
```

Then `npm run snapshot -- -g "lookbook"` and commit the new baseline images.

## Handling dynamic content (false positives)

Regions that legitimately change between runs (carousels, live stock, search
results) would otherwise diff on every run. Add their CSS selectors to a page's
`mask` array — Playwright paints over them before comparing. The search page
already masks `#product-grid` for this reason. When a clean re-run produces a
diff, open the report, identify the noisy region, and add it to `mask` rather
than raising the global pixel tolerance.

## Sharing diff reports with the team (GitHub Pages)

Non-technical teammates review changes at a single link — no install, no CLI.
Two GitHub Actions workflows drive it:

- **Update baselines** (`.github/workflows/update-baselines.yml`) — captures the
  baselines on the same Linux environment CI uses, then commits them. Run it
  **once after the first push** (the committed baselines were captured on macOS
  and won't match Linux rendering), and again whenever an intentional design
  change should become the new normal.
- **Visual regression report** (`.github/workflows/visual-report.yml`) — compares
  the site against the baselines and publishes the Playwright HTML report
  (expected / actual / highlighted diff) to GitHub Pages. Runs on demand and
  weekly. You can pass a theme **preview URL** when starting it manually.

### One-time setup

1. In the repo: **Settings → Pages → Build and deployment → Source = GitHub
   Actions**.
2. **Actions tab → Update baselines → Run workflow** (regenerates Linux
   baselines and commits them).
3. **Actions tab → Visual regression report → Run workflow** — when it finishes,
   the published URL is in the run summary and at Settings → Pages. Share that
   link with the team; it always shows the latest comparison.

> The Pages site is publicly reachable by anyone with the link. The storefront
> is already public, so the screenshots aren't sensitive — but the URL is not
> gated behind a GitHub login.

### Reviewing a theme change

Deploy/preview the new theme, then **Run workflow** on *Visual regression
report* (paste the preview URL if testing a preview). Open the link and click
any page to see its full-page screenshot. Pages with no change show green;
changed pages additionally show **expected vs actual vs diff** side by side. If
a change is intentional, run *Update baselines* to make it the new normal.

Every test attaches a full-page screenshot (`screenshot: 'on'` in the config),
so the report is also a gallery of the current look — not just a diff viewer
that's blank when nothing changed.

## Notes

- Runs are **serialized** (`workers: 1`) with 2 retries to stay gentle on the
  live store and absorb transient network blips. Bump `workers` in
  `playwright.config.ts` if you point it at a local/staging server.
- `test-results/` and `playwright-report/` are generated and git-ignored; only
  the baseline images under `tests/__screenshots__/` are committed.
- Screenshots are OS/browser-version sensitive. Capture baselines and run
  comparisons on the same platform (or in CI on a fixed runner image) to avoid
  font-rendering diffs.
