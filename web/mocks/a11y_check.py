"""Accessibility checks on the mocks with the installed Chrome (Playwright): axe-core WCAG 2.2 A/AA scan,
keyboard walk (skip link first, every control reachable, visible focus), chart keyboard reading, dialog Esc.

    .venv/bin/python web/mocks/a11y_check.py   -> prints a report and writes web/mocks/a11y-report.json
"""

import json
import pathlib

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
AXE = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js"
PAGES = ["setup", "results", "compare", "saved"]
report = {}

FOCUS_JS = """() => { const e = document.activeElement; const cs = getComputedStyle(e);
  return {tag: e.tagName.toLowerCase(), text: (e.getAttribute('aria-label') || e.textContent || e.value || '').trim().slice(0, 40),
          outline: cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) >= 2,
          ring: cs.boxShadow !== 'none', visible: !!(e.offsetWidth || e.getBBox)}; }"""

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome")
    for mode, ctx_args in [("desktop", {"viewport": {"width": 1280, "height": 900}}),
                           ("mobile", {"viewport": {"width": 390, "height": 844}}),
                           ("dark", {"viewport": {"width": 1280, "height": 900}, "color_scheme": "dark"})]:
        ctx = browser.new_context(**ctx_args)
        for name in PAGES:
            page = ctx.new_page()
            page.goto((HERE / f"{name}.html").as_uri())
            page.wait_for_load_state("networkidle")
            page.add_script_tag(url=AXE)
            axe = page.evaluate("""async () => (await axe.run(document, {runOnly: {type: 'tag',
                values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice']}}))""")
            violations = [{"id": v["id"], "impact": v["impact"], "nodes": len(v["nodes"]),
                           "help": v["help"]} for v in axe["violations"]]
            entry = {"axe_violations": violations, "axe_passes": len(axe["passes"])}
            if mode != "dark":
                stops, seen = [], set()
                for _ in range(120):                       # walk the tab order
                    page.keyboard.press("Tab")
                    f = page.evaluate(FOCUS_JS)
                    key = (f["tag"], f["text"])
                    if key in seen and len(stops) > 3:
                        break
                    seen.add(key)
                    stops.append(f)
                entry["tab_stops"] = len(stops)
                entry["first_tab_stop"] = stops[0]["text"] if stops else None
                entry["stops_without_visible_focus"] = [s for s in stops if not (s["outline"] or s["ring"])]
                interactive = page.evaluate("""() => [...document.querySelectorAll('a[href],button:not([disabled]),input,select,textarea,[tabindex="0"],summary')]
                    .filter(e => e.offsetParent !== null || e.tagName === 'svg' || e.closest('svg')).length""")
                entry["visible_interactive_elements"] = interactive
            if name in ("results", "compare") and mode == "desktop":
                page.focus("svg.chart")
                page.keyboard.press("Home")
                page.wait_for_timeout(400)                   # announcements are throttled (250 ms)
                t1 = page.locator(".tooltip").first.text_content()
                page.keyboard.press("ArrowRight")
                page.wait_for_timeout(400)
                t2 = page.locator(".tooltip").first.text_content()
                entry["chart_keyboard"] = {"home": t1, "after_arrow": t2, "changes": t1 != t2 and bool(t1)}
            if name == "compare" and mode == "mobile":
                page.focus("#open-assumptions")
                page.keyboard.press("Enter")
                opened = page.evaluate("document.querySelector('#assumptions-dialog').open")
                page.keyboard.press("Escape")
                closed = not page.evaluate("document.querySelector('#assumptions-dialog').open")
                back = page.evaluate("document.activeElement.id")
                entry["dialog"] = {"opens_with_enter": opened, "closes_with_escape": closed, "focus_returns_to": back}
            report[f"{name}/{mode}"] = entry
            page.close()
        ctx.close()
    browser.close()
(HERE / "a11y-report.json").write_text(json.dumps(report, indent=1))
for k, v in report.items():
    print(k, "| axe violations:", [(x["id"], x["impact"], x["nodes"]) for x in v["axe_violations"]] or "none",
          "| tab stops:", v.get("tab_stops"), "| first:", v.get("first_tab_stop"),
          "| no visible focus:", len(v.get("stops_without_visible_focus", [])),
          "|", v.get("chart_keyboard", {}).get("changes", ""), v.get("dialog", ""))
