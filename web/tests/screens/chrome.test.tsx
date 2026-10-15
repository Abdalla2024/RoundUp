import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { AuthProvider } from "@/components/AuthContext";
import { SiteFooter, SiteHeader } from "@/components/Chrome";
import { COPY } from "@/lib/copy";
import { csvHeader } from "@/lib/csvHeader";

describe("Site chrome and helpers", () => {
  test("label strip and footer wording on every page", () => {
    render(<AuthProvider initial={{ session: null, mode: "supabase" }}><SiteHeader /><SiteFooter /></AuthProvider>);
    expect(screen.getByText(COPY.label)).toBeTruthy();
    expect(screen.getByText(new RegExp(COPY.footer.slice(0, 40)))).toBeTruthy();
    expect(screen.getByRole("navigation", { name: "Main" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Sign in" })).toBeTruthy();
  });
  test("compact menu: a button that names itself, reports open/closed, owns the navigation, and closes with Escape (focus returns to it)", () => {
    render(<AuthProvider initial={{ session: null, mode: "supabase" }}><SiteHeader /></AuthProvider>);
    const btn = screen.getByRole("button", { name: "Menu" });
    const nav = screen.getByRole("navigation", { name: "Main" });
    expect(btn.getAttribute("aria-controls")).toBe(nav.id);
    expect(btn.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(btn);
    expect(btn.getAttribute("aria-expanded")).toBe("true");
    expect(nav.getAttribute("data-open")).toBe("true");
    screen.getByRole("link", { name: "Compare" }).focus();
    fireEvent.keyDown(screen.getByRole("link", { name: "Compare" }), { key: "Escape" });
    expect(btn.getAttribute("aria-expanded")).toBe("false");
    expect(document.activeElement).toBe(btn);
  });
  test("choosing a link closes the menu; the menu is not a role=menu (it is a plain disclosure of links)", () => {
    const { container } = render(<AuthProvider initial={{ session: null, mode: "supabase" }}><SiteHeader /></AuthProvider>);
    const btn = screen.getByRole("button", { name: "Menu" });
    fireEvent.click(btn);
    fireEvent.click(screen.getByRole("link", { name: "Saved scenarios" }));
    expect(btn.getAttribute("aria-expanded")).toBe("false");
    expect(container.querySelector('[role="menu"], [role="menuitem"]')).toBeNull();
  });
  test("no sign-in link when sign-in is not set up", () => {
    render(<AuthProvider initial={{ session: null, mode: "off" }}><SiteHeader /></AuthProvider>);
    expect(screen.queryByRole("link", { name: "Sign in" })).toBeNull();
  });
  test("CSV header reader handles quotes, BOM and CRLF", () => {
    expect(csvHeader('﻿"Date","Amount, USD",Description\r\n1,2,3')).toEqual(["Date", "Amount, USD", "Description"]);
    expect(csvHeader('a,"b ""q""",c\n')).toEqual(["a", 'b "q"', "c"]);
  });
});
