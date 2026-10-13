// Owner rule: the browser never calculates a money figure. Static check over the web source with the TypeScript
// parser: any arithmetic or numeric conversion touching money-like data fails this test.
import fs from "node:fs";
import path from "node:path";
import ts from "typescript";
import { describe, expect, test } from "vitest";

const ROOT = path.resolve(__dirname, "..");
const DIRS = ["app", "components", "lib"];
// Drawing-only exception (documented in the file): converts strings to numbers for line positions and axis scale.
const CHART_FILES = [path.join("components", "ValueChart.tsx"), path.join("components", "ChartCanvas.tsx")];
const MONEY = /\b(contributed|ending_value|gain|gain_pct|value|added|amount|cash|dividends?_\w*|price|shares|below_by|uninvested_cash|roundups_waiting|dividends_as_cash|holdings_value|receivables|summary|difference|money)\b/i;
const ARITH = new Set([ts.SyntaxKind.PlusToken, ts.SyntaxKind.MinusToken, ts.SyntaxKind.AsteriskToken,
  ts.SyntaxKind.SlashToken, ts.SyntaxKind.PercentToken, ts.SyntaxKind.AsteriskAsteriskToken,
  ts.SyntaxKind.PlusEqualsToken, ts.SyntaxKind.MinusEqualsToken, ts.SyntaxKind.AsteriskEqualsToken, ts.SyntaxKind.SlashEqualsToken]);

export function findViolations(source: string, file: string): string[] {
  const sf = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, file.endsWith("x") ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
  const out: string[] = [];
  const isChart = CHART_FILES.some((c) => file.endsWith(c));
  const isString = (n: ts.Node) => ts.isStringLiteral(n) || ts.isNoSubstitutionTemplateLiteral(n) || ts.isTemplateExpression(n);
  const at = (n: ts.Node) => `${file}:${sf.getLineAndCharacterOfPosition(n.getStart()).line + 1}`;
  function visit(n: ts.Node) {
    if (ts.isCallExpression(n)) {
      const callee = n.expression.getText(sf);
      if (["parseFloat", "Number.parseFloat"].includes(callee)) out.push(`${at(n)} ${callee}()`);
      if (callee === "Number" && !isChart) out.push(`${at(n)} Number()`);
      if (/\.toFixed$|\.toPrecision$/.test(callee)) out.push(`${at(n)} ${callee}`);
      if (/^Math\./.test(callee) && !isChart) out.push(`${at(n)} ${callee}`);
      if (/^BigInt$|Decimal/.test(callee)) out.push(`${at(n)} ${callee}`);
    }
    if (ts.isPrefixUnaryExpression(n) && (n.operator === ts.SyntaxKind.PlusToken || n.operator === ts.SyntaxKind.MinusToken)
        && !ts.isNumericLiteral(n.operand) && MONEY.test(n.operand.getText(sf))) out.push(`${at(n)} unary ${n.getText(sf)}`);
    if (ts.isBinaryExpression(n) && ARITH.has(n.operatorToken.kind)) {
      const plusOnStrings = n.operatorToken.kind === ts.SyntaxKind.PlusToken && (isString(n.left) || isString(n.right));
      if (!plusOnStrings && (MONEY.test(n.left.getText(sf)) || MONEY.test(n.right.getText(sf)))) {
        out.push(`${at(n)} arithmetic: ${n.getText(sf).slice(0, 80)}`);
      }
    }
    ts.forEachChild(n, visit);
  }
  visit(sf);
  return out;
}

function sources(): [string, string][] {
  const files: [string, string][] = [];
  const walk = (d: string) => fs.readdirSync(path.join(ROOT, d), { withFileTypes: true }).forEach((e) => {
    const rel = path.join(d, e.name);
    if (e.isDirectory()) walk(rel);
    else if (/\.(ts|tsx)$/.test(e.name)) files.push([rel, fs.readFileSync(path.join(ROOT, rel), "utf8")]);
  });
  DIRS.forEach(walk);
  return files;
}

describe("no money arithmetic in the browser", () => {
  test("the web source has no arithmetic or numeric conversion on money", () => {
    const all = sources().flatMap(([f, s]) => findViolations(s, f));
    expect(all).toEqual([]);
  });
  test("the checker itself catches violations (negative controls)", () => {
    const bad = [
      "const g = summary.ending_value - summary.contributed;",
      "const t = parseFloat(result.summary.gain);",
      "const x = Number(s.contributed) * 2;",
      "const y = (+p.value).toFixed(2);",
      "let total = 0; total += cash;",
      "const r = Math.round(s.gain_pct);",
    ];
    for (const b of bad) expect(findViolations(b, "components/Bad.tsx").length, b).toBeGreaterThan(0);
  });
  test("the chart drawing files are the only ones that convert strings to numbers", () => {
    const users = sources().filter(([, s]) => /\bNumber\(/.test(s)).map(([f]) => f);
    expect(users.sort()).toEqual([...CHART_FILES].sort());
  });
});
