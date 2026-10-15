// One icon set for the whole app: 24 px stroke icons drawn for this project (inline SVG, no library). Always decorative: they carry
// aria-hidden and never hold meaning alone, so every use sits next to text (or inside a control that has an accessible name).
const PATHS = {
  wallet: <><path d="M3 8a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v1" /><rect x="3" y="8" width="18" height="12" rx="2" /><circle cx="16.5" cy="14" r="1.2" /></>,
  coins: <><circle cx="12" cy="12" r="8.5" /><path d="M12 8v8M8 12h8" /></>,
  trend: <><path d="M3 17l6-6 4 4 8-8" /><path d="M15 7h6v6" /></>,
  percent: <><circle cx="7" cy="7" r="2.5" /><circle cx="17" cy="17" r="2.5" /><path d="M19 5L5 19" /></>,
  clock: <><circle cx="12" cy="12" r="8.5" /><path d="M12 7.5V12l3 2" /></>,
  calendar: <><rect x="3.5" y="5" width="17" height="15" rx="2.5" /><path d="M3.5 10h17M8 3v4M16 3v4" /></>,
  layers: <><path d="M12 3l9 5-9 5-9-5 9-5z" /><path d="M3 13l9 5 9-5" /></>,
  sliders: <><path d="M4 6h8M16 6h4M4 12h3M11 12h9M4 18h10M18 18h2" /><circle cx="14" cy="6" r="2" /><circle cx="9" cy="12" r="2" /><circle cx="16" cy="18" r="2" /></>,
  repeat: <><path d="M17 3l4 4-4 4" /><path d="M3 11V9a3 3 0 0 1 3-3h15" /><path d="M7 21l-4-4 4-4" /><path d="M21 13v2a3 3 0 0 1-3 3H3" /></>,
  upload: <><path d="M12 16V4M7 9l5-5 5 5" /><path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" /></>,
  spark: <path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9L12 3z" />,
  check: <path d="M5 12.5l4.5 4.5L19 7.5" />,
  alert: <><path d="M12 4l9 16H3L12 4z" /><path d="M12 10v4M12 17h.01" /></>,
  info: <><circle cx="12" cy="12" r="8.5" /><path d="M12 11v5M12 8h.01" /></>,
  arrow: <path d="M5 12h14M13 6l6 6-6 6" />,
  sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>,
  moon: <path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z" />,
  monitor: <><rect x="3" y="4" width="18" height="12" rx="2" /><path d="M8 20h8M12 16v4" /></>,
  bookmark: <path d="M6 3.5h12v17l-6-4-6 4v-17z" />,
  trash: <><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13" /></>,
  shield: <path d="M12 3l8 3v6c0 4.5-3.2 7.8-8 9-4.8-1.2-8-4.5-8-9V6l8-3z" />,
  open: <><path d="M14 4h6v6M20 4l-9 9" /><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" /></>,
} as const;

export type IconName = keyof typeof PATHS;

export function Icon({ name, size = 20 }: { name: IconName; size?: number }) {
  return (
    <svg className="icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75}
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">{PATHS[name]}</svg>
  );
}
