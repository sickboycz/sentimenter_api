import { test, expect } from "@playwright/test";

test("overview loads", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Sentimeter Dashboard")).toBeVisible();
  await page.screenshot({ path: "test-artifacts/screenshots/overview.png", fullPage: true });
});

test("news loads", async ({ page }) => {
  await page.goto("/news");
  await expect(page.getByText("News Feed")).toBeVisible();
  await page.screenshot({ path: "test-artifacts/screenshots/news.png", fullPage: true });
});
