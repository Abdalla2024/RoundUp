"use client";
import { useEffect, useState } from "react";
import { Icon } from "./Icon";

type Theme = "system" | "light" | "dark";
const NEXT: Record<Theme, Theme> = { system: "light", light: "dark", dark: "system" };
const LABEL: Record<Theme, string> = { system: "the system setting", light: "light", dark: "dark" };
const KEY = "roundup-theme";

/** Colour theme: follows the system setting until the person picks light or dark; the choice is remembered in this browser only. */
export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("system");
  useEffect(() => {
    try { const t = localStorage.getItem(KEY); if (t === "light" || t === "dark") setTheme(t); } catch { /* storage blocked: stay on system */ }
  }, []);
  function choose(t: Theme) {
    setTheme(t);
    const el = document.documentElement;
    // colours ease between light and dark for a moment (the stylesheet switches this off under reduced motion)
    el.classList.add("theme-anim"); window.setTimeout(() => el.classList.remove("theme-anim"), 400);
    if (t === "system") el.removeAttribute("data-theme"); else el.setAttribute("data-theme", t);
    try { if (t === "system") localStorage.removeItem(KEY); else localStorage.setItem(KEY, t); } catch { /* ignore */ }
  }
  return (
    <button type="button" className="theme-toggle" onClick={() => choose(NEXT[theme])}
      aria-label={`Colour theme: ${LABEL[theme]}. Change to ${LABEL[NEXT[theme]]}.`} data-theme-choice={theme}>
      <Icon name={theme === "dark" ? "moon" : theme === "light" ? "sun" : "monitor"} />
    </button>
  );
}
