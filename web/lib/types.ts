// Shapes from API.md / engine FORMAT.md. Every money value is a STRING from the engine; the web app never computes.
export type Strategy = "threshold" | "next_session" | "weekly" | "monthly";
export type Style = "broad" | "dividend";

export interface TransactionIn {
  posted_date: string; amount: string; direction: "debit" | "credit";
  status?: "posted" | "pending" | "cancelled" | "unrecognised"; category?: "purchase" | "non_purchase";
}
export interface RunOptions {
  scenario_id: string; style: Style; start: string; end: string;
  transactions?: TransactionIn[]; generate?: { seed: number; max_per_day: number }; buys?: "all" | "none";
}
export interface SimulateRequest extends RunOptions { strategy: Strategy; reinvest: boolean }
export interface CompareRequest extends RunOptions { a: { strategy: Strategy; reinvest: boolean }; b: { strategy: Strategy; reinvest: boolean } }

export interface Dip { date: string; value: string; added: string; below_by: string }
export interface Summary {
  contributed: string; roundup_buys: string; dividend_buys: string; dividends_earned: string; dividends_paid: string;
  shares: string; holdings_value: string; uninvested_cash: string; roundups_waiting: string; dividends_as_cash: string;
  receivables: string; ending_value: string; gain: string; gain_pct: string; as_of: string; deepest_dip: Dip | null;
}
export interface Point { date: string; value: string; carried: string; added: string }
export interface Result {
  status: "ok"; summary: Summary; series: Point[]; series_resolution: "daily" | "weekly"; series_rule: string;
  transactions_used: string; transactions_ignored: string; engine_version: string; buys: unknown[];
}
export interface Meta {
  engine_version: string; model_version: string; scenario_id: string; style: Style; scenario_seed: number;
  market_checksum: string; input_checksum: string; label: string;
}
export interface SimulateResponse { result: Result; meta: Meta }
export interface CompareResponse {
  a: Result; b: Result; meta: Meta;
  difference: { ending_value: string; gain: string; dividends_earned: string; uninvested_cash: string;
                roundup_buys: string; dividend_buys: string };
}
export interface ScenarioStyle { style: Style; name: string; symbol: string; start: string; end: string; market_checksum: string }
export interface ScenarioInfo { id: string; name: string; description: string; label: string; seed: number; styles: ScenarioStyle[] }
export interface ScenariosResponse { label: string; model_version: string; scenarios: ScenarioInfo[] }
export interface AssumptionsResponse { disclaimer: string; assumptions: { id: string; title: string; text: string }[] }
export interface ParsedRow {
  row: number; posted_date: string | null; amount: string | null; direction: "debit" | "credit";
  status: "posted" | "pending" | "cancelled" | "unrecognised"; category: "purchase" | "non_purchase";
  problem: "invalid_amount" | "invalid_date" | "zero_amount" | null;
}
export interface ParseResponse {
  columns: string[]; date_column_used: string; sign_convention: string; transactions: ParsedRow[];
  summary: { rows: number; usable: number; problems: Record<string, number>; non_purchases: number; credits: number;
    not_posted: number; whole_dollar: number; purchases: number; unrecognised_status: number; ragged_rows: number; possible_duplicates: number };
}
export type Mapping = Partial<Record<"date" | "posted_date" | "amount" | "debit" | "credit" | "type" | "status" |
  "description" | "external_id" | "account", string | null>>;
