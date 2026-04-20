import { expect, test } from "@playwright/test";

test("nav: group chip opens dropdown and click item navigates", async ({ page }) => {
  await page.goto("/");
  const chip = page.getByRole("button", { name: /stats|số liệu|statistik|統計|通計|통계/i }).first();
  await expect(chip).toBeVisible();
  await chip.click();

  const menu = page.getByRole("menu").first();
  await expect(menu).toBeVisible();

  // Click a sub-item (xG Table) and verify navigation.
  const tableLink = menu.getByRole("menuitem", { name: /xg table|bảng xh|ตาราง|xg|순위/i }).first();
  await expect(tableLink).toBeVisible();
  await tableLink.click();
  await expect(page).toHaveURL(/\/table/);
});

test("nav: click outside closes dropdown", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /bets|kèo|แทง|投注|베팅/i }).first().click();
  await expect(page.getByRole("menu").first()).toBeVisible();

  // Click in the main content area (outside header).
  await page.locator("main").first().click();
  await expect(page.getByRole("menu")).toHaveCount(0);
});
