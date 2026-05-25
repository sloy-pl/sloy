import type { Page } from "@playwright/test";

/**
 * Bring a freshly-loaded page into a stable, screenshot-ready state:
 * dismiss the cookie banner, kill animations, trigger lazy-loaded images,
 * and wait for fonts/network to settle.
 */
export async function preparePage(page: Page): Promise<void> {
  await dismissCookieBanner(page);
  await freezePage(page);
  await loadLazyImages(page);
  // Wait for fonts, but never block the whole test on it.
  await Promise.race([
    page.evaluate(() => document.fonts.ready),
    page.waitForTimeout(5000),
  ]);
  // A fixed settle beats `networkidle`, which rarely fires on a storefront
  // full of analytics/marketing beacons.
  await page.waitForTimeout(800);
}

/**
 * Dismiss the cookie consent bar. The bar renders a moment after load
 * (later on mobile/WebKit), so we wait for the accept button to appear,
 * click it, then wait for the bar to disappear.
 */
async function dismissCookieBanner(page: Page): Promise<void> {
  const accept = page
    .getByRole("button", { name: /^(Akceptuj|Akceptuję|Zgadzam się|Accept|I agree)/i })
    .first();
  try {
    await accept.waitFor({ state: "visible", timeout: 6000 });
    await accept.click({ timeout: 3000 });
    // Confirm the bar is gone so it can't shift layout in the screenshot.
    await accept.waitFor({ state: "hidden", timeout: 3000 }).catch(() => {});
    await page.waitForTimeout(300);
  } catch {
    // No banner appeared (e.g. already accepted) — nothing to do.
  }
}

/** Disable animations, transitions, smooth scroll and the caret. */
async function freezePage(page: Page): Promise<void> {
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation-duration: 0s !important;
        animation-delay: 0s !important;
        transition-duration: 0s !important;
        transition-delay: 0s !important;
        scroll-behavior: auto !important;
      }
      html { scroll-behavior: auto !important; }
    `,
  });
}

/** Scroll the full height to trigger lazy/intersection-observed images. */
async function loadLazyImages(page: Page): Promise<void> {
  await page.evaluate(async () => {
    const step = window.innerHeight;
    const height = document.body.scrollHeight;
    for (let y = 0; y < height; y += step) {
      window.scrollTo(0, y);
      await new Promise((r) => setTimeout(r, 150));
    }
    window.scrollTo(0, 0);
  });
  // Wait for any <img> still loading after the scroll, but cap the wait so a
  // lazy/tracking pixel that never fires `load` can't hang the whole test.
  await page
    .evaluate(() => {
      const pending = Array.from(document.images)
        .filter((img) => !img.complete)
        .map(
          (img) =>
            new Promise<void>((resolve) => {
              img.addEventListener("load", () => resolve());
              img.addEventListener("error", () => resolve());
            }),
        );
      const cap = new Promise<void>((resolve) => setTimeout(resolve, 8000));
      return Promise.race([Promise.all(pending), cap]);
    })
    .catch(() => {});
}
