"""Run browser layout/navigation checks. Optional dependency: Playwright + Chromium."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
from threading import Thread
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT)))
Thread(target=server.serve_forever, daemon=True).start()
base = "http://127.0.0.1:" + str(server.server_port) + "/"
checks = []
try:
    with sync_playwright() as playwright:
        executable = os.environ.get("SAMPLE_BROWSER_EXECUTABLE") or shutil.which("google-chrome")
        browser = playwright.chromium.launch(headless=True, executable_path=executable)
        page = browser.new_page()
        for width in (360, 768, 1440):
            page.set_viewport_size({"width": width, "height": 960})
            for filename, title in [("index.html", "Home"), ("about.html", "About"), ("services.html", "Services"), ("contact.html", "Contact")]:
                response = page.goto(base + filename)
                assert response.status == 200
                assert page.locator("h1").count() == 1
                assert page.locator('nav a[aria-current="page"]').inner_text() == title
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (width, filename, "horizontal overflow")
                for link in page.locator("nav a").all():
                    assert link.is_visible()
                checks.append({"width": width, "page": filename, "http_status": response.status, "navigation_visible": True, "horizontal_overflow": False})
        page.set_viewport_size({"width": 1440, "height": 960})
        page.goto(base)
        page.keyboard.press("Tab")
        assert page.locator(".skip").evaluate("e => e === document.activeElement")
        page.keyboard.press("Enter")
        assert page.url.endswith("#main")
        page.locator("nav").get_by_role("link", name="Services", exact=True).click()
        assert page.url.endswith("services.html")
        page.locator("nav").get_by_role("link", name="Contact", exact=True).click()
        assert page.locator('a[href="mailto:hello@example.com"]').is_visible()
        page.goto(base)
        page.screenshot(path=str(ROOT / "preview-desktop.png"), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        page.screenshot(path=str(ROOT / "preview-mobile.png"), full_page=True)
        browser.close()
    result = {"ok": True, "page_viewport_checks": checks, "keyboard_skip_link": "pass", "services_navigation": "pass", "contact_navigation_and_email_link": "pass", "screenshots": ["preview-desktop.png", "preview-mobile.png"], "scope": "Synthetic sample only; no client deployment or live form delivery tested"}
    (ROOT / "qa-results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
finally:
    server.shutdown()
