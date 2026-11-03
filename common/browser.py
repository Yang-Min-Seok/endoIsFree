from contextlib import contextmanager
from typing import Iterator

from playwright.sync_api import Browser, sync_playwright

SITE_ACTION_TIMEOUT_MS = 120_000


@contextmanager
def open_browser() -> Iterator[Browser]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        try:
            yield browser
        finally:
            browser.close()
