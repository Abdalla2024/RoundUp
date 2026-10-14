// Reads ONLY the header row of a CSV in the browser, so the user can choose columns. All row parsing,
// classification and validation happen in the API's parse endpoint.
export function csvHeader(text: string): string[] {
  const t = text.replace(/^﻿/, "").replace(/^(?:[ \t]*\r?\n)+/, "");      // blank lines before the header are ignored
  const out: string[] = [];
  let cur = "", quoted = false;
  for (let i = 0; i < t.length; i++) {
    const c = t[i];
    if (quoted) {
      if (c === '"' && t[i + 1] === '"') { cur += '"'; i++; }
      else if (c === '"') quoted = false;
      else cur += c;
    } else if (c === '"') quoted = true;
    else if (c === ",") { out.push(cur.trim()); cur = ""; }
    else if (c === "\n" || c === "\r") break;
    else cur += c;
  }
  out.push(cur.trim());
  return out.filter((h, i) => h !== "" || i < out.length - 1);
}
