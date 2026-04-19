import { expect, test } from "@playwright/test";

// These run against production by default. Each test is fast (< 5s on a warm
// cache) and stays idempotent — no state writes — so they're safe to run
// on every deploy or on a cron.

test("home renders with styled layout", async ({ page }) => {
  await page.goto("/");
  // Stylesheet present and body has our color token (not browser default).
  const bg = await page.evaluate(() =>
    getComputedStyle(document.body).backgroundColor,
  );
  // surface token is rgb(0, 0, 0); tailwind may also emit as
  // "rgba(0, 0, 0, 1)" depending on browser. Accept either.
  expect(bg).toMatch(/rgb(a)?\(0,\s*0,\s*0/);

  // Hero + at least one match card anchor rendered.
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  const matchLinks = page.locator('a[href^="/match/"]');
  await expect(matchLinks.first()).toBeVisible({ timeout: 10_000 });
});

test("clicking a match card navigates to the detail page", async ({ page }) => {
  await page.goto("/");

  const firstCard = page.locator('a[href^="/match/"]').first();
  await expect(firstCard).toBeVisible();
  const href = await firstCard.getAttribute("href");
  await firstCard.click();

  // URL updates + detail hero renders with the team names.
  await expect(page).toHaveURL(new RegExp(`${href}$`));
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

  // At least one tab from MatchTabs renders (Preview/Markets/Analysis/Community).
  await expect(page.getByRole("tab").first()).toBeVisible();
});

test("language toggle switches dictionary", async ({ page }) => {
  await page.goto("/");

  const selector = page.getByRole("combobox", { name: /language/i });
  await expect(selector).toBeVisible();
  await selector.selectOption("en");

  // After EN, the dashboard headline appears in English (contains "fixtures").
  await expect(
    page.getByRole("heading", { name: /fixtures/i, level: 1 }),
  ).toBeVisible();
});

test("/news page lists recent headlines", async ({ page }) => {
  await page.goto("/news");
  // Headline links target external sources, so we just check count > 0.
  const items = page.locator('a[href^="http"]:has(p)');
  await expect(items.first()).toBeVisible({ timeout: 10_000 });
  const count = await items.count();
  expect(count).toBeGreaterThan(5);
});

test("benchmark page renders accuracy numbers", async ({ page }) => {
  await page.goto("/benchmark");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  // Expect at least one percentage number (accuracy tile).
  await expect(page.getByText(/%/).first()).toBeVisible();
});
