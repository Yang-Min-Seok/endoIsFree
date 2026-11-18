import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

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
    winning_application_confirmation_attempted: bool = False
    winning_application_confirmation_accepted: bool = False
    winning_confirmation_completed: bool = False
    is_followup_winner_check: bool = False
    account_workflow_complete: bool = False
    lottery_results: list["LotteryResultRecord"] = field(
        default_factory=list
    )


@dataclass(frozen=True)
class LotteryResultRecord:
    user_number: str
    result_type: Literal["当選", "落選"]
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
