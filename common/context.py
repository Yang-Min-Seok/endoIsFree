import logging
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import Page


@dataclass(frozen=True)
class ExecutionContext:
    project_root: Path
    logger: logging.Logger
    page: Page
