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
  // Sign convention (stage 6; wording in COPY.md "Upload step, after the owner's testing on the preview")
  signingPrompt: "Choose how amounts are signed",
  signingHelp: "Banks write purchases in different ways. Look at one purchase in your file. If it is a positive number " +
    "(like 6.16), choose \u201cPurchases are positive numbers\u201d. If it has a minus sign (like -6.16), choose " +
    "\u201cPurchases are negative numbers\u201d. If money out and money in are in two columns, or a column says debit " +
    "or credit, choose the matching option.",
  signingOptionHelp: {
    debits_positive: "Purchases are positive numbers, like 6.16. Refunds and other money coming in are negative, like -12.50, and never add round-ups.",
    debits_negative: "Purchases are negative numbers, like -6.16. Money coming in is positive, like 12.50, and never adds round-ups.",
    separate_columns: "Purchases are in the money out column. Money coming in is in the money in column and never adds round-ups.",
    type_column: "A column says debit or credit for each row. Debits are purchases. Credits are money coming in and never add round-ups.",
  } as Record<string, string>,
  signingChosenBecause: (out: string, inn: string) =>
    `We chose this because your file has columns named \u201c${out}\u201d and \u201c${inn}\u201d. Change it if that is wrong.`,
  signingChosenBecauseType: (col: string) =>
    `We chose this because your file has a column named \u201c${col}\u201d next to the amount. Change it if that is wrong.`,
  chooseSigning: "Choose how amounts are signed in this file, in the box named \u201cHow are amounts signed?\u201d. Your options are: " +
    "\u201cPurchases are positive numbers\u201d, \u201cPurchases are negative numbers\u201d, " +
    "\u201cMoney out and money in columns\u201d, or \u201cA column says debit or credit\u201d.",
  chooseSigningField: "Choose one of the four options.",
  checkCredits: (n: string) => `Money coming in (refunds, deposits): ${n}. These never add round-ups.`,
  checkNotPosted: (n: string) => `Pending or cancelled rows: ${n}. These are left out.`,
  checkWholeDollar: (n: string) => `Purchases of an exact dollar amount: ${n}. These add $0.00, because there is no spare change.`,
  checkUnrecognised: (n: string) => (n === "1" ? "1 row has a status we don\u2019t recognise." : `${n} rows have a status we don\u2019t recognise.`) +
    " We count only the statuses posted, settled, cleared and completed as purchases, so these rows are left out for now.",
  countUnrecognised: "Count these rows as purchases too",
  willCountUnrecognised: (n: string) => (n === "1" ? "1 row will be counted as a purchase." : `${n} rows will be counted as purchases.`),
  tabs: "This file seems to use tabs between columns. Save it as a CSV with commas between columns and upload it again.",
  checkPurchases: (n: string) => `Purchases that will add round-ups: ${n}.`,
  checkNoPurchases: "None of these rows would add round-ups. If you expected some, check the box named \u201cHow are amounts signed?\u201d: " +
    "with the wrong choice, purchases can look like money coming in.",
  checkRagged: (n: string) => (n === "1" ? "1 row has more values than the header has columns." : `${n} rows have more values than the header has columns.`) +
    " A comma inside a number (like 6,16) splits it in two, so the amount can be read wrongly. Put such amounts in quotes, or use a dot (6.16).",
  checkNoRows: "This file has no rows below the header.",
  dateFormats: "Dates must look like 2024-01-31, or like 01/31/2024 (month first). A time after the date is not accepted.",
  // Typical spending (R-1.9, owner decision 2026-10-15): the user gives a weekly count and an average round-up; no random numbers.
  typicalTitle: "Typical spending",
  typicalDesc: "An estimate from averages: you tell us how many purchases you make in a typical week.",
  typicalEstimate: "This is an estimate based on averages. Real spending varies.",
  perWeekLabel: "How many purchases do you make in a typical week?",
  perWeekHint: "A whole number from 1 to 60. The purchases are spread evenly across the week, weekends included.",
  perWeekError: "Enter a whole number of purchases from 1 to 60.",
  adjustAverage: "Adjust the average round-up",
  adjustAverageBody: "A round-up is the spare change up to the next dollar. Across everyday prices the average spare change is about " +
    "50 cents, so $0.50 is the starting setting. Choose a higher average if your purchases usually end just under a whole dollar, " +
    "or a lower one if they usually end just over.",
  averageLabel: "Average round-up per purchase",
  averageHint: "From $0.01 to $0.99, written like 0.50.",
  averageError: "Enter an average round-up from $0.01 to $0.99, written like 0.50.",
  typicalSetting: (n: string, avg: string) => `Typical spending: ${n} purchases a week, an average round-up of ${avg}`,
  typicalNote: (n: string, avg: string) => `Estimate: ${n} purchases a week, each with a round-up of ${avg}. Real spending varies.`,
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
