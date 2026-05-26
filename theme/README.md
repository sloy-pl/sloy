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

The visual-regression suite that guards this theme lives in `../tests/`.
