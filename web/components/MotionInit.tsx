"use client";
import { usePathname } from "next/navigation";
import { useEffect } from "react";
import { installInPageLinks } from "@/lib/inpage";
import { startReveal } from "@/lib/reveal";

/** Switches the page's motion on (after hydration): smooth in-page links with focus handling, and entrance animations as things come into
 *  view. Renders nothing. Both parts do nothing under prefers-reduced-motion (instant jumps, no entrance); see lib/inpage.ts and lib/reveal.ts. */
export function MotionInit() {
  const path = usePathname();
  useEffect(() => installInPageLinks(), []);
  useEffect(() => startReveal(), [path]);
  return null;
}
