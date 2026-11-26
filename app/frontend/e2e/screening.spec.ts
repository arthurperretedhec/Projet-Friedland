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
    const count = page.getByTestId("selection-bar").locator("span.text-lg");
    const before = Number((await count.textContent()) ?? "0");
    expect(before).toBeGreaterThan(0);

    await page.getByLabel("Nombre de fonds affichés").selectOption("all");
    await page.getByLabel("Rechercher une société de gestion").fill("Abenex");
    const abenex = page.getByTestId("ranking-row").filter({ hasText: "Abenex Capital SAS" });
    await expect(abenex).toContainText("90");

    // Décocher Abenex (Tier 1, coché par défaut) retire un fonds de la sélection.
    await page.getByLabel("Inclure Abenex Capital SAS dans le PowerPoint").uncheck();
    await expect(count).toHaveText(String(before - 1));
    // Étoile « intérêt exprimé » : le fonds revient dans la sélection.
    await page.getByLabel("Intérêt exprimé par Abenex Capital SAS").click();
    await expect(count).toHaveText(String(before));

    // Aperçu du bandeau dans le panneau latéral.
    await abenex.getByRole("button", { name: /^Abenex Capital SAS/ }).click();
    const drawer = page.getByTestId("fund-drawer");
    await expect(drawer).toBeVisible();
    const banner = drawer.getByRole("figure", { name: "Aperçu du bandeau PowerPoint" });
    await expect(banner).toContainText("€[5-20]m");
    await expect(banner).toContainText("Tethys");
    await expect(banner).toContainText("(2026)");
    await expect(drawer.getByText("Pourquoi ce score")).toBeVisible();
    await page.screenshot({ path: `test-results/screening-${size.name}-${size.width}x${size.height}.png` });
    await page.keyboard.press("Escape");
    await expect(drawer).toBeHidden();
  });
}
