import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { SetupForm } from "@/components/SetupForm";
import { ApiError } from "@/lib/api";
import parseFx from "../fixtures/parse.json";
import scenarios from "../fixtures/scenarios.json";
import simulate from "../fixtures/simulate.json";
import { renderWith } from "../helpers";

const sim = vi.fn(), parse = vi.fn(), scen = vi.fn();
vi.mock("@/lib/api", async (orig) => ({ ...(await orig<typeof import("@/lib/api")>()),
  api: { scenarios: () => scen(), simulate: (...a: unknown[]) => sim(...a), parse: (...a: unknown[]) => parse(...a) } }));
const pushed: string[] = [];
(globalThis as { __push?: (p: string) => void }).__push = (p) => pushed.push(p);
beforeEach(() => { sim.mockReset(); parse.mockReset(); scen.mockReset(); scen.mockResolvedValue(scenarios); pushed.length = 0; });

describe("Setup screen", () => {
  test("lists the four synthetic scenarios with the label", async () => {
    const { container } = renderWith(<SetupForm />);
    await waitFor(() => screen.getByRole("radio", { name: /Crash and recovery/ }));
    expect(screen.getAllByRole("radio", { name: /Steady growth|Crash and recovery|Sideways|High volatility/ })).toHaveLength(4);
    expect(container.textContent).toContain("Starting setting");
    expect(container.textContent).toContain("All four are equally valid to explore.");
  });
  test("generate: sends the request and goes to results", async () => {
    sim.mockResolvedValue(simulate.response);
    renderWith(<SetupForm />);
    await waitFor(() => screen.getByRole("radio", { name: /Crash and recovery/ }));
    fireEvent.click(screen.getByRole("button", { name: "Run simulation" }));
    await waitFor(() => expect(pushed).toEqual(["/results"]));
    expect(sim).toHaveBeenCalledWith({ scenario_id: "crash-and-recovery", style: "broad", start: "2015-01-02",
      end: "2024-12-31", strategy: "threshold", reinvest: true, generate: { seed: 42, max_per_day: 2 } });
  });
  test("API validation errors are shown in plain language, focused, and fields marked", async () => {
    sim.mockImplementation(() => Promise.reject(new ApiError(422, "WINDOW_OUTSIDE_DATA", "The dates must be inside the scenario's range.", ["start"])));
    renderWith(<SetupForm />);
    await waitFor(() => screen.getByRole("radio", { name: /Crash and recovery/ }));
    fireEvent.click(screen.getByRole("button", { name: "Run simulation" }));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("inside the scenario's range"));
    expect(screen.getByLabelText("Start date").getAttribute("aria-invalid")).toBe("true");
    expect(document.activeElement?.id).toBe("form-error");
  });
  test("rate limit message", async () => {
    sim.mockImplementation(() => Promise.reject(new ApiError(429, "RATE_LIMITED", "Too many requests. Please wait 12 seconds and try again.")));
    renderWith(<SetupForm />);
    await waitFor(() => screen.getByRole("radio", { name: /Crash and recovery/ }));
    fireEvent.click(screen.getByRole("button", { name: "Run simulation" }));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("wait 12 seconds"));
  });
  test("bad sample number is caught before calling the API", async () => {
    renderWith(<SetupForm />);
    await waitFor(() => screen.getByRole("radio", { name: /Crash and recovery/ }));
    fireEvent.change(screen.getByLabelText(/Sample number/), { target: { value: "4.2" } });
    fireEvent.click(screen.getByRole("button", { name: "Run simulation" }));
    expect(screen.getByRole("alert").textContent).toContain("whole number");
    expect(sim).not.toHaveBeenCalled();
  });
  test("CSV: columns come from the header, rows are checked by the API, then simulated", async () => {
    parse.mockResolvedValue(parseFx.response);
    sim.mockResolvedValue(simulate.response);
    renderWith(<SetupForm />);
    await waitFor(() => screen.getByRole("radio", { name: /Crash and recovery/ }));
    fireEvent.click(screen.getByRole("radio", { name: /Upload a CSV/ }));
    const file = new File([parseFx.csv], "bank.csv", { type: "text/csv" });
    fireEvent.change(screen.getByLabelText("CSV file (up to 2 MB)"), { target: { files: [file] } });
    await waitFor(() => screen.getByLabelText("Date column"));
    expect((screen.getByLabelText("Date column") as HTMLSelectElement).value).toBe("Date");
    fireEvent.change(screen.getByLabelText("How are amounts signed?"), { target: { value: "debits_positive" } });
    fireEvent.click(screen.getByRole("button", { name: "Check this file" }));
    await waitFor(() => expect(screen.getByRole("status").textContent).toContain("3 of 4 rows can be used."));
    expect(screen.getByRole("status").textContent).toContain("Not purchases (payments, transfers or fees), so no round-ups: 1.");
    expect(parse).toHaveBeenCalledWith(parseFx.csv, { date: "Date", amount: "Amount", description: "Description" }, "debits_positive");
    fireEvent.click(screen.getByRole("button", { name: "Run simulation" }));
    await waitFor(() => expect(sim).toHaveBeenCalled());
    const txs = sim.mock.calls[0][0].transactions;
    expect(txs.length).toBe(3);                              // rows without problems, as parsed by the API
    expect(JSON.stringify(txs)).not.toMatch(/COFFEE|REFUND|PAYMENT/);   // descriptions never sent on (D-8)
  });
  test("CSV: unknown sign convention asks the question", async () => {
    parse.mockImplementation(() => Promise.reject(new ApiError(422, "SIGN_CONVENTION_REQUIRED", "We can't tell which amounts are purchases.")));
    renderWith(<SetupForm />);
    await waitFor(() => screen.getByRole("radio", { name: /Crash and recovery/ }));
    fireEvent.click(screen.getByRole("radio", { name: /Upload a CSV/ }));
    fireEvent.change(screen.getByLabelText("CSV file (up to 2 MB)"), { target: { files: [new File([parseFx.csv], "b.csv")] } });
    await waitFor(() => screen.getByLabelText("Date column"));
    fireEvent.click(screen.getByRole("button", { name: "Check this file" }));
    await waitFor(() => expect(screen.getByText("In this file, are purchases positive or negative numbers?")).toBeTruthy());
  });
  test("CSV: oversize file is refused with a plain message", async () => {
    renderWith(<SetupForm />);
    await waitFor(() => screen.getByRole("radio", { name: /Crash and recovery/ }));
    fireEvent.click(screen.getByRole("radio", { name: /Upload a CSV/ }));
    fireEvent.change(screen.getByLabelText("CSV file (up to 2 MB)"), { target: { files: [new File(["a".repeat(2_000_001)], "big.csv")] } });
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("This file is too large"));
    expect(parse).not.toHaveBeenCalled();
  });
});
