// Builds app/tokens.css from app/tokens.json (the single source of the palette). Run: npm run tokens. tests/contrast.test.ts fails if the
// file is out of date or any colour pair is below its minimum contrast.
import fs from "node:fs";
import path from "node:path";
const dir = path.resolve("app");                      // run from the web folder
const kebab = (s) => s.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
const block = (t) => Object.entries(t).map(([k, v]) => `  --${kebab(k)}: ${v};`).join("\n");

export function build() {
  const { themes } = JSON.parse(fs.readFileSync(path.join(dir, "tokens.json"), "utf8"));
  return `/* GENERATED from tokens.json by tools/gen-tokens-css.mjs. Do not edit by hand (run: npm run tokens). */
:root {
  color-scheme: light;
${block(themes.light)}
}
/* the system setting, unless the person chose light explicitly */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
${block(themes.dark).replace(/^/gm, "  ")}
  }
}
/* dark chosen explicitly with the toggle */
:root[data-theme="dark"] {
  color-scheme: dark;
${block(themes.dark)}
}
`;
}

if (process.argv[1] && process.argv[1].endsWith("gen-tokens-css.mjs")) {
  fs.writeFileSync(path.join(dir, "tokens.css"), build());
  console.log("wrote app/tokens.css");
}
