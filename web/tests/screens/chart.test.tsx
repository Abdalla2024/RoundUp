import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { chartSummary, ValueChart } from "@/components/ValueChart";
import type { Result } from "@/lib/types";
import simulate from "../fixtures/simulate.json";

const result = simulate.response.result as unknown as Result;
const pts = result.series;

describe("Chart keyboard reading (reviewer M6) and summaries (L7)", () => {
  test("nothing is shown until asked; arrows, Home, End and Page keys move; the readout is a polite live region", () => {
    render(<ValueChart result={result} title="Value over time" />);
    const chart = screen.getByTestId("chart");
    const out = screen.getByTestId("chart-readout");
    expect(out.getAttribute("aria-live")).toBe("polite");
    expect(out.textContent).toBe("");
    expect(chart.getAttribute("tabindex")).toBe("0");
    const key = (k: string) => fireEvent.keyDown(chart, { key: k });
    key("ArrowRight");
    expect(out.textContent).toContain("Jan 2, 2015: value $");                   // first press = first point
    key("End");
    expect(out.textContent?.startsWith("Dec 31, 2024: value")).toBe(true);
    key("ArrowRight");                                                          // stays on the last point
    expect(out.textContent?.startsWith("Dec 31, 2024")).toBe(true);
    key("Home");
    expect(out.textContent?.startsWith("Jan 2, 2015")).toBe(true);
    key("PageDown");                                                            // weekly series: about a year
    expect(out.textContent).toContain(`round-ups added $`);
    expect(out.textContent?.startsWith("Jan 2, 2015")).toBe(false);
    expect(result.series_resolution).toBe("weekly");
    // the readout shows the API's own strings for that point
    expect(out.textContent).toContain(pts[52].value.replace(/\B(?=(\d{3})+(?!\d))/g, ","));
  });

  test("one point and an unchanged value get accurate summaries", () => {
    const one = { ...result, series: [pts[0]] };
    expect(chartSummary(one)).toBe(`On Jan 2, 2015 the value is $${pts[0].value} and the round-ups added are $${pts[0].added}.`);
    const flat = { ...result, series: [{ ...pts[0], value: "5.00" }, { ...pts[1], value: "5.00" }] };
    expect(chartSummary(flat)).toContain("the value stays at $5.00");
    expect(chartSummary(flat)).not.toContain("ups and downs");
  });
});
