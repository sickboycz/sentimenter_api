import { test, expect } from "@playwright/test";

// E2E tests require frontend + API running (e.g. docker compose up)
// Set E2E_BASE_URL=http://localhost:3000 and skip webServer in config when using Docker

test.describe("pages load", () => {
  test("overview page", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("body")).toBeVisible();
    await expect(page.locator("text=Overview").or(page.locator("h1"))).toBeVisible({ timeout: 10000 });
  });

  test("news page", async ({ page }) => {
    await page.goto("/news");
    await expect(page.locator("body")).toBeVisible();
  });

  test("topics page", async ({ page }) => {
    await page.goto("/topics");
    await expect(page.locator("body")).toBeVisible();
  });

  test("ops page", async ({ page }) => {
    await page.goto("/ops");
    await expect(page.locator("body")).toBeVisible();
  });

  test("sources page", async ({ page }) => {
    await page.goto("/sources");
    await expect(page.locator("body")).toBeVisible();
  });
});
