import logging
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import Page

from common.config import ApplicationConfig, UserAccount


@dataclass(frozen=True)
class ExecutionContext:
    project_root: Path
    logger: logging.Logger
    page: Page
    user: UserAccount
    user_index: int
    user_count: int
    config: ApplicationConfig
