from playwright.sync_api import Dialog

from common.browser import SITE_ACTION_TIMEOUT_MS
from common.context import CheckExecutionContext

COURT_TYPE_SELECT_SELECTOR = "#selectPpsdPpst0"
COURT_TYPE_LABEL = "テニス（人工芝）"
COURT_TYPE_VALUE = "1000_1030"
APPLICATION_COUNT_INPUT_SELECTOR = "#applynum0"
APPLICATION_COUNT = "20"
WINNING_APPLICATION_CONFIRM_BUTTON_SELECTOR = "#btn-go"
WINNING_APPLICATION_CONFIRM_BUTTON_TEXT = "確認"


def run(context: CheckExecutionContext) -> None:
    context.logger.info(
        "step5 winner branch is called for account %d/%d. "
        "Preparing the winning application for confirmation.",
        context.user_index,
        context.user_count,
    )
    context.workflow_state.current_process = "利用施設選択欄の表示を待つ"
    court_type_select = context.page.locator(COURT_TYPE_SELECT_SELECTOR)
    court_type_select.wait_for(
        state="visible",
        timeout=SITE_ACTION_TIMEOUT_MS,
    )
    court_type_select.select_option(
        label=COURT_TYPE_LABEL,
        timeout=SITE_ACTION_TIMEOUT_MS,
    )
    selected_court_type = court_type_select.input_value(
        timeout=SITE_ACTION_TIMEOUT_MS
    )
    if selected_court_type != COURT_TYPE_VALUE:
        raise RuntimeError(
            "The selected court type does not match the requested option: "
            f"{selected_court_type!r}."
        )

    context.workflow_state.current_process = "申込数入力欄の表示を待つ"
    application_count_input = context.page.locator(
        APPLICATION_COUNT_INPUT_SELECTOR
    )
    application_count_input.wait_for(
        state="visible",
        timeout=SITE_ACTION_TIMEOUT_MS,
    )
    context.workflow_state.current_process = "申込数を入力"
    application_count_input.fill(
        APPLICATION_COUNT,
        timeout=SITE_ACTION_TIMEOUT_MS,
    )
    entered_application_count = application_count_input.input_value(
        timeout=SITE_ACTION_TIMEOUT_MS
    )
    if entered_application_count != APPLICATION_COUNT:
        raise RuntimeError(
            "The application count was not entered correctly: "
            f"{entered_application_count!r}."
        )

    context.workflow_state.current_process = "当選申込みの確認ボタンを待つ"
    confirm_button = context.page.locator(
        WINNING_APPLICATION_CONFIRM_BUTTON_SELECTOR
    ).filter(has_text=WINNING_APPLICATION_CONFIRM_BUTTON_TEXT)
    confirm_button.wait_for(
        state="visible",
        timeout=SITE_ACTION_TIMEOUT_MS,
    )
    dialog_messages: list[str] = []

    def dialog_handler(dialog: Dialog) -> None:
        dialog_messages.append(dialog.message)
        context.logger.info(
            "Accepting the %s confirmation dialog for the winning "
            "application: %s.",
            dialog.type,
            dialog.message,
        )
        dialog.accept()
        context.check_state.winning_application_confirmation_accepted = True

    context.workflow_state.current_process = (
        "当選申込み確認ダイアログのOKを押す"
    )
    context.page.on("dialog", dialog_handler)
    try:
        context.check_state.winning_application_confirmation_attempted = True
        confirm_button.click(timeout=0)
    finally:
        context.page.remove_listener("dialog", dialog_handler)

    if dialog_messages:
        context.workflow_state.current_process = "当選申込み確認ダイアログを承認"
        context.logger.info(
            "Accepted the winning application confirmation dialog for "
            "account %d/%d.",
            context.user_index,
            context.user_count,
        )
    else:
        context.workflow_state.current_process = "確認ダイアログ未検出"
        context.logger.error(
            "The expected confirmation dialog did not appear after clicking "
            "the winning application button for account %d/%d. "
            "The submission result is unknown.",
            context.user_index,
            context.user_count,
        )
        raise RuntimeError(
            "The winning application confirmation dialog did not appear."
        )
