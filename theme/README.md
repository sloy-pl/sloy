# sloy.pl theme

The Shopify **Dawn** theme deployed to sloy.pl. This directory is the deployed
artifact — everything under `theme/` ships to the live theme.

## Workflow

```bash
# Pull the current live theme into this directory (first-time population)
shopify theme pull --path theme

# Local dev server against the theme
shopify theme dev --path theme

# Lint
shopify theme check --path theme

# Push to Shopify (normally done by CI, see .github/workflows/deploy-theme.yml)
shopify theme push --path theme
```

Auth uses a Theme Access app password via `SHOPIFY_CLI_THEME_TOKEN` and the
store domain via `SHOPIFY_FLAG_STORE`.

## Deploy = full push, don't edit in-store

This repo is the source of truth. Deploy by pushing the **whole** directory —
never a hand-picked subset:

```bash
shopify theme push --path theme
```

Why it matters:

- **Templates reference custom blocks.** `templates/*.json` point at custom
  blocks like `blocks/ai_gen_block_17c5840.liquid`. A partial push that ships a
  template without its block (or vice versa) renders broken. A full push keeps
  them in sync.
- **Block colors live in the template JSON, not in theme settings.** The pink /
  purple homepage tiles (`tile_1_bg_color` / `tile_2_bg_color`) are stored
  inline in `templates/index.json`, not in a color scheme. Pushing the committed
  JSON reproduces them exactly; recreating the block in the store editor falls
  back to the schema defaults in the block's `.liquid` and loses them.
- **Treat the store editor as read-only after deploy.** Edits made there diverge
  from the repo and get clobbered on the next push. After the first push to a new
  theme, `shopify theme pull` into a scratch dir and diff against this one to
  confirm nothing fell back to defaults.

The visual-regression suite that guards this theme lives in `../tests/`.
