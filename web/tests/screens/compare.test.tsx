import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { CompareView } from "@/components/CompareView";
import { COPY } from "@/lib/copy";
import assumptions from "../fixtures/assumptions.json";
import compareFx from "../fixtures/compare.json";
import { apiMoneyStrings, COMPARE, renderWith, RUN, shownMoney } from "../helpers";

const compare = vi.fn();
vi.mock("@/lib/api", async (orig) => ({ ...(await orig<typeof import("@/lib/api")>()),
  api: { assumptions: () => Promise.resolve(assumptions), compare: (...a: unknown[]) => compare(...a) } }));

describe("Compare screen", () => {
  test("empty state without a simulation", () => {
    renderWith(<CompareView />);
    expect(screen.getByText(/Run a simulation first/)).toBeTruthy();
  });

  test("runs the comparison with the same purchases and scenario", async () => {
    compare.mockResolvedValue(compareFx.response);
    renderWith(<CompareView />, { run: RUN });
    fireEvent.click(within(screen.getByRole("group", { name: /^B/ })).getByRole("radio", { name: COPY.strategy.weekly }));
    fireEvent.click(screen.getByRole("button", { name: "Compare" }));
    await waitFor(() => expect(compare).toHaveBeenCalled());
    const req = compare.mock.calls[0][0];
    expect(req.b).toEqual({ strategy: "weekly", reinvest: false });
    expect(req.generate).toEqual(RUN.request.generate);
    expect(req).not.toHaveProperty("strategy");
  });

  test("table rows, plain-language labels, note and per-side dips", () => {
    const { container } = renderWith(<CompareView />, { run: RUN, compare: COMPARE });
    const text = container.textContent ?? "";
    for (const r of ["Round-ups added", "Value at end", "Growth on round-ups", "Dividends (simulated)",
      "Round-ups waiting to be invested", "Dividends kept as cash", "Times invested from round-ups", "Times invested from dividends"]) {
      expect(screen.getByRole("rowheader", { name: r })).toBeTruthy();
    }
    expect(screen.getByRole("columnheader", { name: "B minus A" })).toBeTruthy();
    expect(text).toContain("−$91.91");
    expect(text).toContain(COPY.compareNote);
    expect(text).toContain("A, lowest point compared with money put in:");
    expect(text).toContain("B, lowest point compared with money put in:");
    // advice-like phrasing must not appear (the key point "Nothing here suggests what you should do" is the opposite)
    expect(text).not.toMatch(/\b(best (choice|option|strategy)|you should (invest|choose|pick)|we recommend|recommended)\b/i);
  });

  test("every dollar figure comes verbatim from the API response", () => {
    const { container } = renderWith(<CompareView />, { run: RUN, compare: COMPARE });
    const allowed = apiMoneyStrings(compareFx.response);
    expect(shownMoney(container.textContent ?? "").filter((m) => !allowed.has(m))).toEqual([]);
  });

  test("L1: rapid clicks on Compare send one request", async () => {
    let release: (v: unknown) => void = () => {};
    compare.mockReset();
    compare.mockImplementation(() => new Promise((res) => { release = res; }));
    renderWith(<CompareView />, { run: RUN });
    const btn = screen.getByRole("button", { name: "Compare" });
    for (let i = 0; i < 8; i++) fireEvent.click(btn);
    expect(compare).toHaveBeenCalledTimes(1);
    release(compareFx.response);
    await waitFor(() => expect(screen.getByRole("rowheader", { name: "Growth on round-ups" })).toBeTruthy());
    expect(screen.getAllByText(COPY.sameForBoth)).toHaveLength(1);
    expect(screen.getAllByText(COPY.seeAB)).toHaveLength(2);
  });

  test("the two pickers are radio lists, not dropdowns: every label can wrap, so none can be clipped on any platform's fonts", () => {
    const { container } = renderWith(<CompareView />, { run: RUN });
    expect(container.querySelectorAll("select")).toHaveLength(0);
    for (const side of ["A", "B"]) {
      const group = screen.getByRole("group", { name: new RegExp(`^${side}`) });
      const radios = within(group).getAllByRole("radio");
      expect(radios.map((r) => r.closest("label")?.textContent)).toEqual(
        ["threshold", "next_session", "weekly", "monthly"].map((k) => COPY.strategy[k]));
      expect(within(group).getByRole("checkbox", { name: "Reinvest dividends" })).toBeTruthy();
    }
    const checked = (side: string) => within(screen.getByRole("group", { name: new RegExp(`^${side}`) }))
      .getAllByRole("radio").filter((r) => (r as HTMLInputElement).checked).map((r) => r.closest("label")?.textContent);
    expect(checked("A")).toEqual([COPY.strategy.threshold]);          // the same starting settings as before
    expect(checked("B")).toEqual([COPY.strategy.monthly]);
    expect((within(screen.getByRole("group", { name: /^A/ })).getByRole("checkbox") as HTMLInputElement).checked).toBe(true);
    expect((within(screen.getByRole("group", { name: /^B/ })).getByRole("checkbox") as HTMLInputElement).checked).toBe(false);
  });
});
