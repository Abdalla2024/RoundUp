import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { SavedView } from "@/components/SavedView";
import { COPY } from "@/lib/copy";
import simulate from "../fixtures/simulate.json";
import { renderWith, SESSION } from "../helpers";

const list = vi.fn(), del = vi.fn();
vi.mock("@/lib/saved", () => ({ listSaved: (...a: unknown[]) => list(...a), deleteSaved: (...a: unknown[]) => del(...a) }));
const ROW = { id: "11111111-1111-1111-1111-111111111111", name: "Crash test", created_at: "2026-10-12T10:00:00Z",
  config: { scenario_id: "crash-and-recovery", style: "broad", start: "2015-01-02", end: "2024-12-31", strategy: "threshold", reinvest: true },
  scenario_results: [{ result: simulate.response.result, engine_version: "0.2.0", model_version: "scenario-model-1",
    scenario_seed: 1202, market_checksum: "a".repeat(64), input_checksum: "b".repeat(64), created_at: "2026-10-12T10:00:00Z" }] };
beforeEach(() => { list.mockReset(); del.mockReset(); });

describe("Saved scenarios screen", () => {
  test("sign-in not set up", () => {
    renderWith(<SavedView />, { mode: "off" });
    expect(screen.getByText(COPY.signInNotSetUp)).toBeTruthy();
  });
  test("signed out: sign-in form with the plain explanation", () => {
    renderWith(<SavedView />);
    expect(screen.getByRole("heading", { name: "Sign in to see saved scenarios" })).toBeTruthy();
    expect(screen.getByText(COPY.signedOutSaved)).toBeTruthy();
    expect(screen.getByLabelText("Email")).toBeTruthy();
  });
  test("signed out: an invalid email is explained", () => {
    renderWith(<SavedView />);
    fireEvent.click(screen.getByRole("button", { name: "Email me a sign-in link" }));
    expect(screen.getByRole("alert").textContent).toContain("Enter an email address like name@example.com.");
  });
  test("signed in, nothing saved: empty state", async () => {
    list.mockResolvedValue([]);
    renderWith(<SavedView />, { session: SESSION });
    await waitFor(() => expect(screen.getByRole("heading", { name: "Nothing saved yet" })).toBeTruthy());
    expect(list).toHaveBeenCalledWith("test-token");
  });
  test("signed in, with scenarios: card shows label wording and engine strings", async () => {
    list.mockResolvedValue([ROW]);
    const { container } = renderWith(<SavedView />, { session: SESSION });
    await waitFor(() => expect(screen.getByRole("heading", { name: "Crash test" })).toBeTruthy());
    const text = container.textContent ?? "";
    expect(text).toContain("Synthetic scenario: crash and recovery");
    expect(text).toContain("value at end $2,949.37 on Dec 31, 2024");
    expect(text).toContain(COPY.savedIntro);
  });
  test("delete asks first, then deletes and reloads", async () => {
    list.mockResolvedValueOnce([ROW]).mockResolvedValueOnce([]);
    del.mockResolvedValue(undefined);
    renderWith(<SavedView />, { session: SESSION });
    await waitFor(() => screen.getByRole("button", { name: "Delete Crash test" }));
    fireEvent.click(screen.getByRole("button", { name: "Delete Crash test" }));
    expect(screen.getByText(/This removes the scenario and its results/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(del).toHaveBeenCalledWith("test-token", ROW.id));
    await waitFor(() => expect(screen.getByRole("heading", { name: "Nothing saved yet" })).toBeTruthy());
  });
  test("load error and expired session are plain language", async () => {
    list.mockImplementation(() => Promise.reject(Object.assign(new Error("x"), { code: "AUTH" })));
    renderWith(<SavedView />, { session: SESSION });
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain(COPY.errors.sessionExpired));
  });

  test("L10: after a delete, focus goes to the heading and the deletion is announced; names are isolated with <bdi>", async () => {
    const odd = { ...ROW, name: "\u202Eemoji" };
    list.mockResolvedValueOnce([odd]).mockResolvedValueOnce([]);
    del.mockResolvedValue(undefined);
    const { container } = renderWith(<SavedView />, { session: SESSION });
    await waitFor(() => screen.getByRole("button", { name: /^Delete / }));
    expect(container.querySelector(".saved-item h2 bdi")?.textContent).toBe("\u202Eemoji");
    fireEvent.click(screen.getByRole("button", { name: /^Delete / }));
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(screen.getByRole("status").textContent).toBe(COPY.deleted("\u202Eemoji")));
    expect(document.activeElement).toBe(screen.getByRole("heading", { level: 1, name: "Saved scenarios" }));
  });
});
