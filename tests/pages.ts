/**
 * One representative page per Shopify template.
 *
 * Visual regressions live in templates and sections, not in individual
 * products — so we capture one example of each template rather than every
 * URL. Add more entries here as the theme grows (extra sections, landing
 * pages, etc.).
 *
 * `mask` lists CSS selectors for regions whose content legitimately changes
 * between runs (carousels, "recently viewed", live stock). Masked regions are
 * painted over with a solid box before comparison, so they never trigger a
 * false diff. Start empty and add selectors once you see noisy diffs in the
 * report.
 */
export type PageDef = {
  /** Slug used for the screenshot file name. */
  name: string;
  /** Path relative to BASE_URL. */
  path: string;
  /** Human-readable Shopify template this page exercises. */
  template: string;
  /** CSS selectors of dynamic regions to mask out of the comparison. */
  mask?: string[];
  /** Expected HTTP status (defaults to 200; the 404 page expects 404). */
  expectStatus?: number;
};

export const pages: PageDef[] = [
  { name: "home", path: "/", template: "index" },
  { name: "collection", path: "/collections/furniture", template: "collection" },
  {
    name: "product",
    path: "/products/fotel-zen-claude-brisson-ligne-roset-francja-lata-80",
    template: "product",
  },
  { name: "page-about", path: "/pages/about-us", template: "page" },
  { name: "page-contact", path: "/pages/contact-us", template: "page.contact" },
  { name: "blog", path: "/blogs/news", template: "blog" },
  { name: "cart", path: "/cart", template: "cart" },
  {
    name: "search",
    path: "/search?q=lampa",
    template: "search",
    // Result thumbnails decode at slightly different times and results can
    // reorder; the product card itself is covered by the collection page.
    mask: ["#product-grid"],
  },
  { name: "login", path: "/account/login", template: "customers/login" },
  {
    name: "not-found",
    path: "/this-page-intentionally-does-not-exist",
    template: "404",
    expectStatus: 404,
  },
];
