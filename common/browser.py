from contextlib import contextmanager
from typing import Iterator

from playwright.sync_api import Page, sync_playwright


@contextmanager
def open_browser() -> Iterator[Page]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        try:
            yield browser.new_page()
        finally:
            browser.close()
