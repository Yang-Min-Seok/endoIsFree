import argparse
import logging
import time
from pathlib import Path
from typing import Callable

from common.browser import open_browser
from common.check_config import CheckConfig, load_check_config
from common.config import ApplicationConfig, load_config
from common.context import (
    ApplicationCompletionNotConfirmed,
    CheckExecutionContext,
    CheckWorkflowState,
    CommonExecutionContext,
    ExecutionContext,
    LosingApplicationRecord,
    WorkflowState,
)
from common.logging_config import configure_logging
from playwright.sync_api import Page
from commonSteps import step1 as common_step1
from commonSteps import step2 as common_step2
from checkSteps import step3 as check_step3
from checkSteps import step4 as check_step4
from checkSteps import step5 as check_step5
from checkSteps import step6 as check_step6
from checkSteps import step7 as check_step7
from checkSteps import step8 as check_step8
from freeSteps import (
    step0,
    step3,
    step4,
    step5,
    step6,
    step7,
    step8,
)

MAX_WORKFLOW_RETRIES = 3
WORKFLOW_RETRY_DELAY_SECONDS = 5
STEP_START_DELAY_SECONDS = 10
MAX_CHECK_RETRIES = 3
CHECK_RETRY_DELAY_SECONDS = 5
APPLICATION_ROUND_COUNT = 2
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
    step_name = run_step.__module__.rsplit(".", maxsplit=1)[-1]
    context.workflow_state.current_step = step_name
    context.workflow_state.current_process = "ステップ開始"
    try:
        if run_step is not step8.run:
            context.workflow_state.current_process = "ステップ開始前の待機"
            context.logger.info(
                "Waiting %d seconds before %s.",
                STEP_START_DELAY_SECONDS,
                step_name,
            )
            time.sleep(STEP_START_DELAY_SECONDS)
        run_step(context)
        if (
            run_step is step8.run
            and not context.workflow_state.application_success_confirmed
        ):
            raise ApplicationCompletionNotConfirmed(
                "Step8 returned without confirming the application completion "
                "message."
            )
        context.workflow_state.current_process = "サイト通信エラーの確認"
        if _is_site_communication_error(context.page):
            raise RuntimeError(
                "サイトに通信エラーが表示されました: "
                f"{SYSTEM_ERROR_MESSAGE}"
            )
    except Exception as error:
        context.logger.error(
            "ステップエラー | 利用者番号: %s | 申込回: %d回目 | "
            "ステップ: %s | ステップ内の処理: %s | 理由: %s: %s",
            context.user.user_number,
            context.application_round,
            step_name,
            context.workflow_state.current_process,
            type(error).__name__,
            error,
        )
        if isinstance(error, ApplicationCompletionNotConfirmed):
            raise WorkflowRetryError(
                f"{step_name}の「{context.workflow_state.current_process}」で"
                f"完了メッセージを確認できませんでした（{error}）。"
            ) from error
        if context.workflow_state.step7_confirmation_accepted:
            raise ApplicationOutcomeUnknown(
                f"{step_name}の「{context.workflow_state.current_process}」で"
                "エラーが発生しました。step7確認後の申込み結果が不明なため、"
                "この申込み回は再試行しません。"
            ) from error
        raise WorkflowRetryError(
            f"{step_name}の「{context.workflow_state.current_process}」で"
            f"エラーが発生しました（{type(error).__name__}: {error}）。"
        ) from error


def _log_final_summary(
    logger: logging.Logger,
    config: ApplicationConfig,
    outcomes: dict[tuple[int, int], str],
) -> None:
    start_times = ", ".join(
        f"{start_time:02d}:00" for start_time in config.start_times
    )
    logger.info("========== 最終実行結果 ==========")
    logger.info("利用者総数: %d", len(config.users))
    logger.info("公園: %s", config.park)
    logger.info("施設: %s", config.facility)
    logger.info("利用日: %d月%d日", config.month, config.day)
    logger.info("活動時間: %d時間", config.activity_hours)
    logger.info("開始時刻: %s", start_times)
    logger.info("| 利用者番号 | 申込回 | 結果 |")
    logger.info("| --- | --- | --- |")
    for user_index, user in enumerate(config.users, start=1):
        for application_round in range(1, APPLICATION_ROUND_COUNT + 1):
            logger.info(
                "| %s | %s | %s |",
                user.user_number,
                f"{application_round}回目",
                outcomes[(user_index, application_round)],
            )
    logger.info("====================================")


