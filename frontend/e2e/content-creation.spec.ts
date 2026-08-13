import { test, expect, type Page } from "@playwright/test";

/**
 * ContentForge UI E2E smoke — Content-creation 4-step wizard.
 *
 * Checks against the live Vite dev server (5173) proxying to the real
 * contentforge backend (8099):
 *   - #content-creation route loads without console errors
 *   - step 1 renders source selection + platform checkboxes
 *   - wizard progress indicator visible
 *
 * Uses domcontentloaded + settle waits (SPA, hash routing).
 */

const CONTENT_CREATION_URL = "http://127.0.0.1:5173/#content-creation";

async function collectErrors(page: Page): Promise<string[]> {
  const errors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });
  page.on("pageerror", (err) => errors.push(String(err)));
  return errors;
}

test("content-creation page loads without console errors", async ({ page }) => {
  const errors = await collectErrors(page);
  await page.goto(CONTENT_CREATION_URL);
  await page.waitForLoadState("domcontentloaded");
  await page.waitForTimeout(1500);

  await expect(page).toHaveURL(/#content-creation/);
  await expect(page.getByRole("heading", { name: "Content packages" })).toBeVisible();
  await expect(page.getByText(/step 1 of 4/i)).toBeVisible();
  expect(errors).toEqual([]);
});

test("wizard renders source input and platform checkboxes", async ({ page }) => {
  await page.goto(CONTENT_CREATION_URL);
  await page.waitForLoadState("domcontentloaded");
  await page.waitForTimeout(1500);

  await expect(page.getByLabel("Source asset")).toBeVisible();
  await expect(page.getByLabel(/Platform LinkedIn/)).toBeVisible();
  await expect(page.getByLabel(/Platform Twitter/)).toBeVisible();
});
