// Formatting ONLY. Inputs are engine strings like "1789.92" or "-65.11"; outputs are display strings.
// No arithmetic on money is allowed in the web app (tests/no-money-arithmetic.test.ts enforces this).

const group = (digits: string) => digits.replace(/\B(?=(\d{3})+(?!\d))/g, ",");

/** "1789.92" -> "$1,789.92"; "-65.11" -> "−$65.11" (true minus sign). */
export function money(s: string): string {
  const neg = s.startsWith("-");
  const [whole, frac = "00"] = (neg ? s.slice(1) : s).split(".");
  return `${neg ? "−" : ""}$${group(whole)}.${frac}`;
}

/** Signed: "+$1,159.45" / "−$65.11" / "$0.00". */
export function signedMoney(s: string): string {
  if (s.startsWith("-")) return money(s);
  return /^0+(\.0+)?$/.test(s) ? money(s) : `+${money(s)}`;
}

/** The absolute amount as written ("-65.11" -> "$65.11"), for sentences that say "more"/"less" in words. */
export function unsignedMoney(s: string): string {
  return money(s.startsWith("-") ? s.slice(1) : s);
}

export const isNegative = (s: string) => s.startsWith("-");

/** "3606" -> "3,606"; "-206" -> "−206" with an explicit sign when asked. */
export function count(s: string | number, signed = false): string {
  const t = String(s);
  const neg = t.startsWith("-");
  const body = group(neg ? t.slice(1) : t);
  if (neg) return `−${body}`;
  return signed && body !== "0" ? `+${body}` : body;
}

/** "64.78" -> "+64.78%"; "n/a" stays "n/a". */
export function signedPct(s: string): string {
  if (s === "n/a") return "n/a";
  return s.startsWith("-") ? `−${s.slice(1)}%` : `+${s}%`;
}

/** "2024-12-31" -> "Dec 31, 2024" (UTC, so the date never shifts). */
export function longDate(iso: string): string {
  return new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-US",
    { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" });
}