def run_free() -> None:
    project_root = Path(__file__).resolve().parent
    logger = configure_logging(project_root, "free")
    try:
        if not step0.ask_for_confirmation(logger):
            return
    except Exception as error:
        logger.error(
            "ステップエラー | 利用者番号: 該当なし | 申込回: 該当なし | "
            "ステップ: step0 | ステップ内の処理: 実行確認 | 理由: %s: %s",
            type(error).__name__,
            error,
        )
        raise

    config = load_config(project_root / "endoCustom" / "freeConfig.json")
    steps = (
        common_step1.run,
        common_step2.run,
        step3.run,
        step4.run,
        step5.run,
        step6.run,
        step7.run,
        step8.run,
    )
    application_round_count = APPLICATION_ROUND_COUNT
    outcomes = {
        (user_index, application_round): "未実行"
        for user_index in range(1, len(config.users) + 1)
            for application_round in range(1, APPLICATION_ROUND_COUNT + 1)
    }
    try:
        if not config.show_browser:
            raise RuntimeError(
                "A visible browser is required because step8 needs the user "
                "to complete the final confirmation manually."
            )

        logger.info("Launching browser in visible mode.")
        with open_browser(headless=not config.show_browser) as browser:
            for user_index, user in enumerate(config.users, start=1):
                skip_remaining_rounds = False
                for application_round in range(1, application_round_count + 1):
                    outcomes[(user_index, application_round)] = "処理中"
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
                                    _run_step(run_step, context)
                                    if (
                                        context.workflow_state
                                        .application_success_confirmed
                                    ):
                                        break
                            finally:
                                browser_context.close()
                        except WorkflowRetryError as error:
                            if attempt > MAX_WORKFLOW_RETRIES:
                                outcomes[
                                    (user_index, application_round)
                                ] = "失敗"
                                logger.error(
                                    "利用者 %d/%d の申込 %d/%d は%d回の再試行後も"
                                    "失敗しました（%s）。次の申込へ進みます。",
                                    user_index,
                                    len(config.users),
                                    application_round,
                                    application_round_count,
                                    MAX_WORKFLOW_RETRIES,
                                    error,
                                )
                                break
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
                            outcomes[
                                (user_index, application_round)
                            ] = "結果不明"
                            for skipped_round in range(
                                application_round + 1,
                                application_round_count + 1,
                            ):
                                outcomes[(user_index, skipped_round)] = "スキップ"
                            logger.error(
                                "利用者 %d/%d の申込 %d/%d は最終確認結果が不明 "
                                "（%s）のため再試行しません。同じ利用者の残りの申込を"
                                "スキップし、次の利用者へ進みます。",
                                user_index,
                                len(config.users),
                                application_round,
                                application_round_count,
                                error,
                            )
                            skip_remaining_rounds = True
                            break
                        outcomes[(user_index, application_round)] = "成功"
                        break
                    if skip_remaining_rounds:
                        break
    finally:
        for key, outcome in outcomes.items():
            if outcome == "処理中":
                outcomes[key] = "中断"
        _log_final_summary(logger, config, outcomes)


def _log_check_summary(
    logger: logging.Logger,
    config: CheckConfig,
    outcomes: dict[int, str],
    losing_applications: list[LosingApplicationRecord],
) -> None:
    logger.info("========== 最終実行結果 ==========")
    logger.info("| 利用者番号 | 結果 |")
    logger.info("| --- | --- |")
    for user_index, user in enumerate(config.users, start=1):
        logger.info("| %s | %s |", user.user_number, outcomes[user_index])
    logger.info("====================================")
    if losing_applications:
        logger.info("========== 落選した申込み ==========")
        logger.info(
            "| 利用者番号 | 状態 | 予約番号 | 公園・施設 | "
            "利用日 | 利用時間 | 利用料金 |"
        )
        logger.info("| --- | --- | --- | --- | --- | --- | --- |")
        for result in losing_applications:
            logger.info(
                "| %s | %s | %s | %s | %s | %s | %s |",
                result.user_number,
                result.status,
                result.reservation_number,
                result.park_facility,
                result.use_date,
                result.use_time,
                result.fee,
            )
        logger.info("====================================")


