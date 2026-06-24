#!/usr/bin/env node
// Migrate per-theme content translations (e.g. Polish) from an OLD Shopify
// theme to a NEW one via the Admin GraphQL API. Theme-editor content (section
// text, button labels in templates/*.json) is translated as DB records bound to
// a specific theme, so it does NOT follow a theme migration — this re-registers
// it onto the new theme. Store-level translations (products, pages, menus) are
// theme-independent and are left untouched.
//
// Requires Node 18+ (global fetch) and an Admin API access token whose app has
// scopes: read_themes, read_translations, write_translations.
// Get the token from a Dev Dashboard app via the client-credentials grant
// (POST https://<shop>/admin/oauth/access_token) -- it is valid for 24h. The
// legacy in-admin "Develop apps" shpat_ token has been retired.
//
// Usage (three passes):
//   1) list themes:   SHOP=foo.myshopify.com ADMIN_TOKEN=shpat_... node scripts/migrate-theme-translations.mjs
//   2) dry run:       SHOP=... ADMIN_TOKEN=... SOURCE_THEME_ID=<old> TARGET_THEME_ID=<new> node scripts/migrate-theme-translations.mjs
//   3) apply:         ... APPLY=1 node scripts/migrate-theme-translations.mjs

const SHOP   = process.env.SHOP;                 // your-store.myshopify.com
const TOKEN  = process.env.ADMIN_TOKEN;          // shpat_... custom app token
const LOCALE = process.env.LOCALE || "pl";
const SRC    = process.env.SOURCE_THEME_ID;      // numeric id of OLD theme
const DST    = process.env.TARGET_THEME_ID;      // numeric id of NEW (published) theme
const APPLY  = process.env.APPLY === "1";        // dry-run unless APPLY=1

if (!SHOP || !TOKEN) {
  console.error("Set SHOP and ADMIN_TOKEN env vars. See header for usage.");
  process.exit(1);
}

const API = `https://${SHOP}/admin/api/2026-01/graphql.json`;

// Merchant-authored content (section text, button labels, page/product copy).
// This is the layer that does NOT survive a theme migration -- always migrate it.
const CONTENT_TYPES = [
  "ONLINE_STORE_THEME_JSON_TEMPLATE",
  "ONLINE_STORE_THEME_SECTION_GROUP",
  "ONLINE_STORE_THEME_SETTINGS_DATA_SECTIONS",
  "ONLINE_STORE_THEME_SETTINGS_CATEGORY",
];
// Theme UI defaults = the contents of locales/*.json, already shipped with the
// theme in git. Migrating these turns file-based defaults into per-theme DB
// overrides, so they're opt-in only (INCLUDE_LOCALE=1).
const LOCALE_TYPES = ["ONLINE_STORE_THEME", "ONLINE_STORE_THEME_LOCALE_CONTENT"];
const TYPES = process.env.INCLUDE_LOCALE === "1"
  ? [...CONTENT_TYPES, ...LOCALE_TYPES]
  : CONTENT_TYPES;

const gql = async (query, variables = {}) => {
  const r = await fetch(API, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Shopify-Access-Token": TOKEN },
    body: JSON.stringify({ query, variables }),
  });
  const j = await r.json();
  if (j.errors) throw new Error(JSON.stringify(j.errors, null, 2));
  return j.data;
};

async function* resources(type) {
  let after = null;
  do {
    const d = await gql(
      `query($t:TranslatableResourceType!,$a:String,$l:String!){
        translatableResources(first:100,resourceType:$t,after:$a){
          pageInfo{ hasNextPage endCursor }
          nodes{
            resourceId
            translatableContent{ key digest }
            translations(locale:$l){ key value }
          } } }`,
      { t: type, a: after, l: LOCALE }
    );
    const c = d.translatableResources;
    for (const n of c.nodes) yield n;
    after = c.pageInfo.hasNextPage ? c.pageInfo.endCursor : null;
  } while (after);
}

// translatableResources (the list query) only returns the PUBLISHED theme, but
// theme resource ids embed the theme id (e.g. ...JsonTemplate/index?theme_id=N).
// So we list the published (target) theme's resources, rewrite each id to the
// source theme, and read that source resource directly with the singular
// translatableResource query -- which works for unpublished themes too.
const toSource = (targetId) => targetId.replaceAll(DST, SRC);

const sourceTranslations = async (srcId) => {
  const d = await gql(
    `query($id:ID!,$l:String!){
      translatableResource(resourceId:$id){ translations(locale:$l){ key value } } }`,
    { id: srcId, l: LOCALE }
  );
  return d.translatableResource?.translations ?? [];
};

(async () => {
  if (!SRC || !DST) {
    const t = await gql(`{ themes(first:50){ nodes{ id name role } } }`);
    console.log("Themes (use the numeric part of the id):");
    for (const n of t.themes.nodes) {
      console.log(`  ${n.id.replace("gid://shopify/OnlineStoreTheme/", "")}  [${n.role}]  ${n.name}`);
    }
    console.log("\nSet SOURCE_THEME_ID (old) and TARGET_THEME_ID (new), then re-run.");
    return;
  }

  if (process.env.INSPECT === "1") {
    for (const type of TYPES) {
      let count = 0, hasSrc = 0, hasDst = 0;
      const samples = [];
      for await (const n of resources(type)) {
        count++;
        if (n.resourceId.includes(SRC)) hasSrc++;
        if (n.resourceId.includes(DST)) hasDst++;
        if (samples.length < 4) samples.push(n.resourceId);
      }
      console.log(`\n${type}: ${count} resources  (contain SRC ${SRC}: ${hasSrc}, DST ${DST}: ${hasDst})`);
      for (const s of samples) console.log(`   ${s}`);
    }
    return;
  }

  let planned = 0, applied = 0, emptySrc = 0;
  for (const type of TYPES) {
    for await (const t of resources(type)) {          // t = target (published) resource
      if (!t.resourceId.includes(DST)) continue;       // safety: only published-theme ids
      const srcTr = await sourceTranslations(toSource(t.resourceId));
      if (!srcTr.length) { emptySrc++; continue; }
      const digest = Object.fromEntries(t.translatableContent.map((c) => [c.key, c.digest]));
      const tr = srcTr
        .filter((x) => x.value && digest[x.key])
        .map((x) => ({ locale: LOCALE, key: x.key, value: x.value, translatableContentDigest: digest[x.key] }));
      if (!tr.length) continue;

      planned += tr.length;
      console.log(`${APPLY ? "WRITE" : "DRY  "} ${type}  ${t.resourceId}  (+${tr.length})`);
      if (APPLY) {
        const r = await gql(
          `mutation($id:ID!,$t:[TranslationInput!]!){
            translationsRegister(resourceId:$id,translations:$t){ userErrors{ message field } } }`,
          { id: t.resourceId, t: tr }
        );
        const errs = r.translationsRegister.userErrors;
        if (errs.length) console.error("  userErrors:", errs);
        else applied += tr.length;
      }
    }
  }
  console.log(`\n${APPLY ? `Applied ${applied}/${planned}` : `Would write ${planned}`} ${LOCALE} translations.` +
    (emptySrc ? `  (${emptySrc} target resources had no source ${LOCALE} translations)` : ""));
})();
