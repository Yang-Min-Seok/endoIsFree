import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from playwright.sync_api import Page

from common.config import ApplicationConfig, UserAccount


class ApplicationCompletionNotConfirmed(RuntimeError):
    pass


@dataclass
class WorkflowState:
    current_step: str = ""
    current_process: str = ""
    step7_confirmation_accepted: bool = False
    application_success_confirmed: bool = False
    site_communication_error: bool = False


@dataclass
class CheckWorkflowState:
    has_unconfirmed_winning_results: Optional[bool] = None
    account_workflow_complete: bool = False
    losing_applications: list["LosingApplicationRecord"] = field(
        default_factory=list
    )


@dataclass(frozen=True)
class LosingApplicationRecord:
    user_number: str
    status: str
    reservation_number: str
    park_facility: str
    use_date: str
    use_time: str
    fee: str


@dataclass(frozen=True)
class CommonExecutionContext:
    project_root: Path
    logger: logging.Logger
    page: Page
    user: UserAccount
    user_index: int
    user_count: int
    workflow_state: WorkflowState


@dataclass(frozen=True)
class CheckExecutionContext(CommonExecutionContext):
    check_state: CheckWorkflowState


@dataclass(frozen=True)
class ExecutionContext(CommonExecutionContext):
    config: ApplicationConfig
    application_round: int
    application_round_count: int
