import logging
import time
from pathlib import Path
from typing import Callable

from common.browser import open_browser
from common.config import load_config
from common.context import ExecutionContext, WorkflowState
from common.logging_config import configure_logging
from playwright.sync_api import Page
from steps import step0, step1, step2, step3, step4, step5, step6, step7

MAX_WORKFLOW_RETRIES = 3
WORKFLOW_RETRY_DELAY_SECONDS = 5
STEP_START_DELAY_SECONDS = 10
SYSTEM_ERROR_SELECTOR = "#sys-error"
SYSTEM_ERROR_MESSAGE = "データ通信を正しく行うことができませんでした"


class WorkflowRetryError(RuntimeError):
    pass


class ApplicationOutcomeUnknown(RuntimeError):
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
        if context.workflow_state.final_confirmation_accepted:
            raise ApplicationOutcomeUnknown(
                "The workflow failed after the final application "
                "confirmation was accepted. The application may already "
                "have been received. This application round will not be "
                "retried."
            ) from error
        step_name = run_step.__module__.rsplit(".", maxsplit=1)[-1]
        raise WorkflowRetryError(
            f"{step_name} failed before final submission "
            f"({type(error).__name__}: {error})."
        ) from error

    if _is_site_communication_error(context.page):
        if context.workflow_state.final_confirmation_accepted:
            raise ApplicationOutcomeUnknown(
                "The site displayed a communication error after final "
                "application confirmation was accepted. The application may "
                "already have been received. This application round will "
                "not be retried."
            )
        raise WorkflowRetryError(
            "The site displayed a communication error before final "
            "submission."
        )


def _log_failure_summary(
    logger: logging.Logger,
    failures: list[str],
) -> None:
    if not failures:
        return

    logger.warning("Failure summary (%d case(s)):", len(failures))
    for index, failure in enumerate(failures, start=1):
        logger.warning("Failure %d: %s", index, failure)


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
    failures: list[str] = []
    try:
        with open_browser(headless=not config.show_browser) as browser:
            for user_index, user in enumerate(config.users, start=1):
                skip_remaining_rounds = False
                for application_round in range(1, application_round_count + 1):
                    for attempt in range(1, MAX_WORKFLOW_RETRIES + 2):
                        logger.info(
                            "Starting workflow for account %d/%d, application "
                            "%d/%d (attempt %d/%d).",
                            user_index,
                            len(config.users),
                            application_round,
                            application_round_count,
                            attempt,
                            MAX_WORKFLOW_RETRIES + 1,
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
                                    step_name = run_step.__module__.rsplit(
                                        ".",
                                        maxsplit=1,
                                    )[-1]
                                    logger.info(
                                        "Waiting %d seconds before %s.",
                                        STEP_START_DELAY_SECONDS,
                                        step_name,
                                    )
                                    time.sleep(STEP_START_DELAY_SECONDS)
                                    _run_step(run_step, context)
                            finally:
                                browser_context.close()
                        except WorkflowRetryError as error:
                            outcome = (
                                "retries exhausted; stopped"
                                if attempt > MAX_WORKFLOW_RETRIES
                                else "retrying from step1"
                            )
                            failures.append(
                                f"account {user_index}/{len(config.users)}, "
                                f"application {application_round}/"
                                f"{application_round_count}, attempt "
                                f"{attempt}/{MAX_WORKFLOW_RETRIES + 1}: "
                                f"{error} Outcome: {outcome}."
                            )
                            if attempt > MAX_WORKFLOW_RETRIES:
                                raise RuntimeError(
                                    "The workflow failed after "
                                    f"{MAX_WORKFLOW_RETRIES} retries for "
                                    f"account {user_index}/{len(config.users)}, "
                                    f"application {application_round}/"
                                    f"{application_round_count}: {error}"
                                ) from error
                            logger.warning(
                                "Workflow failed for account %d/%d, "
                                "application %d/%d: %s Restarting from step1 "
                                "after %d seconds (retry %d/%d).",
                                user_index,
                                len(config.users),
                                application_round,
                                application_round_count,
                                error,
                                WORKFLOW_RETRY_DELAY_SECONDS,
                                attempt,
                                MAX_WORKFLOW_RETRIES,
                            )
                            time.sleep(WORKFLOW_RETRY_DELAY_SECONDS)
                            continue
                        except ApplicationOutcomeUnknown as error:
                            failures.append(
                                f"account {user_index}/{len(config.users)}, "
                                f"application {application_round}/"
                                f"{application_round_count}: {error} Outcome: "
                                "not retried; remaining applications for this "
                                "account skipped."
                            )
                            logger.error(
                                "Not retrying account %d/%d, application "
                                "%d/%d because its final confirmation was "
                                "accepted and the outcome is unknown: %s "
                                "Skipping the remaining applications for this "
                                "account and continuing with the next account.",
                                user_index,
                                len(config.users),
                                application_round,
                                application_round_count,
                                error,
                            )
                            skip_remaining_rounds = True
                            break
                        break
                    if skip_remaining_rounds:
                        break
    finally:
        _log_failure_summary(logger, failures)


if __name__ == "__main__":
    main()
