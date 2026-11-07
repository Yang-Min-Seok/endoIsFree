import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from playwright.sync_api import Page

from common.config import ApplicationConfig, UserAccount


@dataclass
class WorkflowState:
    final_confirmation_accepted: bool = False
    final_confirmation_accepted_at: Optional[float] = None
    site_communication_error: bool = False


@dataclass(frozen=True)
class ExecutionContext:
    project_root: Path
    logger: logging.Logger
    page: Page
    user: UserAccount
    user_index: int
    user_count: int
    config: ApplicationConfig
    application_round: int
    application_round_count: int
    workflow_state: WorkflowState = field(default_factory=WorkflowState)
