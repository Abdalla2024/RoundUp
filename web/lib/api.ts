import type { AssumptionsResponse, CompareRequest, CompareResponse, Mapping, ParseResponse, ScenariosResponse,
  SimulateRequest, SimulateResponse } from "./types";
import { COPY } from "./copy";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public fields: string[] = [],
              public retryAfter: string | null = null, public requestId: string | null = null) {
    super(message);
  }
}

async function call<T>(path: string, init?: RequestInit, token?: string): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { ...(init?.body ? { "Content-Type": "application/json" } : {}),
                 ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    });
  } catch {
    throw new ApiError(0, "NETWORK", COPY.errors.network);
  }
  const requestId = res.headers.get("X-Request-ID");
  if (!res.ok) {
    let body: { error?: { code?: string; message?: string; fields?: string[] } } = {};
    try { body = await res.json(); } catch { /* non-JSON error body */ }
    const retry = res.headers.get("Retry-After");
    const code = body.error?.code ?? "INTERNAL";
    const message = code === "RATE_LIMITED" && retry ? COPY.errors.rateLimited(retry)
      : body.error?.message ?? COPY.errors.generic;
    throw new ApiError(res.status, code, message, body.error?.fields ?? [], retry, requestId);
  }
  return res.json() as Promise<T>;
}

const post = (body: unknown) => ({ method: "POST", body: JSON.stringify(body) });

export const api = {
  scenarios: () => call<ScenariosResponse>("/v1/scenarios"),
  assumptions: () => call<AssumptionsResponse>("/v1/assumptions"),
  simulate: (req: SimulateRequest) => call<SimulateResponse>("/v1/simulate", post({ ...req, buys: "none" })),
  compare: (req: CompareRequest) => call<CompareResponse>("/v1/compare", post({ ...req, buys: "none" })),
  parse: (csv: string, mapping: Mapping, sign_convention: string | null) =>
    call<ParseResponse>("/v1/transactions/parse", post({ csv, mapping, sign_convention })),
  save: (req: SimulateRequest, name: string, saveTransactions: boolean, token: string) =>
    call<SimulateResponse & { id: string }>("/v1/saved",
      post({ ...req, buys: "none", name, save_transactions: saveTransactions }), token),
};
