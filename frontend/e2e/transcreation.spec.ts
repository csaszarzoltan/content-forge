import { test, expect, type Page } from "@playwright/test";

/**
 * ContentForge UI E2E smoke — Transcreate review flow.
 *
 * Checks against the live Vite dev server (5173) proxying to the real
 * contentforge backend (8099):
 *   - Transcreate route loads without console errors
 *   - adapt() renders the side-by-side diff + low-confidence flag
 *   - per-segment accept resolves the flag and unlocks export
 *
 * Uses domcontentloaded + settle waits (SPA, hash routing).
 */

const TRANSCREATE_URL = "http://127.0.0.1:5173/#transcreation";

async function collectErrors(page: Page): Promise<string[]> {
  const errors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });
  page.on("pageerror", (err) => errors.push(String(err)));
  return errors;
}

test("transcreate page loads without console errors", async ({ page }) => {
  const errors = await collectErrors(page);
  await page.goto(TRANSCREATE_URL);
  await page.waitForLoadState("domcontentloaded");
  await page.waitForTimeout(1500);

  await expect(page).toHaveURL(/#transcreation/);
  await expect(page.getByRole("heading", { name: "Transcreate" })).toBeVisible();
  await expect(page.getByLabel("Source text")).toBeVisible();
  await expect(page.getByRole("button", { name: "Adapt" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Analyze risks" })).toBeVisible();
  expect(errors).toEqual([]);
});

test("adapt flow renders side-by-side diff and flags low confidence", async ({ page }) => {
  const errors = await collectErrors(page);
  await page.goto(TRANSCREATE_URL);
  await page.waitForLoadState("domcontentloaded");

  await page.getByLabel("Source text").fill(
    "It's raining cats and dogs. The report is ready.",
  );
  await page.getByRole("button", { name: "Adapt" }).click();

  // Adapted result panel
  await expect(page.getByTestId("adapted-text")).toContainText("Es regnet in Strömen");
  // Side-by-side columns for segment 1 (scoped to the segment review panel)
  const segReview = page.locator("section[aria-label=\"Segment review\"]");
  await expect(segReview.getByText("It's raining cats and dogs.", { exact: true })).toBeVisible();
  await expect(segReview.getByText("Es regnet Katzen und Hunde.", { exact: true })).toBeVisible();
  await expect(segReview.getByText("Es regnet in Strömen.", { exact: true })).toBeVisible();
  // Low-confidence flag
  await expect(page.locator(".tc-segment.flagged")).toHaveCount(1);
  await expect(page.locator(".tc-segment.flagged .tc-flag")).toContainText(
    "Low confidence (65%) — review required",
  );
  // Per-segment controls
  await expect(page.locator(".tc-segment .tc-seg-btns button", { hasText: "Accept" }).first()).toBeVisible();
  await expect(page.locator(".tc-segment .tc-seg-btns button", { hasText: "Edit" }).first()).toBeVisible();
  await expect(page.locator(".tc-segment .tc-seg-btns button", { hasText: "Reject" }).first()).toBeVisible();
  // Export hint (no asset → button hidden, but hint about resolution shown for banner)
  await expect(page.locator(".tc-flag-banner")).toContainText("flagged for review");
  expect(errors).toEqual([]);
});

test("accepting the flagged segment resolves it and flips the banner", async ({ page }) => {
  const errors = await collectErrors(page);
  await page.goto(TRANSCREATE_URL);
  await page.waitForLoadState("domcontentloaded");

  await page.getByLabel("Source text").fill(
    "It's raining cats and dogs. The report is ready.",
  );
  await page.getByRole("button", { name: "Adapt" }).click();
  await expect(page.locator(".tc-segment.flagged")).toHaveCount(1);

  await page.locator(".tc-segment.flagged button", { hasText: "Accept" }).click();
  await expect(page.locator(".tc-segment.flagged")).toHaveCount(0);
  await expect(page.locator(".tc-segment.resolved")).toHaveCount(1);
  await expect(page.locator(".tc-flag-clear")).toContainText("All segments reviewed");
  expect(errors).toEqual([]);
});
