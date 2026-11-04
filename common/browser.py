from contextlib import contextmanager
from typing import Generator

from playwright.sync_api import Browser, sync_playwright

SITE_ACTION_TIMEOUT_MS = 120_000


@contextmanager
def open_browser(headless: bool = False) -> Generator[Browser, None, None]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        try:
            yield browser
        finally:
            browser.close()
