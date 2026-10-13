import { expect, test } from "@playwright/test";

test("smoke: setup page renders scenarios from the API", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "Set up a simulation" })).toBeVisible();
  await expect(page.getByText("Crash and recovery")).toBeVisible();
});
