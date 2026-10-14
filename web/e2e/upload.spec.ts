import path from "node:path";
import { expect, test, type Page } from "@playwright/test";

// The whole upload flow through the real page and the real API, with the sample bank exports in samples/.
// Expected numbers come from samples/expected.json, which make_samples.py works out by construction.
// OWNER_SAMPLE_CSV (optional): the owner's own export; skipped when it is not set.
const SAMPLES = path.resolve(__dirname, "../../samples");

async function chooseDates(page: Page, start: string, end: string) {
  await page.getByLabel("Start date").fill(start);
  await page.getByLabel("End date").fill(end);
}

for (const [file, convention, note] of [
  ["sample-transactions.csv", null, null],
  ["sample-split-columns.csv", "Money out and money in columns", "columns named “Money out” and “Money in”"],
  ["sample-type-column.csv", "A column says debit or credit", "a column named “Type” next to the amount"],
] as const) {
  test(`upload ${file}: the check, the ignored rows and the results`, async ({ page }) => {
    await page.goto("/");
    await page.getByRole("radio", { name: /Upload a CSV/ }).check();
    await page.getByLabel("CSV file (up to 2 MB)").setInputFiles(path.join(SAMPLES, file));
    await page.getByLabel("Date column").waitFor();
    const select = page.getByLabel("How are amounts signed?");
    await expect(page.getByLabel("Status column (optional)")).toHaveValue("Status");
    if (convention) {
      await expect(select.locator("option:checked")).toHaveText(convention);       // chosen for you...
      await expect(page.locator("#conv-help")).toContainText(note!);               // ...and the page says why
    } else {
      await expect(select.locator("option:checked")).toHaveText("Choose how amounts are signed");   // R-1.3: never guessed
      await page.getByRole("button", { name: "Check this file" }).click();
      await expect(page.locator(".form-error")).toContainText("Choose how amounts are signed in this file");
      await expect(select).toBeFocused();
      await select.selectOption("debits_positive");
    }
    await page.getByRole("button", { name: "Check this file" }).click();
    const status = page.getByRole("status").filter({ hasText: "rows can be used" });
    await expect(status).toContainText("93 of 93 rows can be used.");
    await expect(status).toContainText("Money coming in (refunds, deposits): 2.");
    await expect(status).toContainText("so no round-ups: 2.");                       // transfer and card payment
    await expect(status).toContainText("Pending or cancelled rows: 2.");
    await expect(status).toContainText("Purchases of an exact dollar amount: 1.");
    await expect(status).toContainText("Purchases that will add round-ups: 86.");
    await expect(status).toContainText("1 row has a status we don’t recognise.");       // R-1.4a: the reversed row is flagged and left out
    await expect(page.getByRole("checkbox", { name: "Count these rows as purchases too" })).not.toBeChecked();
    await expect(status).toContainText("Dates in this file run from Jan 2, 2024 to Mar 29, 2024.");
    await expect(status).not.toContainText("fall outside the dates");              // 2024 sits inside the default scenario range
    await chooseDates(page, "2024-01-02", "2024-03-29");
    await page.getByRole("button", { name: "Run simulation" }).click();
    await page.waitForURL("**/results");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Your round-ups in a made-up market");
    await expect(page.locator(".chips")).toContainText("86 purchases");
    await expect(page.locator("#headline")).toContainText("$38.70");
    await expect(page.getByTestId("not-counted")).toContainText("7 rows add no round-ups");
    await expect(page.locator("body")).not.toContainText("Maple Grocery");          // descriptions are never kept or shown
  });
}

test("owner's own export (OWNER_SAMPLE_CSV): pending, refund, transfer and whole-dollar rows are handled", async ({ page }) => {
  const file = process.env.OWNER_SAMPLE_CSV;
  test.skip(!file, "set OWNER_SAMPLE_CSV to the path of the owner's sample-transactions.csv to run this");
  await page.goto("/");
  await page.getByRole("radio", { name: /Upload a CSV/ }).check();
  await page.getByLabel("CSV file (up to 2 MB)").setInputFiles(file!);
  await page.getByLabel("Date column").waitFor();
  await expect(page.getByLabel("Status column (optional)")).toHaveValue("Status");
  await page.getByLabel("How are amounts signed?").selectOption("debits_positive");
  await page.getByRole("button", { name: "Check this file" }).click();
  const status = page.getByRole("status").filter({ hasText: "rows can be used" });
  await expect(status).toContainText("139 of 139 rows can be used.");
  await expect(status).toContainText("Money coming in (refunds, deposits): 1.");
  await expect(status).toContainText("so no round-ups: 1.");
  await expect(status).toContainText("Pending or cancelled rows: 1.");
  await expect(status).toContainText("Purchases of an exact dollar amount: 3.");
  await expect(status).toContainText("Purchases that will add round-ups: 136.");
  await chooseDates(page, "2024-01-02", "2024-03-29");
  await page.getByRole("button", { name: "Run simulation" }).click();
  await page.waitForURL("**/results");
  await expect(page.locator(".chips")).toContainText("136 purchases");
  await expect(page.locator("#headline")).toContainText("$70.90");
  await expect(page.getByTestId("not-counted")).toContainText("3 rows add no round-ups");
});
