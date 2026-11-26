import { expect, test } from "@playwright/test";

// Parcours principal sur la vraie base : décrire la cible, lancer le classement, ouvrir le détail.
// Abenex Capital (SC5 d'acceptance.md, 90 calculé à la main) doit apparaître dans le classement.
const sizes = [
  { name: "desktop", width: 1366, height: 900 },
  { name: "mobile", width: 390, height: 844 },
];

for (const size of sizes) {
  test(`screening: form, ranking and detail (${size.width}x${size.height})`, async ({ page }) => {
    await page.setViewportSize({ width: size.width, height: size.height });
    await page.goto("/");

    // Formulaire vide : les erreurs s'affichent sous les champs, rien n'est envoyé.
    await page.getByRole("button", { name: "Trouver les acquéreurs" }).click();
    await expect(page.getByText("Champ obligatoire").first()).toBeVisible();

    await page.getByLabel("Nom de la société").fill("PME industrielle (exemple)");
    await page.getByLabel("Site internet").fill("www.exemple.fr");
    await page.getByLabel("Secteur").selectOption("industrials");
    await page.getByLabel("Valeur d'entreprise (M€)").fill("40");
    await page.getByLabel("Ticket equity recherché (M€)").fill("15");
    await expect(page.getByText("Soit 38 % de la VE")).toBeVisible();
    await page.getByRole("button", { name: "Trouver les acquéreurs" }).click();

    const results = page.getByTestId("results");
    await expect(results).toBeVisible({ timeout: 15_000 });
    await expect(results.getByRole("heading", { level: 2 })).toContainText("PME industrielle (exemple)");
    await expect(page.getByTestId("ranking-row").first()).toBeVisible();

    await page.getByLabel("Nombre de fonds affichés").selectOption("all");
    await page.getByLabel("Rechercher une société de gestion").fill("Abenex");
    const abenex = page.getByTestId("ranking-row").filter({ hasText: "Abenex Capital SAS" });
    await expect(abenex).toContainText("90");
    await abenex.getByRole("button", { name: "Détail" }).click();
    await expect(page.getByText("Pourquoi ce score")).toBeVisible();
    await expect(page.locator("#detail-fund-001")).toContainText("5–20 M€");

    await page.screenshot({ path: `test-results/screening-${size.name}-${size.width}x${size.height}.png`, fullPage: true });
  });
}
