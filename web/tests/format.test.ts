import { describe, expect, test } from "vitest";
import { count, counted, longDate, money, signedMoney, signedPct, unsignedMoney } from "@/lib/format";

describe("format (display only)", () => {
  test("money", () => {
    expect(money("1789.92")).toBe("$1,789.92");
    expect(money("-65.11")).toBe("−$65.11");
    expect(money("0.00")).toBe("$0.00");
    expect(money("1234567.05")).toBe("$1,234,567.05");
  });
  test("signed and unsigned", () => {
    expect(signedMoney("1159.45")).toBe("+$1,159.45");
    expect(signedMoney("-65.11")).toBe("−$65.11");
    expect(signedMoney("0.00")).toBe("$0.00");
    expect(unsignedMoney("-65.11")).toBe("$65.11");
  });
  test("counts, percentages and dates", () => {
    expect(count("3606")).toBe("3,606");
    expect(count("-206", true)).toBe("−206");
    expect(count("12", true)).toBe("+12");
    expect(count("0", true)).toBe("0");
    expect(signedPct("64.78")).toBe("+64.78%");
    expect(signedPct("-4.00")).toBe("−4.00%");
    expect(signedPct("n/a")).toBe("n/a");
    expect(signedPct("0.00")).toBe("0.00%");                 // reviewer L8: no "+" on zero
    expect(counted("1", "purchase", "purchases")).toBe("1 purchase");   // reviewer L8: "1 purchases"
    expect(counted("3606", "purchase", "purchases")).toBe("3,606 purchases");
    expect(counted("0", "time", "times")).toBe("0 times");
    expect(longDate("2024-12-31")).toBe("Dec 31, 2024");
    expect(longDate("2012-01-03")).toBe("Jan 3, 2012");
  });
  test("format never changes digits (strings in, same digits out)", () => {
    for (const s of ["0.01", "999999.99", "-0.05", "1.10"]) {
      expect(money(s).replace(/[^\d.]/g, "")).toBe(s.replace("-", ""));
    }
  });
});
