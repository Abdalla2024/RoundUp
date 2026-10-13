// Exact user-facing wording, mirroring COPY.md (owner-approved). Change COPY.md first, then here.
export const COPY = {
  label: "Synthetic scenario. Not a real fund, not real prices, and not a forecast.",
  footer: "RoundUp is an educational demo. No money moves and nothing here is advice or a forecast.",
  disclaimerLead: "Hypothetical simulation on a synthetic market.",
  disclaimer: (sample: boolean) =>
    `These results show how ${sample ? "sample round-ups" : "round-ups from your file"} behave in a made-up market ` +
    "scenario. No money was invested, the prices are not real, and this is not a forecast. It is not investment, " +
    "tax or financial advice.",
  keyPoints: [
    ["Made-up prices.", "The scenario is invented. It is not a real fund or a real market."],
    ["Not a forecast.", "It says nothing about what any market will do."],
    ["No fees included.", "Real round-up apps may charge fees that matter a lot for small balances."],
    ["Not advice.", "Nothing here suggests what you should do with your money."],
  ] as const,
  datesNote: "Scenario dates follow a real calendar, but the prices are made up.",
  explainer: "an AI explainer that only describes these numbers. It will never predict or advise.",
  savedIntro: "Saved scenarios keep their results exactly as calculated. They are not backed up in this demo. " +
    "Every saved result comes from a synthetic scenario: not a real fund, not real prices, and not a forecast.",
  signInNotSetUp: "Sign-in isn't set up on this copy of RoundUp, so saving is turned off. Everything else works.",
  signedOutSaved: "You can run simulations without an account. Signing in only lets you keep them. We send a " +
    "one-time sign-in link to your email; there is no password.",
  compareNote: "Both use the same round-ups, so “B minus A” is the same for value at end and for growth on " +
    "round-ups. Cash waiting and dividends kept as cash are part of the value at end. These differences come from this " +
    "one made-up scenario and say nothing about which choice works better in general.",
  wholeDollar: "These purchases were all whole-dollar amounts, so there was no spare change to invest.",
  // Added after the stage-5 web review (COPY.md, "Added after the stage-5 web review")
  notCounted: (n: string) => n === "1"
    ? "1 row adds no round-ups because it falls outside the chosen dates or is not a purchase (money coming in, a " +
      "payment, transfer or fee, or a pending or cancelled row)."
    : `${n} rows add no round-ups because they fall outside the chosen dates or are not purchases (money coming in, ` +
      "payments, transfers or fees, or pending or cancelled rows).",
  noneInWindow: "None of these rows were purchases between the chosen dates, so there was no spare change to invest.",
  noTradingDay: "There is no trading day between these dates, so there is nothing to show. Choose a wider date range.",
  chartKeys: "To read values with the keyboard, select the chart, then use the arrow keys, Home, End, Page Up and Page Down.",
  linkSentKeepTab: "Check your email for a sign-in link. It works once. Keep this tab open: your results stay here, " +
    "and you can save them once you\u2019re signed in.",
  seedHint: "A whole number from 0 to 2,147,483,647.",
  seedError: "Use a whole number from 0 to 2,147,483,647 for the sample number.",
  perDayError: "Use 1, 2 or 3 for purchases per day.",
  fileDates: (a: string, b: string) => `Dates in this file run from ${a} to ${b}.`,
  outsideDates: "Some rows fall outside the dates in step 4, so they won\u2019t add round-ups.",
  useFileDates: "Use this file\u2019s dates",
  slashDates: "Dates written with slashes are read as month/day/year (US style), so 01/06/2020 is January 6, 2020. " +
    "If your bank writes the day first, these dates will be wrong.",
  emptyFile: "The file is empty.",
  semicolons: "This file seems to use semicolons between columns. Save it with commas between columns and upload it again.",
  sameColumn: "Choose a different column for each field.",
  compareEmpty: "Run a simulation first; the comparison uses the same purchases and scenario.",
  sameForBoth: "same for both",
  seeAB: "see A and B",
  deleted: (name: string) => `Deleted \u201c${name}\u201d.`,
  errors: {
    network: "We couldn’t reach the RoundUp service. Check your connection and try again.",
    rateLimited: (s: string) => `Too many requests. Please wait ${s} seconds and try again.`,
    sessionExpired: "Your sign-in has expired. Sign in again to save. Your results are still here.",
    generic: "Something went wrong on our side. Please try again.",
  },
  strategy: {
    threshold: "Invest each time round-ups reach $5",
    next_session: "Invest after every purchase day",
    weekly: "Invest once a week",
    monthly: "Invest once a month",
  } as Record<string, string>,
  dividends: (reinvest: boolean) => (reinvest ? "Dividends reinvested" : "Dividends kept as cash"),
};
