import { expect, test } from "@playwright/test";

// Parcours principal sur la vraie base : décrire la cible, lancer le classement, choisir les fonds
// pour le PowerPoint, ouvrir l'aperçu du bandeau. Abenex Capital (SC5 d'acceptance.md, 90 calculé à
// la main) doit apparaître ; son bandeau montre Tethys (2026), lu sur le site d'Abenex.
const sizes = [
  { name: "desktop", width: 1440, height: 900 },
  { name: "mobile", width: 390, height: 844 },
];

for (const size of sizes) {
  test(`screening: form, selection and banner preview (${size.width}x${size.height})`, async ({ page }) => {
    await page.setViewportSize({ width: size.width, height: size.height });
    await page.goto("/");

    // Formulaire vide : les erreurs s'affichent sous les champs, rien n'est envoyé.
    await page.getByRole("button", { name: "Find buyers" }).click();
    await expect(page.getByText("Required").first()).toBeVisible();

    await page.getByLabel("Company name").fill("Industrial SME (example)");
    await page.getByLabel("Website").fill("www.example.com");
    await page.getByLabel("Sector").selectOption("industrials");
    await page.getByLabel("Enterprise value (€m)").fill("40");
    await page.getByLabel("Equity ticket sought (€m)").fill("15");
    await expect(page.getByText("i.e. 38% of EV")).toBeVisible();
    await page.getByRole("button", { name: "Find buyers" }).click();

    const results = page.getByTestId("results");
    await expect(results).toBeVisible({ timeout: 15_000 });
    await expect(results.getByRole("heading", { level: 2 })).toContainText("Industrial SME (example)");
    const count = page.getByTestId("selection-bar").locator("span.text-lg");
    const before = Number((await count.textContent()) ?? "0");
    expect(before).toBeGreaterThan(0);

    await page.getByLabel("Number of funds shown").selectOption("all");
    await page.getByLabel("Search a management company").fill("Abenex");
    const abenex = page.getByTestId("ranking-row").filter({ hasText: "Abenex Capital SAS" });
    await expect(abenex).toContainText("90");

    // Décocher Abenex (Tier 1, coché par défaut) retire un fonds de la sélection.
    await page.getByLabel("Include Abenex Capital SAS in the PowerPoint").uncheck();
    await expect(count).toHaveText(String(before - 1));
    // Étoile « intérêt exprimé » : le fonds revient dans la sélection.
    await page.getByLabel("Interest expressed by Abenex Capital SAS").click();
    await expect(count).toHaveText(String(before));

    // Aperçu du bandeau dans le panneau latéral.
    await abenex.getByRole("button", { name: /^Abenex Capital SAS/ }).click();
    const drawer = page.getByTestId("fund-drawer");
    await expect(drawer).toBeVisible();
    const banner = drawer.getByRole("figure", { name: "PowerPoint banner preview" });
    await expect(banner).toContainText("€[5-20]m");
    await expect(banner).toContainText("Tethys");
    await expect(banner).toContainText("(2026)");
    await expect(drawer.getByText("Why this score")).toBeVisible();
    await page.screenshot({ path: `test-results/screening-${size.name}-${size.width}x${size.height}.png` });
    await page.keyboard.press("Escape");
    await expect(drawer).toBeHidden();
  });
}

test("food deal: DEMEA banner shows its food holdings with descriptions", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await page.getByLabel("Company name").fill("Fabulous French Brasseurs");
  await page.getByLabel("Sector").selectOption("food_beverage");
  await page.getByLabel("Enterprise value (€m)").fill("65");
  await page.getByLabel("Equity ticket sought (€m)").fill("30");
  await page.getByRole("button", { name: "Find buyers" }).click();
  await page.getByTestId("ranking-row").filter({ hasText: "DEMEA Agro SAS" }).getByRole("button", { name: /^DEMEA Agro SAS/ }).click();
  const banner = page.getByTestId("fund-drawer").getByRole("figure", { name: "PowerPoint banner preview" });
  await expect(banner).toContainText("Investments in F&B");
  // Site DEMEA (participations 2026) et sites des sociétés (descriptions), résumés par l'IA.
  await expect(banner.getByTestId("banner-sector")).toContainText("Polaris (2026) - Producer of omega-3 oils");
  await expect(banner.getByTestId("banner-sector")).toContainText("L2PI (2026)");
  // Each banner column sits under its header box (shared grid), and the logo stays inside its column.
  const headBoxes = await banner.getByTestId("banner-grid").locator(":scope > div").evaluateAll((els) =>
    els.slice(0, 6).map((e) => { const r = e.getBoundingClientRect(); return [r.left, r.right]; }),
  );
  const cellBoxes = await banner.getByTestId("banner-grid").locator(":scope > div:nth-child(n+7) > div").evaluateAll((els) =>
    els.map((e) => { const r = e.getBoundingClientRect(); return [r.left, r.right]; }),
  );
  expect(cellBoxes).toHaveLength(6);
  cellBoxes.forEach(([l, r], i) => {
    expect(Math.abs(l - headBoxes[i][0])).toBeLessThan(1.5);
    expect(Math.abs(r - headBoxes[i][1])).toBeLessThan(1.5);
  });
  const logo = banner.getByTestId("banner-logo");
  await expect(logo).toBeVisible();
  const logoBox = (await logo.boundingBox())!;
  expect(logoBox.x).toBeGreaterThanOrEqual(headBoxes[0][0] - 0.5);
  expect(logoBox.x + logoBox.width).toBeLessThanOrEqual(headBoxes[0][1] + 0.5);
  await page.screenshot({ path: "test-results/screening-food-demea-1440x900.png" });
});

test("bulk selection by tier, all and none", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Company name").fill("Target");
  await page.getByLabel("Sector").selectOption("food_beverage");
  await page.getByLabel("Enterprise value (€m)").fill("65");
  await page.getByLabel("Equity ticket sought (€m)").fill("30");
  await page.getByRole("button", { name: "Find buyers" }).click();
  const count = page.getByTestId("selection-bar").locator("span.text-lg");
  const quick = page.getByRole("group", { name: "Quick selection" });
  const tier1 = Number((await count.textContent()) ?? "0"); // Tier 1 coché par défaut
  const tier2Label = (await quick.getByRole("button", { name: /^Tier 2/ }).textContent()) ?? "";
  const tier2 = Number(tier2Label.match(/\((\d+)\)/)?.[1]);
  await quick.getByRole("button", { name: /^Tier 2/ }).click();
  await expect(count).toHaveText(String(tier1 + tier2));
  await quick.getByRole("button", { name: "None" }).click();
  await expect(count).toHaveText("0");
  await quick.getByRole("button", { name: "All" }).click();
  await expect(count).not.toHaveText("0");
});
