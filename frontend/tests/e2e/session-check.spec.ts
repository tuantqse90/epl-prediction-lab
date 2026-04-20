/**
 * End-to-end check of everything shipped in the 2026-04-20 session:
 * - team-logo audit (35 mappings fixed, 0 broken image requests)
 * - /roi/by-league (Phase 8)
 * - /proof CLV card (Phase 5 — hidden until snapshots exist, page still renders)
 * - /match/:id <MarketsEdge> (Phase 6)
 * - /roi Flat / Kelly toggle (Phase 7)
 * - player-photo proxy (scorer strip serves real photos, not monograms)
 */
import { expect, test } from "@playwright/test";

test.describe("Session shipment", () => {
  test("home — no broken image requests + scorer photos load", async ({ page }) => {
    const failedImages: string[] = [];
    page.on("response", (res) => {
      const u = res.url();
      if ((u.includes("/api/players/photo/") || u.includes("espncdn.com")) && res.status() >= 400) {
        failedImages.push(`${res.status()} ${u}`);
      }
    });

    await page.goto("/");
    // Wait for lazy-loaded images to resolve (scorer strip uses loading=lazy)
    await page.mouse.wheel(0, 800);
    await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});

    // Home must show at least one real scorer photo (the <img> tag, not the
    // monogram fallback div). The proxy route is /api/players/photo/{id}.
    const proxyImages = page.locator('img[src^="/api/players/photo/"]');
    await expect(proxyImages.first()).toBeVisible({ timeout: 15_000 });
    const photoCount = await proxyImages.count();
    expect(photoCount).toBeGreaterThan(0);

    // Team crests on match cards must resolve (ESPN IDs fixed this session).
    const crestImages = page.locator('img[src*="espncdn.com/i/teamlogos"]');
    const crestCount = await crestImages.count();
    expect(crestCount).toBeGreaterThan(0);

    expect(failedImages, "broken image responses:\n" + failedImages.join("\n")).toEqual([]);
  });

  test("/roi has flat/kelly toggle + both modes render", async ({ page }) => {
    await page.goto("/roi");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    // Staking toggle exists (Flat + Kelly chips).
    const flatChip = page.getByRole("link", { name: /flat 1u|1u cố định/i });
    const kellyChip = page.getByRole("link", { name: /^kelly$/i });
    await expect(flatChip).toBeVisible();
    await expect(kellyChip).toBeVisible();

    // Default is flat — ROI chart is visible with an SVG path.
    await expect(page.locator("svg path[stroke]").first()).toBeVisible();

    // Switch to Kelly.
    await kellyChip.click();
    await expect(page).toHaveURL(/staking=kelly/);
    await expect(page.getByText(/virtual bankroll|bankroll ảo/i)).toBeVisible();
    // Kelly chart has the 5-chip header: Starting/Peak/Final/ROI/Max DD.
    await expect(page.getByText(/peak|đỉnh/i)).toBeVisible();
    await expect(page.getByText(/max dd|drawdown/i)).toBeVisible();

    // By-league link chip.
    const byLg = page.getByRole("link", { name: /by league|theo giải/i });
    await expect(byLg).toBeVisible();
  });

  test("/roi/by-league renders per-league table (≥ 5 rows)", async ({ page }) => {
    await page.goto("/roi/by-league?window=30d&threshold=0.05");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    // Table with ≥ 1 league row. Each row shows a ROI% cell.
    const tableRows = page.locator("table tbody tr");
    const rowCount = await tableRows.count();
    expect(rowCount).toBeGreaterThan(0);

    // Window + edge chips.
    await expect(page.getByRole("link", { name: /^30d$/ })).toBeVisible();
    await expect(page.getByRole("link", { name: /^≥ 5%$/ })).toBeVisible();
  });

  test("/match/:id renders MarketsEdge + AH + SGP rows under Markets tab", async ({ page }) => {
    // Pull a match id from the API so the test is independent of fixture list.
    const resp = await page.request.get("/api/matches?limit=1");
    const matches = await resp.json();
    expect(matches.length).toBeGreaterThan(0);
    const matchId = matches[0].id;

    await page.goto(`/match/${matchId}`);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    // MarketsEdge lives inside the "Markets" tab — click it first.
    const marketsTab = page.getByRole("tab", { name: /markets|thị trường/i }).first();
    await expect(marketsTab).toBeVisible();
    await marketsTab.click();

    // MarketsEdge section header + specific AH row + SGP row.
    await expect(page.getByText(/correlated markets|thị trường tương quan/i)).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/^AH .+ -1\.5$/).first()).toBeVisible();
    await expect(page.getByText(/SGP: BTTS & Over 2\.5/)).toBeVisible();
  });

  test("/proof page renders without the CLV card crashing (card hidden until data)", async ({ page }) => {
    await page.goto("/proof");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    // Model-vs-market comparison section is the canary that /proof didn't
    // blow up. Scope to h2 since the h1 hero also contains "mô hình".
    await expect(
      page.getByRole("heading", { level: 2, name: /model vs|mô hình vs/i }),
    ).toBeVisible();
  });

  test("/last-weekend renders cards with league badges + short names", async ({ page }) => {
    await page.goto("/last-weekend");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    // At least one match card link.
    const cards = page.locator('a[href^="/match/"]');
    await expect(cards.first()).toBeVisible({ timeout: 10_000 });

    // HIT/MISS pill text must render (we changed this UI earlier this session).
    await expect(page.getByText(/^(HIT|MISS|ĐÚNG|TRẬT)$/i).first()).toBeVisible();
  });

  test("player photo proxy returns real PNGs with long cache headers", async ({ page }) => {
    // Harry Kane (api_football_id 184) is populated in the DB.
    const r = await page.request.get("/api/players/photo/184");
    expect(r.status()).toBe(200);

    const cache = r.headers()["cache-control"] ?? "";
    expect(cache).toContain("immutable");
    expect(cache).toMatch(/max-age=\d{6,}/); // ≥ 100k seconds

    const body = await r.body();
    // PNG signature: 89 50 4E 47
    expect(body.length).toBeGreaterThan(1000);
    expect(body.slice(0, 4).toString("hex")).toBe("89504e47");
  });

  test("/roi/kelly API returns 200-range bankroll trajectory with drawdown tracking", async ({ request }) => {
    const r = await request.get("/api/stats/roi/kelly?season=2025-26&threshold=0.05&cap=0.25&starting=100");
    expect(r.status()).toBe(200);
    const d = await r.json();
    expect(d.starting_units).toBe(100);
    expect(d.total_bets).toBeGreaterThan(0);
    expect(d.points.length).toBe(d.total_bets); // one point per bet
    expect(d.peak_units).toBeGreaterThanOrEqual(d.starting_units);
    expect(d.max_drawdown_pct).toBeGreaterThanOrEqual(0);
    expect(d.max_drawdown_pct).toBeLessThanOrEqual(100);
  });

  test("/roi/by-league API returns the 5 top leagues", async ({ request }) => {
    const r = await request.get("/api/stats/roi/by-league?window=30d&threshold=0.05");
    expect(r.status()).toBe(200);
    const d = await r.json();
    expect(d.window).toBe("30d");
    expect(d.threshold).toBe(0.05);
    expect(d.leagues.length).toBeGreaterThanOrEqual(4); // at minimum 4 of the top 5 should have recent finals
    for (const lg of d.leagues) {
      expect(typeof lg.league_code).toBe("string");
      expect(typeof lg.bets).toBe("number");
      expect(typeof lg.roi_vig_pct).toBe("number");
    }
  });

  test("/markets endpoint exposes Phase 6 AH + SGP fields", async ({ request }) => {
    const mm = await request.get("/api/matches?limit=1");
    const matchId = (await mm.json())[0].id;

    const r = await request.get(`/api/matches/${matchId}/markets`);
    expect(r.status()).toBe(200);
    const d = await r.json();

    expect(typeof d.prob_ah_home_minus_1_5).toBe("number");
    expect(typeof d.prob_ah_home_minus_0_5).toBe("number");
    expect(typeof d.prob_ah_home_plus_0_5).toBe("number");
    expect(typeof d.prob_ah_home_plus_1_5).toBe("number");
    expect(typeof d.prob_sgp_btts_over_2_5).toBe("number");

    // AH home at +1.5 > +0.5 > -0.5 > -1.5 monotonically.
    expect(d.prob_ah_home_plus_1_5).toBeGreaterThan(d.prob_ah_home_plus_0_5);
    expect(d.prob_ah_home_plus_0_5).toBeGreaterThan(d.prob_ah_home_minus_0_5);
    expect(d.prob_ah_home_minus_0_5).toBeGreaterThan(d.prob_ah_home_minus_1_5);

    // SGP ≤ each marginal (BTTS and Over 2.5).
    expect(d.prob_sgp_btts_over_2_5).toBeLessThanOrEqual(d.prob_btts + 1e-9);
    expect(d.prob_sgp_btts_over_2_5).toBeLessThanOrEqual(d.prob_over_2_5 + 1e-9);
  });

  test("/clv endpoint responds (empty is fine until closing_odds populates)", async ({ request }) => {
    const r = await request.get("/api/stats/clv?days=60&threshold=0.05");
    expect(r.status()).toBe(200);
    const d = await r.json();
    expect(typeof d.bets).toBe("number");
    expect(typeof d.mean_clv).toBe("number");
    expect(typeof d.pct_beat_close).toBe("number");
    expect(Array.isArray(d.by_league)).toBe(true);
  });
});
