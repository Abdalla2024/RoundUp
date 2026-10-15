import type { Page } from "@playwright/test";

export const API = "http://127.0.0.1:8000";

/** Runs the default sample simulation through the real UI and waits for the results page. */
export async function runSample(page: Page, opts: { start?: string; end?: string } = {}) {
  await page.goto("/");
  await page.getByRole("radio", { name: /Crash and recovery/ }).check();
  if (opts.start) await page.getByLabel("Start date").fill(opts.start);
  if (opts.end) await page.getByLabel("End date").fill(opts.end);
  await page.getByRole("button", { name: "Run simulation" }).click();
  await page.waitForURL("**/results");
  await page.getByText("In this made-up scenario").waitFor();
}

/** On a phone the header links sit behind the Menu button: open it if it is showing. */
export async function openMenuIfCompact(page: Page) {
  const menu = page.getByRole("button", { name: "Menu" });
  if (await menu.isVisible() && (await menu.getAttribute("aria-expanded")) === "false") await menu.click();
}

export async function signIn(page: Page, email = "tester@example.test") {
  await openMenuIfCompact(page);
  await page.getByRole("link", { name: "Sign in", exact: true }).click();
  await page.getByLabel("Email").fill(email);
  await page.getByRole("button", { name: "Email me a sign-in link" }).click();
  await page.getByRole("button", { name: "Sign out", includeHidden: true }).waitFor({ state: "attached" });   // behind the Menu button on a phone
}
