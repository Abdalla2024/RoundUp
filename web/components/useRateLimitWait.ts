"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import type { ApiError } from "@/lib/api";

/** After a 429 with Retry-After, keep the action disabled until the wait ends (FRONTEND.md §6, review L2).
 *  `note(err)` must be called in the same handler that shows the error, so the button is never enabled
 *  for even one render while the "please wait" message is on screen (CI failure, 2026-10-13). */
export function useRateLimitWait(): [boolean, (err: ApiError) => void] {
  const [waiting, setWaiting] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);
  const note = useCallback((err: ApiError) => {
    const secs = err.code === "RATE_LIMITED" && err.retryAfter ? Number.parseInt(err.retryAfter, 10) : 0;
    if (!(secs > 0)) return;
    if (timer.current) clearTimeout(timer.current);
    setWaiting(true);
    timer.current = setTimeout(() => setWaiting(false), secs * 1000);
  }, []);
  return [waiting, note];
}
