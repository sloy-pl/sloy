import { test, expect } from "@playwright/test";
import { pages } from "./pages";
import { preparePage } from "./helpers";

for (const def of pages) {
  test(`${def.template} — ${def.name}`, async ({ page }) => {
    const response = await page.goto(def.path, { waitUntil: "domcontentloaded" });

    if (def.expectStatus) {
      expect(response?.status(), `unexpected status for ${def.path}`).toBe(def.expectStatus);
    }

    await preparePage(page);

    // The cookie bar is dismissed in preparePage(); per-page `mask` selectors
    // cover any remaining dynamic regions (carousels, live stock, etc.).
    const mask = (def.mask ?? []).map((selector) => page.locator(selector));

    await expect(page).toHaveScreenshot(`${def.name}.png`, {
      fullPage: true,
      mask,
    });
  });
}
