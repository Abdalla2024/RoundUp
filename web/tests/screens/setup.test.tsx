import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { SetupForm } from "@/components/SetupForm";
import { ApiError } from "@/lib/api";
import { COPY } from "@/lib/copy";
import { useState } from "react";
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
  test("CSV: oversize file is refused with a plain message", async () => {
    renderWith(<SetupForm />);
    await waitFor(() => screen.getByRole("radio", { name: /Crash and recovery/ }));
    fireEvent.click(screen.getByRole("radio", { name: /Upload a CSV/ }));
    fireEvent.change(screen.getByLabelText("CSV file (up to 2 MB)"), { target: { files: [new File(["a".repeat(2_000_001)], "big.csv")] } });
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("This file is too large"));
    expect(parse).not.toHaveBeenCalled();
  });

  // ---- stage-5 web review fixes ----
  const ready = async () => { await waitFor(() => screen.getByRole("radio", { name: /Crash and recovery/ })); };
  async function upload(csv: string) {
    fireEvent.click(screen.getByRole("radio", { name: /Upload a CSV/ }));
    fireEvent.change(screen.getByLabelText("CSV file (up to 2 MB)"), { target: { files: [new File([csv], "b.csv")] } });
  }

  test("M1: the form keeps its settings after leaving and coming back", async () => {
    function Toggle() {          // unmounting and remounting the form is what navigating away and back does
      const [shown, setShown] = useState(true);
      return <><button type="button" onClick={() => setShown(!shown)}>toggle</button>{shown && <SetupForm />}</>;
    }
    renderWith(<Toggle />);
    await ready();
    fireEvent.change(screen.getByLabelText(COPY.perWeekLabel, { selector: "#perweek" }), { target: { value: "14" } });
    fireEvent.click(screen.getByRole("radio", { name: /Sideways/ }));
    fireEvent.click(screen.getByRole("radio", { name: /Once a week/ }));
    fireEvent.click(screen.getByRole("button", { name: "toggle" }));
    expect(screen.queryByLabelText(COPY.perWeekLabel, { selector: "#perweek" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "toggle" }));
    await ready();
    expect((screen.getByLabelText(COPY.perWeekLabel, { selector: "#perweek" }) as HTMLInputElement).value).toBe("14");
    expect((screen.getByRole("radio", { name: /Sideways/ }) as HTMLInputElement).checked).toBe(true);
    expect((screen.getByRole("radio", { name: /Once a week/ }) as HTMLInputElement).checked).toBe(true);
  });

  test("M4: each sign option shows the columns it needs, and only those are sent", async () => {
    parse.mockResolvedValue(parseFx.response);
    renderWith(<SetupForm />);
    await ready();
    await upload("Date,Money out,Money in,Kind,Memo\n2015-01-05,4.37,,debit,COFFEE\n");
    await waitFor(() => screen.getByLabelText("Date column"));
    fireEvent.change(screen.getByLabelText("How are amounts signed?"), { target: { value: "separate_columns" } });
    expect(screen.queryByLabelText("Amount column")).toBeNull();
    fireEvent.change(screen.getByLabelText("Money out column"), { target: { value: "Money out" } });
    fireEvent.change(screen.getByLabelText("Money in column"), { target: { value: "Money in" } });
    fireEvent.click(screen.getByRole("button", { name: "Check this file" }));
    await waitFor(() => expect(parse).toHaveBeenCalled());
    expect(parse.mock.calls[0][1]).toEqual({ date: "Date", description: "Memo", debit: "Money out", credit: "Money in" });
    fireEvent.change(screen.getByLabelText("How are amounts signed?"), { target: { value: "type_column" } });
    expect(screen.getByLabelText("Debit or credit column")).toBeTruthy();
    expect(screen.getByLabelText("Amount column")).toBeTruthy();
  });

  test("H2 + M5: the check shows the file's dates, warns about rows outside the window, and explains slash dates", async () => {
    const res = JSON.parse(JSON.stringify(parseFx.response));
    res.transactions[0].posted_date = "2009-01-06"; res.transactions[2].posted_date = "2030-01-07";
    parse.mockResolvedValue(res);
    renderWith(<SetupForm />);
    await ready();
    await upload("Date,Amount\n01/06/2009,4.37\n");
    await waitFor(() => screen.getByLabelText("Date column"));
    fireEvent.change(screen.getByLabelText("How are amounts signed?"), { target: { value: "debits_positive" } });
    fireEvent.click(screen.getByRole("button", { name: "Check this file" }));
    const status = await screen.findByRole("status");
    expect(status.textContent).toContain(COPY.fileDates("Jan 6, 2009", "Jan 7, 2030"));
    expect(status.textContent).toContain(COPY.outsideDates);
    expect(status.textContent).toContain(COPY.slashDates);
    fireEvent.click(screen.getByRole("button", { name: COPY.useFileDates }));
    // kept inside the scenario's range (scenarios fixture: 2012-01-03 to 2025-12-31 or similar)
    const start = (screen.getByLabelText("Start date") as HTMLInputElement).value;
    const end = (screen.getByLabelText("End date") as HTMLInputElement).value;
    const range = scenarios.scenarios.find((x) => x.id === "crash-and-recovery")!.styles[0];
    expect(start).toBe(range.start);
    expect(end).toBe(range.end);
  });

  test("L9: empty file, semicolon file and a column chosen twice get plain messages", async () => {
    renderWith(<SetupForm />);
    await ready();
    await upload("");
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain(COPY.emptyFile));
    fireEvent.change(screen.getByLabelText("CSV file (up to 2 MB)"), { target: { files: [new File(["Date;Amount\n2015-01-05;4.37\n"], "s.csv")] } });
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain(COPY.semicolons));
    fireEvent.change(screen.getByLabelText("CSV file (up to 2 MB)"), { target: { files: [new File([parseFx.csv], "b.csv")] } });
    await waitFor(() => screen.getByLabelText("Date column"));
    fireEvent.change(screen.getByLabelText("Amount column"), { target: { value: "Date" } });
    fireEvent.click(screen.getByRole("button", { name: "Check this file" }));
    expect(screen.getByRole("alert").textContent).toContain(COPY.sameColumn);
    expect(screen.getByLabelText("Amount column").getAttribute("aria-invalid")).toBe("true");
    expect(parse).not.toHaveBeenCalled();
  });

  test("L2: after a rate limit the Run button stays disabled until the wait ends", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      sim.mockImplementation(() => Promise.reject(new ApiError(429, "RATE_LIMITED", "Too many requests. Please wait 2 seconds and try again.", [], "2")));
      renderWith(<SetupForm />);
      await ready();
      // Record every DOM change: the button must never be enabled while the "please wait" message shows
      // (CI 2026-10-13 caught a one-render gap when the wait was started in an effect).
      const seen: boolean[] = [];
      const obs = new MutationObserver(() => {
        if (document.querySelector('[role="alert"]')) {
          seen.push((screen.getByRole("button", { name: /Run simulation|Running/ }) as HTMLButtonElement).disabled);
        }
      });
      obs.observe(document.body, { subtree: true, childList: true, attributes: true });
      fireEvent.click(screen.getByRole("button", { name: "Run simulation" }));
      await screen.findByRole("alert");
      await new Promise((r) => setTimeout(r, 50));
      obs.disconnect();
      expect(seen.length).toBeGreaterThan(0);
      expect(seen.every(Boolean)).toBe(true);
      expect((screen.getByRole("button", { name: "Run simulation" }) as HTMLButtonElement).disabled).toBe(true);
      await vi.advanceTimersByTimeAsync(2100);
      await waitFor(() => expect((screen.getByRole("button", { name: "Run simulation" }) as HTMLButtonElement).disabled).toBe(false));
    } finally { vi.useRealTimers(); }
  });

  // ---- stage 6: the sign-convention control (owner's testing on the deployed preview) ----
  const signing = () => screen.getByLabelText("How are amounts signed?") as HTMLSelectElement;

  test("the sign control starts on a neutral prompt, with plain-language help beside it", async () => {
    renderWith(<SetupForm />);
    await ready();
    await upload(parseFx.csv);                                // one signed Amount column
    await waitFor(() => screen.getByLabelText("Date column"));
    expect(signing().value).toBe("");
    expect(signing().options[0].textContent).toBe("Choose how amounts are signed");
    expect(screen.queryByText("Work it out from the columns")).toBeNull();
    const help = document.getElementById("conv-help")!;
    expect(help.textContent).toBe(COPY.signingHelp);
    expect(signing().getAttribute("aria-describedby")).toContain("conv-help");
    fireEvent.change(signing(), { target: { value: "debits_negative" } });
    expect(document.getElementById("conv-help")!.textContent).toContain(COPY.signingOptionHelp.debits_negative);
  });

  test("checking without a choice sends nothing; the page points at the field and names the four options", async () => {
    renderWith(<SetupForm />);
    await ready();
    await upload(parseFx.csv);
    await waitFor(() => screen.getByLabelText("Date column"));
    fireEvent.click(screen.getByRole("button", { name: "Check this file" }));
    expect(parse).not.toHaveBeenCalled();                       // R-1.3: never guess silently
    const banner = screen.getByRole("alert");
    expect(banner.textContent).toBe(COPY.chooseSigning);
    for (const t of ["Purchases are positive numbers", "Purchases are negative numbers",
                     "Money out and money in columns", "A column says debit or credit"]) {
      expect(banner.textContent).toContain(`“${t}”`);
    }
    expect(banner.textContent).toContain("How are amounts signed?");
    expect(signing().getAttribute("aria-invalid")).toBe("true");
    await waitFor(() => expect(document.activeElement).toBe(signing()));
    expect(document.getElementById("conv-help")!.textContent).toContain(COPY.chooseSigningField);
  });

  test("two money columns: the matching option is chosen for you, and the page says why", async () => {
    parse.mockResolvedValue(parseFx.response);
    renderWith(<SetupForm />);
    await ready();
    await upload("Date,Description,Money out,Money in,Status\n2024-01-02,Coffee,6.16,,posted\n");
    await waitFor(() => screen.getByLabelText("Date column"));
    expect(signing().value).toBe("separate_columns");
    expect(document.getElementById("conv-help")!.textContent).toContain(COPY.signingChosenBecause("Money out", "Money in"));
    expect((screen.getByLabelText("Money out column") as HTMLSelectElement).value).toBe("Money out");
    expect((screen.getByLabelText("Money in column") as HTMLSelectElement).value).toBe("Money in");
    fireEvent.click(screen.getByRole("button", { name: "Check this file" }));
    await waitFor(() => expect(parse).toHaveBeenCalled());
    expect(parse.mock.calls[0][1]).toEqual({ date: "Date", description: "Description", debit: "Money out", credit: "Money in", status: "Status" });
    expect(parse.mock.calls[0][2]).toBe("separate_columns");
  });

  test("a debit/credit type column next to the amount: that option is chosen, with the reason", async () => {
    renderWith(<SetupForm />);
    await ready();
    await upload("Date,Description,Amount,Type\n2024-01-02,Coffee,6.16,debit\n");
    await waitFor(() => screen.getByLabelText("Date column"));
    expect(signing().value).toBe("type_column");
    expect(document.getElementById("conv-help")!.textContent).toContain(COPY.signingChosenBecauseType("Type"));
    expect((screen.getByLabelText("Debit or credit column") as HTMLSelectElement).value).toBe("Type");
  });

  test("a Status column is found and sent, so pending and cancelled rows are not counted", async () => {
    parse.mockResolvedValue(parseFx.response);
    renderWith(<SetupForm />);
    await ready();
    await upload("Date,Description,Amount,Status\n2024-01-02,Coffee,6.16,pending\n");
    await waitFor(() => screen.getByLabelText("Status column (optional)"));
    expect((screen.getByLabelText("Status column (optional)") as HTMLSelectElement).value).toBe("Status");
    fireEvent.change(signing(), { target: { value: "debits_positive" } });
    fireEvent.click(screen.getByRole("button", { name: "Check this file" }));
    await waitFor(() => expect(parse).toHaveBeenCalled());
    expect(parse.mock.calls[0][1]).toEqual({ date: "Date", amount: "Amount", description: "Description", status: "Status" });
  });

  test("the check says how many rows are money in, pending or cancelled, and whole-dollar", async () => {
    const res = JSON.parse(JSON.stringify(parseFx.response));
    res.summary = { ...res.summary, credits: 2, not_posted: 1, whole_dollar: 3 };
    parse.mockResolvedValue(res);
    renderWith(<SetupForm />);
    await ready();
    await upload(parseFx.csv);
    await waitFor(() => screen.getByLabelText("Date column"));
    fireEvent.change(signing(), { target: { value: "debits_positive" } });
    fireEvent.click(screen.getByRole("button", { name: "Check this file" }));
    const status = await screen.findByRole("status");
    expect(status.textContent).toContain(COPY.checkCredits("2"));
    expect(status.textContent).toContain(COPY.checkNotPosted("1"));
    expect(status.textContent).toContain(COPY.checkWholeDollar("3"));
  });

  // ---- stage 6: findings from the independent review of the upload flow ----
  test("a tab-separated file gets a message about tabs, not about columns", async () => {
    renderWith(<SetupForm />);
    await ready();
    await upload("Date\tAmount\tDescription\n2024-01-02\t6.16\tCoffee\n");
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain(COPY.tabs));
  });

  test("blank lines before the header are skipped, so the column pickers still appear", async () => {
    renderWith(<SetupForm />);
    await ready();
    await upload("\n\nDate,Amount,Description\n2024-01-02,6.16,Coffee\n");
    await waitFor(() => screen.getByLabelText("Date column"));
    expect((screen.getByLabelText("Amount column") as HTMLSelectElement).value).toBe("Amount");
  });

  async function checked(summary: Record<string, unknown>) {
    const res = JSON.parse(JSON.stringify(parseFx.response));
    res.summary = { ...res.summary, ...summary };
    parse.mockResolvedValue(res);
    renderWith(<SetupForm />);
    await ready();
    await upload(parseFx.csv);
    await waitFor(() => screen.getByLabelText("Date column"));
    fireEvent.change(signing(), { target: { value: "debits_positive" } });
    fireEvent.click(screen.getByRole("button", { name: "Check this file" }));
    return (await screen.findByRole("status")).textContent ?? "";
  }

  test("the check says how many purchases will add round-ups, and warns when there are none", async () => {
    const t = await checked({ purchases: 2 });
    expect(t).toContain(COPY.checkPurchases("2"));
    expect(t).not.toContain(COPY.checkNoPurchases);
  });
  test("zero purchases: a plain warning that points at the sign box", async () => {
    const t = await checked({ rows: 2, usable: 2, credits: 2, purchases: 0 });
    expect(t).toContain(COPY.checkNoPurchases);
    expect(t).toContain("How are amounts signed?");
  });
  test("rows with more values than the header: a warning that explains the comma", async () => {
    expect(await checked({ ragged_rows: 2 })).toContain(COPY.checkRagged("2"));
  });
  test("a header-only file says so", async () => {
    expect(await checked({ rows: 0, usable: 0, purchases: 0, credits: 0, non_purchases: 0 })).toContain(COPY.checkNoRows);
  });
  test("unreadable dates come with the formats that work", async () => {
    expect(await checked({ problems: { invalid_amount: 0, invalid_date: 3, zero_amount: 0 } })).toContain(COPY.dateFormats);
  });

  test("choosing an option clears the sign-box error", async () => {
    renderWith(<SetupForm />);
    await ready();
    await upload(parseFx.csv);
    await waitFor(() => screen.getByLabelText("Date column"));
    fireEvent.click(screen.getByRole("button", { name: "Check this file" }));
    expect(screen.getByRole("alert")).toBeTruthy();
    fireEvent.change(signing(), { target: { value: "debits_positive" } });
    expect(screen.queryByRole("alert")).toBeNull();
    expect(signing().getAttribute("aria-invalid")).toBe("false");
  });

  // ---- R-1.4a (owner decision OQ-12): only clearly posted statuses count; the rest is flagged until the user decides ----
  async function checkedWithUnrecognised(n: number) {
    const res = JSON.parse(JSON.stringify(parseFx.response));
    res.transactions[1].status = "unrecognised"; res.transactions[2].status = "unrecognised";
    res.summary = { ...res.summary, unrecognised_status: n };
    parse.mockResolvedValue(res); sim.mockResolvedValue(simulate.response);
    renderWith(<SetupForm />);
    await ready();
    await upload(parseFx.csv);
    await waitFor(() => screen.getByLabelText("Date column"));
    fireEvent.change(signing(), { target: { value: "debits_positive" } });
    fireEvent.click(screen.getByRole("button", { name: "Check this file" }));
    return (await screen.findByRole("status")).textContent ?? "";
  }

  test("unrecognised statuses are flagged in the check step and left out until the user decides", async () => {
    const t = await checkedWithUnrecognised(2);
    expect(t).toContain(COPY.checkUnrecognised("2"));
    const box = screen.getByRole("checkbox", { name: COPY.countUnrecognised }) as HTMLInputElement;
    expect(box.checked).toBe(false);                                   // default: not counted
    fireEvent.click(screen.getByRole("button", { name: "Run simulation" }));
    await waitFor(() => expect(sim).toHaveBeenCalled());
    const sent = sim.mock.calls[0][0].transactions as { status: string }[];
    expect(sent.filter((x) => x.status === "unrecognised")).toHaveLength(2);   // sent as they are, and the API ignores them
    expect(sent.filter((x) => x.status === "posted").length).toBeGreaterThan(0);
  });

  test("ticking the box sends those rows as posted", async () => {
    await checkedWithUnrecognised(2);
    fireEvent.click(screen.getByRole("checkbox", { name: COPY.countUnrecognised }));
    expect(screen.getByText(COPY.willCountUnrecognised("2"))).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Run simulation" }));
    await waitFor(() => expect(sim).toHaveBeenCalled());
    const sent = sim.mock.calls[0][0].transactions as { status: string }[];
    expect(sent.filter((x) => x.status === "unrecognised")).toHaveLength(0);
  });

  test("no unrecognised statuses: no notice and no checkbox", async () => {
    const t = await checked({ unrecognised_status: 0 });
    expect(t).not.toContain("a status we don");
    expect(screen.queryByRole("checkbox", { name: COPY.countUnrecognised })).toBeNull();
  });

  // ---- typical spending (R-1.9, owner decision 2026-10-15): a weekly count and an average round-up, no random numbers ----
  const perWeek = () => screen.getByLabelText(COPY.perWeekLabel, { selector: "#perweek" }) as HTMLInputElement;
  const slider = () => screen.getByRole("slider", { name: COPY.perWeekLabel }) as HTMLInputElement;
  const average = () => screen.getByLabelText(COPY.averageLabel) as HTMLInputElement;

  test("typical spending is the starting choice, with a slider and a number box, and says it is an estimate", async () => {
    const { container } = renderWith(<SetupForm />);
    await ready();
    expect((screen.getByRole("radio", { name: new RegExp(COPY.typicalTitle) }) as HTMLInputElement).checked).toBe(true);
    expect(perWeek().value).toBe("10");
    expect(slider().value).toBe("10");
    expect([slider().min, slider().max]).toEqual(["1", "60"]);
    expect(container.textContent).toContain(COPY.typicalEstimate);
    expect(document.getElementById("perweek-help")!.textContent).toBe(COPY.perWeekHint);
    expect(average().value).toBe("0.50");
    const details = screen.getByText(COPY.adjustAverage).closest("details") as HTMLDetailsElement;
    expect(details.open).toBe(false);                               // tucked away
    expect(details.textContent).toContain(COPY.adjustAverageBody);
    for (const gone of ["Made-up purchase list number", "Most purchases in one day", "Sample number", "seed"]) expect(container.textContent).not.toContain(gone);
  });

  test("the slider and the number box stay in step", async () => {
    renderWith(<SetupForm />);
    await ready();
    fireEvent.change(slider(), { target: { value: "25" } });
    expect(perWeek().value).toBe("25");
    fireEvent.change(perWeek(), { target: { value: "7" } });
    expect(slider().value).toBe("7");
    fireEvent.change(perWeek(), { target: { value: "" } });                  // an empty or invalid box is shown as typed; the slider keeps its last good value
    expect(perWeek().value).toBe("");
    expect(slider().value).toBe("7");
  });

  test("typical: the request carries the weekly count and the average as text, and goes to results", async () => {
    sim.mockResolvedValue(simulate.response);
    renderWith(<SetupForm />);
    await ready();
    fireEvent.change(perWeek(), { target: { value: "20" } });
    fireEvent.change(average(), { target: { value: "0.25" } });
    fireEvent.click(screen.getByRole("button", { name: "Run simulation" }));
    await waitFor(() => expect(pushed).toEqual(["/results"]));
    expect(sim).toHaveBeenCalledWith({ scenario_id: "crash-and-recovery", style: "broad", start: "2015-01-02", end: "2024-12-31",
      strategy: "threshold", reinvest: true, typical: { per_week: 20, average_roundup: "0.25" } });
  });

  test("weekly counts outside 1 to 60, or not whole numbers, are caught before the API; only that field is marked", async () => {
    renderWith(<SetupForm />);
    await ready();
    for (const bad of ["0", "61", "5.5", "abc", "", "-3", "1e1"]) {
      fireEvent.change(perWeek(), { target: { value: bad } });
      fireEvent.click(screen.getByRole("button", { name: "Run simulation" }));
      expect(screen.getByRole("alert").textContent).toContain(COPY.perWeekError);
      expect(perWeek().getAttribute("aria-invalid")).toBe("true");
      expect(average().getAttribute("aria-invalid")).toBe("false");
      expect(sim).not.toHaveBeenCalled();
    }
    sim.mockResolvedValue(simulate.response);
    fireEvent.change(perWeek(), { target: { value: "60" } });                         // the largest allowed value goes through
    fireEvent.click(screen.getByRole("button", { name: "Run simulation" }));
    await waitFor(() => expect(sim).toHaveBeenCalled());
    expect(sim.mock.calls[0][0].typical.per_week).toBe(60);
  });

  test("averages must be $0.01 to $0.99 written with two decimals; the error opens the adjust box and marks the field", async () => {
    renderWith(<SetupForm />);
    await ready();
    for (const bad of ["0.00", "1.00", "0.5", "0.505", ".50", "abc", "", "-0.50", "0,50"]) {
      fireEvent.change(average(), { target: { value: bad } });
      fireEvent.click(screen.getByRole("button", { name: "Run simulation" }));
      expect(screen.getByRole("alert").textContent).toContain(COPY.averageError);
      expect(average().getAttribute("aria-invalid")).toBe("true");
      expect((screen.getByText(COPY.adjustAverage).closest("details") as HTMLDetailsElement).open).toBe(true);
      expect(perWeek().getAttribute("aria-invalid")).toBe("false");
    }
  });

  test("the browser never computes a money figure for the typical inputs: the average is sent exactly as typed", async () => {
    sim.mockResolvedValue(simulate.response);
    renderWith(<SetupForm />);
    await ready();
    fireEvent.change(average(), { target: { value: "0.99" } });
    fireEvent.click(screen.getByRole("button", { name: "Run simulation" }));
    await waitFor(() => expect(sim).toHaveBeenCalled());
    expect(sim.mock.calls[0][0].typical.average_roundup).toBe("0.99");
  });
});

describe("weekly slider end labels", () => {
  test("the numbers 1 and 60 are shown at the ends of the slider and hidden from screen readers (the slider announces its own limits)", async () => {
    const { container } = renderWith(<SetupForm />);
    await waitFor(() => expect(container.querySelector(".slider-ends")).toBeTruthy());
    const ends = container.querySelector(".slider-ends")!;
    expect(ends.getAttribute("aria-hidden")).toBe("true");
    expect([...ends.querySelectorAll("span")].map((x) => x.textContent)).toEqual(["1", "60"]);
    const range = container.querySelector('input[type="range"]')!;
    expect([range.getAttribute("min"), range.getAttribute("max")]).toEqual(["1", "60"]);
  });
});