def run_check() -> None:
    project_root = Path(__file__).resolve().parent
    logger = configure_logging(project_root, "check")
    config = load_check_config(project_root / "endoCustom" / "checkConfig.json")
    steps = (
        common_step1.run,
        common_step2.run,
        check_step3.run,
        check_step4.run,
        check_step5.run,
        check_step6.run,
        check_step7.run,
        check_step8.run,
    )
    outcomes = {
        user_index: "未確認（結果確認ステップ未実装）"
        for user_index in range(1, len(config.users) + 1)
    }
    losing_applications: list[LosingApplicationRecord] = []

    try:
        logger.info("Launching browser in visible mode.")
        with open_browser(headless=False) as browser:
            for user_index, user in enumerate(config.users, start=1):
                for attempt in range(1, MAX_CHECK_RETRIES + 2):
                    logger.info(
                        "Starting workflow for account %d/%d (attempt %d/%d).",
                        user_index,
                        len(config.users),
                        attempt,
                        MAX_CHECK_RETRIES + 1,
                    )
                    browser_context = None
                    execution_context = None
                    current_step = "step1"
                    current_process = "ブラウザーセッションを開始"
                    try:
                        browser_context = browser.new_context()
                        execution_context = CheckExecutionContext(
                            project_root=project_root,
                            logger=logger,
                            page=browser_context.new_page(),
                            user=user,
                            user_index=user_index,
                            user_count=len(config.users),
                            workflow_state=WorkflowState(),
                            check_state=CheckWorkflowState(),
                        )
                        for run_step in steps:
                            current_step = run_step.__module__.rsplit(
                                ".", maxsplit=1
                            )[-1]
                            execution_context.workflow_state.current_step = (
                                current_step
                            )
                            current_process = "ステップ開始前の待機"
                            execution_context.workflow_state.current_process = (
                                current_process
                            )
                            logger.info(
                                "Waiting %d seconds before %s.",
                                STEP_START_DELAY_SECONDS,
                                current_step,
                            )
                            time.sleep(STEP_START_DELAY_SECONDS)
                            logger.info(
                                "Wait complete. Starting %s.",
                                current_step,
                            )
                            current_process = "ステップ開始"
                            execution_context.workflow_state.current_process = (
                                current_process
                            )
                            run_step(execution_context)
                            current_process = (
                                execution_context.workflow_state.current_process
                            )
                            if (
                                execution_context.check_state
                                .account_workflow_complete
                            ):
                                logger.info(
                                    "The no-win workflow is complete for "
                                    "account %d/%d. Moving to the next account.",
                                    user_index,
                                    len(config.users),
                                )
                                break
                        if (
                            execution_context.check_state
                            .has_unconfirmed_winning_results
                        ):
                            outcomes[user_index] = (
                                "当選結果あり（確認未完了）"
                            )
                        else:
                            outcomes[user_index] = "当選結果なし"
                        losing_applications.extend(
                            execution_context.check_state.losing_applications
                        )
                    except Exception as error:
                        if execution_context is not None:
                            current_process = (
                                execution_context.workflow_state.current_process
                            )
                        logger.error(
                            "ステップエラー | 利用者番号: %s | "
                            "申込回: 該当なし | ステップ: %s | "
                            "ステップ内の処理: %s | 理由: %s: %s",
                            user.user_number,
                            current_step,
                            current_process,
                            type(error).__name__,
                            error,
                        )
                        if attempt > MAX_CHECK_RETRIES:
                            outcomes[user_index] = "未確認（再試行上限）"
                            logger.error(
                                "利用者 %d/%d の結果確認は%d回の再試行後も"
                                "失敗しました（%s）。次の利用者へ進みます。",
                                user_index,
                                len(config.users),
                                MAX_CHECK_RETRIES,
                                error,
                            )
                            break
                        logger.warning(
                            "Workflow failed for account %d/%d: %s Restarting "
                            "from step1 after %d seconds (retry %d/%d).",
                            user_index,
                            len(config.users),
                            error,
                            CHECK_RETRY_DELAY_SECONDS,
                            attempt,
                            MAX_CHECK_RETRIES,
                        )
                        time.sleep(CHECK_RETRY_DELAY_SECONDS)
                    else:
                        break
                    finally:
                        if browser_context is not None:
                            try:
                                browser_context.close()
                            except Exception as error:
                                logger.warning(
                                    "ブラウザーセッションを閉じられませんでした | "
                                    "利用者番号: %s | 理由: %s: %s",
                                    user.user_number,
                                    type(error).__name__,
                                    error,
                                )
    finally:
        _log_check_summary(
            logger,
            config,
            outcomes,
            losing_applications,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="endoIsFree workflow runner")
    parser.add_argument("mode", choices=("free", "check"))
    args = parser.parse_args()
    if args.mode == "free":
        run_free()
    else:
        run_check()


if __name__ == "__main__":
    main()
