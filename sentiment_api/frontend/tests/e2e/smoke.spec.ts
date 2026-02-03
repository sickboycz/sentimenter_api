import { test, expect } from "@playwright/test";

test("overview loads", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Sentimeter").first()).toBeVisible({ timeout: 15000 });
  await page.screenshot({ path: "test-artifacts/screenshots/overview.png", fullPage: true });
});

test("news loads", async ({ page }) => {
  await page.goto("/news");
  await expect(page.getByText("News Feed")).toBeVisible();
  await page.screenshot({ path: "test-artifacts/screenshots/news.png", fullPage: true });
});

test("ops page loads", async ({ page }) => {
  await page.goto("/ops");
  await expect(page.getByText("Ops", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("System Overview")).toBeVisible();
  await page.screenshot({ path: "test-artifacts/screenshots/ops.png", fullPage: true });
});

test("health / system overview visible on ops", async ({ page }) => {
  await page.goto("/ops");
  await expect(page.getByText("System Overview")).toBeVisible();
  await expect(page.getByText("Queue Activity")).toBeVisible();
  await expect(page.getByText("System Counts")).toBeVisible();
});
