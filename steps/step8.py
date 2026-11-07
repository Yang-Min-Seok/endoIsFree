from playwright.sync_api import Dialog
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from common.application_completion import (
    APPLICATION_COMPLETION_MESSAGE_SELECTOR,
    APPLICATION_SUCCESS_MESSAGE,
)
from common.browser import SITE_ACTION_TIMEOUT_MS
from common.context import ApplicationCompletionNotConfirmed, ExecutionContext
from common.notification import play_page_loaded_sound

USER_ACTION_REMINDER_SECONDS = 10


def run(context: ExecutionContext) -> None:
    context.workflow_state.current_process = "step7確認ダイアログの承認状態を確認"
    if not context.workflow_state.step7_confirmation_accepted:
        raise RuntimeError(
            "Step8 requires the step7 confirmation dialog to have been "
            "accepted."
        )

    context.workflow_state.current_process = "最終確認ページの読み込みを待つ"
    context.page.wait_for_load_state(
        "load",
        timeout=SITE_ACTION_TIMEOUT_MS,
    )
    context.logger.info(
        "Step8: the final confirmation is now manual. Use the visible browser "
        "to complete it; automation will not click or submit anything here. "
        "Keep the browser open until the page changes."
    )

    def dialog_handler(dialog: Dialog) -> None:
        context.logger.info(
            "A %s dialog is waiting for manual confirmation: %s",
            dialog.type,
            dialog.message,
        )

    context.page.on("dialog", dialog_handler)
    try:
        while True:
            context.workflow_state.current_process = (
                "ユーザーによる最終確認を待ち、10秒ごとに通知"
            )
            play_page_loaded_sound(context.logger)
            context.logger.info(
                "Waiting for the user to complete the final confirmation. "
                "A reminder will sound again in %d seconds.",
                USER_ACTION_REMINDER_SECONDS,
            )
            try:
                context.page.wait_for_event(
                    "framenavigated",
                    predicate=lambda frame: frame == context.page.main_frame,
                    timeout=USER_ACTION_REMINDER_SECONDS * 1000,
                )
            except PlaywrightTimeoutError:
                if context.page.is_closed():
                    raise RuntimeError(
                        "The browser page was closed before the user completed "
                        "the final confirmation."
                    )
                context.logger.info(
                    "No final-confirmation navigation detected; reminding "
                    "the user again."
                )
                continue

            context.page.wait_for_load_state(
                "load",
                timeout=SITE_ACTION_TIMEOUT_MS,
            )
            context.workflow_state.current_process = (
                "抽選申込み完了メッセージを確認"
            )
            success_message = context.page.locator(
                APPLICATION_COMPLETION_MESSAGE_SELECTOR
            ).get_by_text(
                APPLICATION_SUCCESS_MESSAGE,
                exact=True,
            )
            try:
                success_message.wait_for(
                    state="visible",
                    timeout=SITE_ACTION_TIMEOUT_MS,
                )
            except PlaywrightTimeoutError as error:
                raise ApplicationCompletionNotConfirmed(
                    "The completion message was not visible after the final "
                    f"confirmation: {APPLICATION_SUCCESS_MESSAGE}"
                ) from error
            context.workflow_state.application_success_confirmed = True
            context.logger.info(
                "The application completion message was confirmed for "
                "application %d/%d; destination page: %s.",
                context.application_round,
                context.application_round_count,
                context.page.url,
            )
            return
    finally:
        context.page.remove_listener("dialog", dialog_handler)
