import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { ResultsView } from "@/components/ResultsView";
import { COPY } from "@/lib/copy";
import assumptions from "../fixtures/assumptions.json";
import simulate from "../fixtures/simulate.json";
import whole from "../fixtures/simulate_whole_dollar.json";
import { apiMoneyStrings, renderWith, RUN, SESSION, shownMoney } from "../helpers";

const save = vi.fn();
// Plain function (not vi.fn) for rejections: Vitest 5 reports a vi.fn's rejected result even when the caller handles it.
let saveOverride: ((...a: unknown[]) => Promise<unknown>) | null = null;
vi.mock("@/lib/api", async (orig) => ({ ...(await orig<typeof import("@/lib/api")>()),
  api: { assumptions: () => Promise.resolve(assumptions),
         save: (...a: unknown[]) => (saveOverride ? saveOverride(...a) : save(...a)) } }));
beforeEach(() => { save.mockReset(); saveOverride = null; });

describe("Results screen", () => {
  test("empty state when no simulation has run", () => {
    renderWith(<ResultsView />);
    expect(screen.getByRole("heading", { level: 1, name: "No results yet" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Set up a simulation" }).getAttribute("href")).toBe("/");
  });

  test("full result: exact COPY.md wording and engine figures", async () => {
    const { container } = renderWith(<ResultsView />, { run: RUN });
    const text = container.textContent ?? "";
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Your sample round-ups in a made-up market");
    expect(screen.getByText(/In this made-up scenario/).textContent?.replace(/\s+/g, " ")).toBe(
      "In this made-up scenario, $1,789.92 of sample round-ups ends at $2,949.37 on Dec 31, 2024: $1,159.45 more than was put in.");
    expect(text).toContain(`${COPY.disclaimerLead} ${COPY.disclaimer(true)}`);
    for (const t of ["Round-ups added", "Value at end", "Dividends (simulated)", "Growth on round-ups"]) {
      expect(screen.getByRole("button", { name: t })).toBeTruthy();
    }
    expect(text).toContain("+$1,159.45");
    // owner decision 2026-10-13: dollar figure only, no percentage next to "Growth on round-ups"
    expect(text).toContain("+$1,159.45compared with the round-ups added");
    expect(text).not.toMatch(/\d%/);
    expect(text).toContain("Lowest point compared with money put in: on Nov 6, 2017 the value was $344.52, which was $164.98 below the $509.50 of round-ups added by then.");
    expect(text).toContain("On the last day, $0.95 of round-ups was waiting to be invested and $0.00 of dividends was kept as cash.");
    expect(text).toContain(simulate.response.result.series_rule);
    expect(screen.getByTestId("explainer-placeholder").textContent).toContain("Coming later:");
    await waitFor(() => expect(screen.getByText("All assumptions (12)")).toBeTruthy());
    expect(text).toContain("Made-up prices.");
    expect((screen.getByText("All assumptions (12)").closest("details") as HTMLDetailsElement).open).toBe(false);
    expect(text).not.toMatch(/\(R-\d/);                     // rule codes only inside the collapsed references
  });

  test("every dollar figure on screen comes verbatim from the API response", () => {
    const { container } = renderWith(<ResultsView />, { run: RUN });
    fireEvent.click(screen.getByRole("button", { name: "Show the chart as a table" }));
    const allowed = apiMoneyStrings(simulate.response);
    const shown = shownMoney(container.textContent ?? "");
    expect(shown.length).toBeGreaterThan(500);               // includes the whole table
    expect(shown.filter((m) => !allowed.has(m))).toEqual([]);
  });

  test("definitions open from the tile labels (no hover-only text)", () => {
    renderWith(<ResultsView />, { run: RUN });
    const b = screen.getByRole("button", { name: "Growth on round-ups" });
    expect(b.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(b);
    expect(b.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByText(/How far the value at the end is above, or below/)).toBeTruthy();
  });

  test("signed out: 'Sign in to save'; sign-in not set up: no sign-in button", () => {
    const first = renderWith(<ResultsView />, { run: RUN });
    expect(screen.getByRole("button", { name: "Sign in to save" })).toBeTruthy();
    first.unmount();
    renderWith(<ResultsView />, { run: RUN, mode: "off" });
    expect(screen.queryByRole("button", { name: "Sign in to save" })).toBeNull();
  });

  test("signed in: save flow sends the user's token and the original request", async () => {
    save.mockResolvedValue({ id: "x" });
    renderWith(<ResultsView />, { run: RUN, session: SESSION });
    fireEvent.click(screen.getByRole("button", { name: "Save this scenario" }));
    fireEvent.change(screen.getByLabelText("Name for this scenario"), { target: { value: "Crash test" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(screen.getByRole("status").textContent).toContain("Saved as “Crash test”"));
    expect(save).toHaveBeenCalledWith(simulate.request, "Crash test", false, "test-token");
  });

  test("signed in: an expired session shows the plain message and keeps the results", async () => {
    const { ApiError } = await import("@/lib/api");
    saveOverride = async () => { throw new ApiError(401, "AUTH_INVALID", "raw"); };
    renderWith(<ResultsView />, { run: RUN, session: SESSION });
    fireEvent.click(screen.getByRole("button", { name: "Save this scenario" }));
    fireEvent.change(screen.getByLabelText("Name for this scenario"), { target: { value: "x" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain(COPY.errors.sessionExpired);
    expect(screen.getByText(/In this made-up scenario/)).toBeTruthy();
  });

  // ---- stage-5 web review fixes ----
  const variant = (edit: (r: typeof simulate.response.result) => void, sample = false) => {
    const response = JSON.parse(JSON.stringify(simulate.response)) as typeof simulate.response;
    edit(response.result);
    return { request: simulate.request, response, sample } as unknown as typeof RUN;
  };

  test("H2: rows outside the dates are reported, and an empty window is not blamed on whole dollars", () => {
    const some = variant((r) => { r.transactions_ignored = "2"; });
    const { container, unmount } = renderWith(<ResultsView />, { run: some });
    expect(container.textContent).toContain(COPY.notCounted("2"));
    unmount();
    const none = variant((r) => { r.transactions_used = "0"; r.transactions_ignored = "2"; r.summary.contributed = "0.00"; });
    const t = renderWith(<ResultsView />, { run: none }).container.textContent ?? "";
    expect(t).toContain(COPY.noneInWindow);
    expect(t).not.toContain(COPY.wholeDollar);
    expect(t).toContain("from 0 purchases");
  });

  test("H1: a result with no chart points shows a plain message instead of crashing", () => {
    const run = variant((r) => { r.series = []; });
    const { container } = renderWith(<ResultsView />, { run });
    expect(container.textContent).toContain(COPY.noTradingDay);
    expect(screen.queryByRole("button", { name: "Show the chart as a table" })).toBeNull();
  });

  test("M2: Save is disabled while saving, and a scenario opened from Saved cannot be saved again", async () => {
    let release: (v: unknown) => void = () => {};
    save.mockImplementation(() => new Promise((res) => { release = res; }));
    renderWith(<ResultsView />, { run: RUN, session: SESSION });
    fireEvent.click(screen.getByRole("button", { name: "Save this scenario" }));
    fireEvent.change(screen.getByLabelText("Name for this scenario"), { target: { value: "Twice" } });
    const btn = screen.getByRole("button", { name: "Save" }) as HTMLButtonElement;
    fireEvent.click(btn); fireEvent.click(btn);
    expect(save).toHaveBeenCalledTimes(1);
    expect(btn.disabled).toBe(true);
    release({ id: "x" });
    await screen.findByText(/Saved as/);
    renderWith(<ResultsView />, { run: { ...RUN, savedName: "Kept" }, session: SESSION });
    expect(screen.queryAllByRole("button", { name: "Save this scenario" })).toHaveLength(0);
  });

  test("M7: 'Sign in to save' opens the sign-in form on the results page", () => {
    renderWith(<ResultsView />, { run: RUN });
    fireEvent.click(screen.getByRole("button", { name: "Sign in to save" }));
    expect(screen.getByLabelText("Email")).toBeTruthy();
    expect(screen.getByText(/In this made-up scenario/)).toBeTruthy();       // results stay on screen
  });

  test("L5: technical details include the settings needed to reproduce the numbers", () => {
    const { container } = renderWith(<ResultsView />, { run: RUN });
    const tech = container.querySelector("details.tech")?.textContent?.replace(/\s+/g, " ") ?? "";
    expect(tech).toContain("scenario seed");
    expect(tech).toContain("purchase list number 42, up to 2 purchases a day");
    expect(tech).toContain("Jan 2, 2015 to Dec 31, 2024");
    expect(tech).toContain(COPY.strategy[simulate.request.strategy]);
    expect(tech).not.toContain("anyone reproduce");
  });

  test("whole-dollar purchases: plain message, gain % n/a, no dip", () => {
    const run = { request: whole.request, response: whole.response, sample: false } as unknown as typeof RUN;
    const { container } = renderWith(<ResultsView />, { run });
    const text = container.textContent ?? "";
    expect(text).toContain(COPY.wholeDollar);
    expect(text).toContain("no round-ups were added");
    expect(text).toContain("the value never fell below the round-ups added in this scenario.");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Your round-ups in a made-up market");
    expect(text).toContain(COPY.disclaimer(false));
    expect(text).toContain("from 1 purchase");                // L8: singular
    expect(text).not.toContain("1 purchases");
  });
});
