"""Screenshots of the design mocks with the locally installed Google Chrome (Playwright, channel="chrome").

    .venv/bin/python web/mocks/capture.py
"""

import pathlib

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "screenshots"
PAGES = ["setup", "results", "compare", "saved"]

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome")
    for label, ctx_args in [("desktop", {"viewport": {"width": 1280, "height": 900}}),
                            ("mobile", {"viewport": {"width": 390, "height": 844}, "device_scale_factor": 2,
                                        "is_mobile": True, "has_touch": True})]:
        ctx = browser.new_context(**ctx_args)
        page = ctx.new_page()
        for name in PAGES:
            page.goto((HERE / f"{name}.html").as_uri())
            page.wait_for_load_state("networkidle")
            page.screenshot(path=str(OUT / f"{name}-{label}.png"), full_page=True)
        if label == "mobile":                      # the assumptions panel as a dialog on small screens
            page.goto((HERE / "compare.html").as_uri())
            page.wait_for_load_state("networkidle")
            page.click("#open-assumptions")
            page.screenshot(path=str(OUT / "compare-mobile-assumptions-open.png"))
        ctx.close()
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, color_scheme="dark")
    page = ctx.new_page()
    page.goto((HERE / "results.html").as_uri())
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT / "results-desktop-dark.png"), full_page=True)
    ctx.close()
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    page.goto((HERE / "saved.html").as_uri())
    page.wait_for_load_state("networkidle")
    for state in ["empty", "signed-out"]:
        page.click(f'[data-state="{state}"]')
        page.screenshot(path=str(OUT / f"saved-desktop-{state}.png"))
    ctx.close()
    browser.close()
print(sorted(x.name for x in OUT.glob("*.png")))
