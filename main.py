import time
from pathlib import Path
from typing import Callable

from common.browser import open_browser
from common.config import load_config
from common.context import ExecutionContext, WorkflowState
from common.logging_config import configure_logging
from playwright.sync_api import Page
from steps import step0, step1, step2, step3, step4, step5, step6, step7

MAX_SYSTEM_ERROR_RETRIES = 3
SYSTEM_ERROR_RETRY_DELAY_SECONDS = 5
SYSTEM_ERROR_SELECTOR = "#sys-error"
SYSTEM_ERROR_MESSAGE = "データ通信を正しく行うことができませんでした"


class SiteCommunicationError(RuntimeError):
    pass


def _is_site_communication_error(page: Page) -> bool:
    error_article = page.locator(SYSTEM_ERROR_SELECTOR)
    if error_article.count() == 0 or not error_article.is_visible():
        return False
    return SYSTEM_ERROR_MESSAGE in error_article.inner_text()


def _run_step(
    run_step: Callable[[ExecutionContext], None],
    context: ExecutionContext,
) -> None:
    try:
        run_step(context)
    except Exception as error:
        if not _is_site_communication_error(context.page):
            raise
        if context.workflow_state.final_submission_started:
            raise RuntimeError(
                "The site displayed a communication error during final "
                "application submission. The application may already have "
                "been received, so it was not automatically retried."
            ) from error
        raise SiteCommunicationError(
            "The site displayed a communication error; the current "
            "account and application round can be retried from step1."
        ) from error

    if _is_site_communication_error(context.page):
        if context.workflow_state.final_submission_started:
            raise RuntimeError(
                "The site displayed a communication error after final "
                "application submission. The application may already have "
                "been received, so it was not automatically retried."
            )
        raise SiteCommunicationError(
            "The site displayed a communication error; the current "
            "account and application round can be retried from step1."
        )


def main() -> None:
    project_root = Path(__file__).resolve().parent
    logger = configure_logging(project_root)
    if not step0.ask_for_confirmation(logger):
        return

    config = load_config(project_root / "endoCustom" / "endoCustom.json")

    steps = (
        step1.run,
        step2.run,
        step3.run,
        step4.run,
        step5.run,
        step6.run,
        step7.run,
    )
    application_round_count = 2
    logger.info(
        "Launching browser in %s mode.",
        "visible" if config.show_browser else "background",
    )
    with open_browser(headless=not config.show_browser) as browser:
        for user_index, user in enumerate(config.users, start=1):
            for application_round in range(1, application_round_count + 1):
                for attempt in range(1, MAX_SYSTEM_ERROR_RETRIES + 2):
                    logger.info(
                        "Starting workflow for account %d/%d, application "
                        "%d/%d (attempt %d/%d).",
                        user_index,
                        len(config.users),
                        application_round,
                        application_round_count,
                        attempt,
                        MAX_SYSTEM_ERROR_RETRIES + 1,
                    )
                    browser_context = browser.new_context()
                    try:
                        try:
                            context = ExecutionContext(
                                project_root=project_root,
                                logger=logger,
                                page=browser_context.new_page(),
                                user=user,
                                user_index=user_index,
                                user_count=len(config.users),
                                config=config,
                                application_round=application_round,
                                application_round_count=application_round_count,
                                workflow_state=WorkflowState(),
                            )
                            for run_step in steps:
                                _run_step(run_step, context)
                        finally:
                            browser_context.close()
                    except SiteCommunicationError as error:
                        if attempt > MAX_SYSTEM_ERROR_RETRIES:
                            raise RuntimeError(
                                "The site communication error persisted after "
                                f"{MAX_SYSTEM_ERROR_RETRIES} retries for "
                                f"account {user_index}/{len(config.users)}, "
                                f"application {application_round}/"
                                f"{application_round_count}."
                            ) from error
                        logger.warning(
                            "Site communication error for account %d/%d, "
                            "application %d/%d. Restarting from step1 after "
                            "%d seconds (retry %d/%d).",
                            user_index,
                            len(config.users),
                            application_round,
                            application_round_count,
                            SYSTEM_ERROR_RETRY_DELAY_SECONDS,
                            attempt,
                            MAX_SYSTEM_ERROR_RETRIES,
                        )
                        time.sleep(SYSTEM_ERROR_RETRY_DELAY_SECONDS)
                        continue
                    break


if __name__ == "__main__":
    main()
